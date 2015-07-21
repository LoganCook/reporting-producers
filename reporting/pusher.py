#!/usr/bin/env python

# pylint: disable=broad-except

import json
import logging
import os
import random
import re
import sys
import time
import traceback
import uuid
import multiprocessing
import datetime
import signal

import yaml
from reporting.utilities import getLogger, excepthook
from reporting.exceptions import MessageInvalidError, NetworkConnectionError, RemoteServerError

log = getLogger(__name__)

class Pusher(multiprocessing.Process):
    """Harvest staged data and push to the API."""
    uuid_pattern = re.compile("^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$")
    ignore = set()
    max_backoff = 2 * 60

    def __init__(self, output, directory, batch=1, stats_on=False):
        super(Pusher, self).__init__()
        self.client = output
        self.directory = directory
        self.__running=True
        self.__batch=batch
        self.__back_off=0
        self.__stats_on=stats_on

    def __sigTERMhandler(self, signum, frame):
        log.debug("Caught signal %d. Exiting" % signum)
        self.quit()
        
    def quit(self):
        self.__running=False

    def broken(self, filename):
        if filename not in self.ignore:
            try:
                os.rename(filename, filename + ".broken")
            except Exception as e:
                self.ignore.add(filename)
                log.warning("couldn't rename file %s: %s", filename, str(e))

    def backoff(self, attempt):
        time.sleep(min(self.max_backoff, attempt + random.random() * pow(2, attempt)))

    def run(self):
        # Install signal handlers
        signal.signal(signal.SIGTERM, self.__sigTERMhandler)
        signal.signal(signal.SIGINT, self.__sigTERMhandler)
        # Ensure unhandled exceptions are logged
        sys.excepthook = excepthook
        log.info("Pusher has started at %s" % datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y"))
        attempt=0
        while self.__running:
            if self.__back_off>0:
                time.sleep(1)
                self.__back_off-=1
            #log.debug("getting files to push...")
            num_success=0
            num_invalid=0
            num_error=0
            for (path, dirs, files) in os.walk(self.directory):
                data_list=[]
                data_size=0
                filename_list=[]
                for file in files:
                    filename = os.path.join(path, file)
                    if not self.uuid_pattern.match(file):
                        continue
                    try:
                        with open(filename, "r") as data:
                            self.client.push(json.loads(data.read()))
                        os.remove(filename)
                        attempt=0
                        num_success+=1
                    except MessageInvalidError as e:
                        self.broken(filename)
                        log.error("error processing %s: %s", filename, str(e))
                        num_invalid+=1
                    except Exception as e:
                        attempt+=1
                        num_error+=1
                        log.exception("network or remote server error, back off for %d seconds" % self.__back_off)
                        self.__back_off=min(self.max_backoff, attempt + random.random() * pow(2, attempt))
                        break
                    if not self.__running:
                        break
            num_total=num_success+num_invalid+num_error
            if num_total>0 and self.__stats_on==True:
                log.info("Messages total: %d; success: %d; invalid: %d; error: %d" % (num_total,num_success,num_invalid,num_error) )
            time.sleep(1)
        log.info("Pusher has stopped at %s" % datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y"))
        