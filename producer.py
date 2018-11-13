#!/usr/bin/env python

# pylint: disable=broad-except

import os
import sys
import time
import signal
import logging
import logging.handlers
import yaml
import datetime
import json

import getopt
from getopt import GetoptError

from daemon import Daemon
from reporting.utilities import getLogger, excepthook, get_log_level, set_global, init_object
from reporting.__version__ import version
from reporting.outputs import KafkaHTTPOutput, BufferOutput, FileOutput, BufferThread, AWSOutput
from reporting.pusher import Pusher
from reporting.collectors import Collector
from reporting.tailer import Tailer
from reporting.admin import AsyncServer
from reporting.exceptions import AsyncServerException
from __builtin__ import True

log = getLogger("producer")

class ProducerDaemon(Daemon):
    def __init__(self, pidfile, socketfile, config, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        Daemon.__init__(self, pidfile, stdin, stdout, stderr)
        self.__running=True
        self.__socket_file=socketfile
        self.config=config
        self.__outputs={}
        self.__pusher_pid=-1
        self.__tailer = None
        self.__buffer_thread=None
        self.__collectors=[]
        self.__asyncServer = AsyncServer(self)

    def __sigTERMhandler(self, signum, frame):
        log.debug("Caught signal %d. Exiting" % signum)
        self.quit()

    def quit(self):
        self.__asyncServer.stop()
        for c in self.__collectors:
            c.quit()
        if self.__buffer_thread is not None:
            self.__buffer_thread.quit()
        if self.__pusher_pid>-1:
            try:
                os.kill(self.__pusher_pid, signal.SIGTERM)
            except OSError as err:
                err = str(err)
                if err.find("No such process") > 0:
                    log.info("Pusher process has gone.")
        self.__running=False

    def init(self):
        """Set up all necessary directories and etc"""
        if 'global' in config:
            global_vars = config['global']
            set_global(global_vars)

        for n, cfg in config['output'].iteritems():
            if n == 'buffer':
                if not 'directory' in cfg:
                    print "ERROR: buffer directory not specified in config."
                    return False
                buffer_dir = cfg['directory']
                if os.path.exists(buffer_dir) and (not os.path.isdir(buffer_dir)):
                    print "ERROR: buffer directory exists but it is not a directory."
                    return False
                if not os.path.exists(buffer_dir):
                    log.info("Creating buffer directory %s.", buffer_dir)
                    os.makedirs(buffer_dir)
                self.__outputs[n] = BufferOutput(cfg)
            elif n == 'kafka-http':
                self.__outputs[n] = KafkaHTTPOutput(cfg)
            elif n == 'aws':
                self.__outputs[n] = AWSOutput(cfg)
            elif n == 'file':
                self.__outputs[n] = FileOutput(cfg)
            elif 'class' in cfg:
                arguments = {}
                if 'arguments' in cfg:
                    arguments = cfg['arguments']
                self.__outputs[n] = init_object(cfg['class'], **arguments)

        if 'pusher' in config:
            if not 'directory' in config['pusher'] or not 'output' in config['pusher']:
                print "ERROR: need to specify directory and output in pusher."
                return False

        if 'tailer' in config:
            self.__tailer = Tailer(config['tailer'])

        return True

    def run(self):
        # Install signal handlers
        signal.signal(signal.SIGTERM, self.__sigTERMhandler)
        signal.signal(signal.SIGINT, self.__sigTERMhandler)
        # Ensure unhandled exceptions are logged
        sys.excepthook = excepthook
        log.info("Reporting producer started at %s",
                 datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y"))
        if 'pusher' in config:
            pusher = Pusher(self.__outputs[config['pusher']['output']],
                            config['pusher']['directory'],
                            config['pusher'].get('batch', 1),
                            config['pusher'].get('stats_on', False),
                            config['pusher'].get('back_off_indicator', None))
            pusher.daemon = True
            pusher.start()
            self.__pusher_pid = pusher.pid
            log.info("started pusher pid=%d", pusher.pid)
        if 'buffer' in self.__outputs:
            self.__buffer_thread = BufferThread(self.__outputs['buffer'])
        if 'collector' in config:
            for collector_config in config['collector']:
                log.debug("Initiating collector %s", collector_config)
                log.debug("Output object: %s", self.__outputs)
                c = Collector(collector_config, config['collector'][collector_config],
                              self.__outputs[config['collector'][collector_config]['output']],
                              self.__tailer)
                self.__collectors.append(c)
        for c in self.__collectors:
            c.start()
        if self.__buffer_thread is not None:
            log.info("starting buffer thread")
            self.__buffer_thread.start()
        # Start the communication
        log.debug("Starting console communication")
        try:
            self.__asyncServer.start(self.__socket_file)
        except AsyncServerException as e:
            log.exception("Could not start socket server: %s", e)
        if 'pusher' in config:
            pusher.join()
        if self.__buffer_thread is not None and self.__buffer_thread.is_alive():
            self.__buffer_thread.join()
        for c in self.__collectors:
            if c.is_alive():
                c.join()
        log.info("Reporting producer stopped at %s",
                 datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y"))

    def console(self, message):
        if message=="config":
            return json.dumps({"producer-config":self.config})
        elif message=="show":
            return json.dumps({"collectors": [c.info() for c in self.__collectors]})
        elif message=="check":
            result=[]
            if 'buffer' in self.__outputs:
                if not self.__outputs['buffer'].check_dir.is_ok():
                    result.append("Buffer directory %s is full." % self.__outputs['buffer'].directory)
            for c in self.__collectors:
                info=c.info()
                if not info['is_running']:
                    result.append("Collector %s has stopped." % info['name'])
            return json.dumps({"check-result":result})
        elif message=="help":
            return "{\"system\": \"Command list: config, show, check\"}"
        else:
            return "{\"system\": \"Unknown command. Please run help to get a list of supported commands.\"}"

def usage():
    """ Prints reporting producer command line options and exits
    """
    print "Usage: %s [OPTIONS]" % sys.argv[0]
    print
    print "Reporting Producer v" + version + " manages local producers and buffer/pusher."
    print
    print "Options:"
    print "    -b                   start in background"
    print "    -f                   start in foreground"
    print "    -k                   kill a background instance"
    print "    -v                   verbose level: -v, warning; -vv, info; -vvv, debug. It will be overwritten by the setting in config file."
    print "    -p <FILE>            pidfile path. default: /tmp/daemon-producer.pid"
    print "    -s <FILE>            socket file path. default: /tmp/producer.sock"
    print "    -c <FILE>            configuration file path. default: config.yaml"
    print "    -h, --help           display this help message"
    print "    -V, --version        print the version"

if __name__ == "__main__":
    try:
        (opts, getopts) = getopt.getopt(sys.argv[1:], 'bfvp:s:c:khV',
                                        ["background", "foreground", "verbose", "pid=", "sock=",
                                         "config=", "kill", "help", "version"])
    except GetoptError:
        print "\nInvalid command line option detected."
        usage()
        sys.exit(1)
    daemon=False
    verbose=0
    killing=False
    pid_file="/tmp/daemon-producer.pid"
    socket_file="/tmp/producer.sock"
    config_file="config.yaml"
    #print opts
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage()
            sys.exit(0)
        if opt in ('-b', '--background'):
            daemon=True
        if opt in ('-f', '--foreground'):
            daemon=False
        if opt in ('-k', '--kill'):
            killing=True
        if opt in ('-p', '--pid'):
            pid_file = arg
        if opt in ('-s', '--sock'):
            socket_file = arg
        if opt in ('-c', '--config'):
            config_file = arg
        if opt in ('-v', '--verbose'):
            verbose += 1
        if opt in ('-V', '--version'):
            print "Reporting Producer version:", version
            sys.exit(0)

    if not os.path.exists(config_file) or not os.path.isfile(config_file):
        print "Config file %s does not exist or is not a file." % config_file
        sys.exit(1)

    config = yaml.load(open(config_file, "r"))
    producer = ProducerDaemon(pid_file, socket_file, config)
    # FIXME: if multiple loggers is needed, config file should have more configable items
    if 'logging' in config:
        if 'log_level' in config['logging']:
            log.setLevel(get_log_level(config['logging']['log_level']))
        if 'log_format' in config['logging']:
            log_format = config['logging']['log_format']
        else:
            log_format = '%(asctime)s - %(levelname)s - %(processName)s - %(threadName)s - %(message)s'
        log_formatter = logging.Formatter(log_format)
        if daemon==False:
            # Add the default logging handler to dump to stderr
            logout = logging.StreamHandler(sys.stderr)
            # tell the handler to use this format
            logout.setFormatter(log_formatter)
            log.addHandler(logout)
        elif daemon==True and killing==False:
            file_handler = None
            if 'log_max_size' in config['logging']:
                file_handler = logging.handlers.RotatingFileHandler(
                                                config['logging']['log_location'],
                                                maxBytes=config['logging']['log_max_size'],
                                                backupCount=3)
            else:
                try:
                    file_handler = logging.handlers.WatchedFileHandler(
                                                config['logging']['log_location'],)
                except AttributeError:
                    # Python 2.5 doesn't support WatchedFileHandler
                    file_handler = logging.handlers.RotatingFileHandler(
                                                config['logging']['log_location'],)

            file_handler.setFormatter(log_formatter)
            log.addHandler(file_handler)
    if verbose>0:
        log.setLevel(get_log_level(verbose))
    #print "daemon %s killing %s" % (daemon, killing)
    if killing==True:
        producer.stop()
        sys.exit(0)
    if not producer.init():
        print "init failed."
        sys.exit(1)
    if daemon==True:
        producer.start()
    elif daemon==False:
        producer.run()
    sys.exit(0)
