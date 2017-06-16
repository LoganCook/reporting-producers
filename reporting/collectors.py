#!/usr/bin/env python

# pylint: disable=broad-except

import threading
from subprocess import Popen, PIPE
import time, datetime
import shlex
import uuid
import json
import collections
import urllib2, urllib
from os.path import expanduser

from reporting.parsers import MatchParser, SplitParser, DummyParser, JsonGrepParser
from reporting.utilities import getLogger, get_hostname, init_object
from reporting.exceptions import PluginInitialisationError, RemoteServerError
from reporting.crontab import CronEvent

log = getLogger(__name__)

class IDataSource(object):
    def get_data(self, **kwargs):
        assert 0, "This method must be defined."

class CommandRunner(IDataSource):
    def __init__(self, cmd):
        self.__cmd=cmd
    def get_data(self, **kwargs):
        log.debug("running cmd %s"%self.__cmd)
        process = Popen(shlex.split(self.__cmd), stdout=PIPE)
        pipe = process.stdout
        output = ''.join(pipe.readlines()).strip()
        process.wait()
        return output

class FileReader(IDataSource):
    def __init__(self, path):
        if path.startswith("~"):
            path = expanduser(path)
        self.__path = path

    def get_data(self, **kwargs):
        log.debug("Reading file %s" % self.__path)
        with open(self.__path) as f:
            content = ''.join(f.readlines()).strip()
        return content

class HTTPReader(IDataSource):
    def __init__(self, url, headers={}, auth=None):
        self.__url=url
        self.__headers=headers
        self.__auth=auth
    def get_data(self, **kwargs):
        try:
            if self.__auth:
                password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
                password_manager.add_password(None, self.__url, self.__auth['username'], self.__auth['password'])

                auth = urllib2.HTTPBasicAuthHandler(password_manager) # create an authentication handler
                opener = urllib2.build_opener(auth) # create an opener with the authentication handler
                urllib2.install_opener(opener) # install the opener...

            req = urllib2.Request(self.__url, None, self.__headers)
            handler = urllib2.urlopen(req)
        except urllib2.HTTPError as e:
            log.error('response code %d' % e.code)
            if e.code == 400 or e.code==500:
                raise MessageInvalidError()
            else:
                raise RemoteServerError()
        except urllib2.URLError as e:
            raise Exception("Error accessing URL %s: %s" % (self.__url, e.args))
        else:
            # 200
            response = handler.read()
            log.debug("response %d %s"% (handler.code, response))
            handler.close()
            return response

class Collector(threading.Thread):
    def __init__(self, collector_name, config, output, tailer=None):
        threading.Thread.__init__(self, name=collector_name)
        self.__collector_name=collector_name
        self.__config=config
        self.__sleep_time=self.__config['input'].get('frequency',10)
        self.__cron=self.__config['input'].get('schedule',None)
        self.__schedule=None
        if self.__cron is not None:
            self.__schedule=CronEvent(self.__cron)
            log.debug("job scheduled at %s"%self.__schedule.numerical_tab)
        self.__input=None
        self.__parser=None
        self.__output=output

        if self.__config['input']['type']=='command':
            self.__input=CommandRunner(self.__config['input']['source'])
        elif self.__config['input']['type']=='file':
            self.__input=FileReader(self.__config['input']['path'])
        elif self.__config['input']['type']=='http':
            #log.debug('input %s'%self.__config['input'])
            url=self.__config['input']['url']
            headers=self.__config['input'].get('headers', {})
            #log.debug('headers %s'%headers)
            auth=self.__config['input'].get('auth', None)
            self.__input=HTTPReader(url, headers, auth)
        elif self.__config['input']['type']=='class':
            arguments={}
            if 'arguments' in self.__config['input']:
                arguments=self.__config['input']['arguments']
            self.__input=init_object(self.__config['input']['name'], **arguments)
        elif self.__config['input']['type']=='tailer':
            if tailer is None:
                raise AttributeError("Missing tailer in config file for tailer type input")
            self.__input=tailer

        assert(self.__input)

        if 'parser' in self.__config:
            if self.__config['parser']['type']=='match':
                self.__parser=MatchParser(self.__config['parser']['pattern'].strip(), self.__config['parser']['transform'].strip())
            elif self.__config['parser']['type']=='split':
                self.__parser=SplitParser(self.__config['parser']['delimiter'].strip(), self.__config['parser']['transform'].strip())
            elif self.__config['parser']['type']=='dummy':
                self.__parser=DummyParser()
            elif self.__config['parser']['type']=='json':
                arguments={}
                if 'arguments' in self.__config['parser']:
                    arguments=self.__config['parser']['arguments']
                self.__parser=JsonGrepParser(**arguments)
            elif self.__config['parser']['type']=='class':
                arguments={}
                if 'arguments' in self.__config['parser']:
                    arguments=self.__config['parser']['arguments']
                self.__parser=init_object(self.__config['parser']['name'], **arguments)
        self.__running=True
        self.__session_id=str(uuid.uuid4())
        self.__max_error_count=self.__config['input'].get('max_error_count', -1)
        self.__current_data=None
        self.__number_collected=0
        self.__number_failed=0
        self.__sleep_count=0
        self.__error_count=0
        self.__last_check_minute=-1

    def quit(self):
        self.__running=False

    def info(self):
        col_info={"name":self.__collector_name, "config":self.__config, "sleep_time": self.__sleep_time}
        col_info["session_id"]=self.__session_id
        col_info["is_running"]=self.__running
        col_info["current_data"]=self.__current_data
        col_info["number_collected"]=self.__number_collected
        col_info["number_failed"]=self.__number_failed
        col_info["sleep_count"]=self.__sleep_count
        col_info["error_count"]=self.__error_count
        col_info["max_error_count"]=self.__max_error_count
        if self.__cron is not None:
            col_info["cron"]=self.__cron
        if self.__config['input']['type']=='tailer':
            col_info["tailer"]=self.__input.info(self.__config['input']['path'])
        return col_info

    def match_time(self):
        """Return True if this event should trigger at the specified datetime"""
        if self.__schedule is None:
            return False
        t=datetime.datetime.now()
        if t.minute==self.__last_check_minute:
            return False
        self.__last_check_minute=t.minute
        log.debug("check if cron job can be triggered. %d"%self.__last_check_minute)
        return self.__schedule.check_trigger((t.year,t.month,t.day,t.hour,t.minute))

    def run(self):
        count = self.__sleep_time
        error_count = 0
        log.info("Collector %s has started.", self.__collector_name)
        while self.__running:
            args = {'config': self.__config['input']}
            if (self.__schedule is None and count == self.__sleep_time) or self.match_time():
                log.debug("Starting to collect data.")
                count = 0
                data = None
                no_msgs = 1
                try:
                    data = self.__input.get_data(**args)
                    if isinstance(data, collections.deque) or isinstance(data, list):
                        self.__current_data = [l.decode('ASCII', 'ignore') for l in data]
                        payload = []
                        no_msgs = len(data)
                        for line in data:
                            log.debug("Raw data: %s", line)
                            payload.append(self.generate_payload(str(line.decode('ASCII', 'ignore'))))
                        if len(payload) > 0:
                            self.__output.push(payload)
                        else:
                            continue
                    else:
                        self.__current_data = data
                        log.debug("Raw data: %s", data)
                        payload = self.generate_payload(str(data.decode('ASCII', 'ignore')))
                        self.__output.push(payload)
                except:
                    self.__current_data = data
                    log.exception('Unable to get or parse data. data: %s', data)
                    error_count += 1
                    if self.__max_error_count > 0 and error_count >= self.__max_error_count:
                        self.__running = False
                        self.__error_count = error_count
                        break
                    self.__number_failed += no_msgs
                    if self.__config['input']['type'] == 'tailer':
                        self.__input.fail(**args)
                else:
                    error_count = 0
                    self.__number_collected += no_msgs
                    if self.__config['input']['type'] == 'tailer':
                        self.__input.success(**args)
                self.__error_count = error_count
            else:
                time.sleep(1)
                if self.__schedule is None:
                    count += 1

            self.__sleep_count = count

        self.__output.close()
        log.info("Collector %s has stopped.", self.__collector_name)

    def generate_payload(self, data):
        """Parse raw data and package the result in required format"""
        if self.__parser:
            data = self.__parser.parse(data)

        log.debug("parsed data %s", data)
        payload = {"id": str(uuid.uuid4()), "session": self.__session_id}
        payload['data'] = data
        if 'metadata' in self.__config:
            for m in self.__config['metadata']:
                payload[m] = self.__config['metadata'][m]
        log.debug("payload to push: %s", payload)
        return payload
