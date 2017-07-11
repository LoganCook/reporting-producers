#!/usr/bin/env python

# pylint: disable=broad-except

import json
import os
import time
import threading
import urllib2
import base64
import datetime
import collections

from reporting.exceptions import MessageInvalidError, RemoteServerError
from reporting.utilities import getLogger
from archive import Archive


log = getLogger(__name__)

class IOutput(object):
    def push(self, data):
        """
        data is a python object, list or dict
        """
        assert 0, "This method must be defined."
    def close(self):
        pass

class KafkaHTTPOutput(IOutput):
    """Reporting API client."""
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }

    def __init__(self, config):
        self.url = config["url"]
        self.auth = (config["username"], config["token"])
        self.attempts = config.get("attempts", 3)
        self.timeout = config.get("timeout", 50)

    def push(self, data):
        if not isinstance(data, list) and not isinstance(data, collections.deque):
            data = [data]
        sub=data[0]['schema'].split('.')[0]
        payload = json.dumps(data)
        log.debug("pushing data to http: %s", payload[:1024])
        base64string = base64.encodestring('%s:%s' % (self.auth[0], self.auth[1])).replace('\n', '')
        self.headers['Authorization'] = "Basic %s" % base64string
        try:
            #password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
            #password_manager.add_password(None, self.url, self.auth[0], self.auth[1])

            #auth = urllib2.HTTPBasicAuthHandler(password_manager) # create an authentication handler
            #opener = urllib2.build_opener(auth) # create an opener with the authentication handler
            #urllib2.install_opener(opener) # install the opener...
            start_time=time.time()
            req = urllib2.Request(self.url+"."+sub, payload, self.headers)
            handler = urllib2.urlopen(req, timeout=self.timeout)
        except urllib2.HTTPError as e:
            if e.code == 400: # or e.code==500:
                response = handler.read() if handler else ""
                log.error('Failed to push data to %s, error code %d, error message: %s', self.url+"."+sub, e.code, response)
                raise MessageInvalidError()
            else:  # 500 or other error
                log.error('Failed to push data to %s, error code %d', self.url+"."+sub, e.code)
                raise RemoteServerError()
        except urllib2.URLError as e:
            log.error("spent %d second to push %d bytes",
                      time.time()-start_time, len(payload))
            raise Exception("Failed to push data to %s, HTTP error: %s" % (self.url+"."+sub, e.args))
        else:
            # 200
            response = handler.read()
            log.debug("response %d %s", handler.code, response)
            handler.close()

class FileOutput(IOutput):
    def __init__(self, config):
        self.path = config["path"]
        self.__handle=open(self.path, "w")

    def push(self, data):
        if not isinstance(data, list):
            data = [data]
        for line in data:
            self.__handle.write(json.dumps(line) + os.linesep)
        self.__handle.flush()

    def close(self):
        log.debug("closing file handle for %s", self.path)
        if self.__handle:
            self.__handle.close()

class CheckDir(object):
    """Ensure sufficient capacity for staging data."""

    def __init__(self, directory = ".", cache_size=100, check_period=30):
        self.__directory = directory
        self.__cache_size = cache_size
        self.__check_period = check_period
        self.__last_check = 0
        self.__ok = False

    def perform_check(self):
        actual_size=self.get_directory_size(self.__directory)
        log.debug("size of dir %s is %d, cache size is %d", self.__directory, actual_size, self.__cache_size)
        return self.__cache_size > actual_size

    def is_ok(self):
        if (time.time() - self.__last_check) >= self.__check_period:
            self.__ok = self.perform_check()
        return self.__ok

    def get_directory_size(self, directory):
        dir_size = 0
        for (path, _, files) in os.walk(directory):
            for file in files:
                filename = os.path.join(path, file)
                try:
                    # if the file has been uploaded and gone, ignore
                    dir_size += os.path.getsize(filename)
                except:
                    pass
        return dir_size

class BufferOutput(IOutput):
    """Stage data prior to upload."""
    def __init__(self, config):
        self._verify(config)
        self.directory = config['directory']
        self.check_dir = CheckDir(config['directory'], config['size'])
        self.log_space_warning = False
        self.queue = []
        self.write_lock = threading.Lock()

    def _verify(self, config):
        """Verify directory in configuration and create directory if needed"""
        if not 'directory' in config:
            log.exception("ERROR: BufferOutput - buffer directory not specified in config.")

        buffer_dir = config['directory']
        if os.path.exists(buffer_dir) and (not os.path.isdir(buffer_dir)):
            log.exception("ERROR: BufferOutput - buffer directory exists but it is not a directory.")

        if not os.path.exists(buffer_dir):
            log.info("BufferOutput - creating buffer directory %s.", buffer_dir)
            os.makedirs(buffer_dir)

    def push(self, data):
        with self.write_lock:
            if isinstance(data, collections.deque) or isinstance(data, list):
                self.queue.extend(data)
            else:
                self.queue.append(data)
        return True

    def execute(self):
        json.encoder.FLOAT_REPR = lambda f: ("%.2f" % f)
        if len(self.queue)>0:
            with self.write_lock:
                data = self.queue.pop()
            if len(data) == 0:
                return False
            if self.check_dir.is_ok():
                self.log_space_warning=False
                log.debug("data to save: %s", data)
                data_id = data["id"]
                data_dir = self.directory
                if 'schema' in data:
                    sub_dir = data['schema'].split('.')[0]
                    data_dir += os.sep + sub_dir
                    if not os.path.exists(data_dir):
                        os.mkdir(data_dir)
                filename = "%s/%s" % (data_dir, data_id)
                filename_tmp = "%s/.%s" % (data_dir, data_id)
                try:
                    with open(filename_tmp, "w") as output:
                        output.write(json.dumps(data))
                    os.rename(filename_tmp, filename)
                except Exception as e:
                    log.error("unexpected error: %s", str(e))
                    return False
            else:
                if not self.log_space_warning:
                    log.warn("Cache directory %s has reached its capacity.", self.directory)
                self.log_space_warning=True
                return False
            return True
        return False

    def cleanup(self):
        log.info("write all data to cache before exit...")
        while len(self.queue)>0:
            self.execute()

class BufferThread(threading.Thread):
    def __init__(self, buffer):
        threading.Thread.__init__(self, name="buffer-thread")
        self.__buffer=buffer
        self.__running=True

    def quit(self):
        self.__running=False

    def run(self):
        log.info("Buffer thread has started.")
        while self.__running:
            if not self.__buffer.execute():
                time.sleep(1)
        self.__buffer.cleanup()
        log.info("Buffer thread stopped at %s",
                 datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y"))


class HCPOutput(IOutput):
    """HCP client for uploading packages."""

    def __init__(self, config):
        self.attempts = config.get("attempts", 3)
        self.timeout = config.get("timeout", 50)
        self.archiver = Archive(config["id"],
                                config["secret"],
                                config["url"],
                                config["bucket"],
                                config["prefix"])

    def push(self, data):
        archive_name = "%s/%s.json.xz" % (data["schema"], data["data"]["timestamp"])
        # Put single message into an array for backward compatibility
        # when the source of ingest was from archives of messages
        # from Kafka identified by offsets.
        self.archiver.save(archive_name, [data])
