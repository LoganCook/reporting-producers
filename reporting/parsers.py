#!/usr/bin/env python

# pylint: disable=broad-except

import re
import json
import time

from reporting.utilities import getLogger, get_hostname
from reporting.exceptions import InputDataError

log = getLogger(__name__)

class IParser(object):
    def parse(self, data):
        assert 0, "This method must be defined."

class MatchParser(IParser):
    def __init__(self, pattern, transform):
        self.__pattern=pattern
        self.__transform=transform
    def parse(self, data):
        log.debug("match %s" % self.__pattern)
        match_obj = re.match(self.__pattern, data, re.M|re.I)
        match_groups = match_obj.groups()
        result = self.__transform.format(*match_groups)
        output = json.loads(result)
        output['timestamp'] = int(time.time())
        output['hostname'] = get_hostname()
        return output

class SplitParser(IParser):
    def __init__(self, delimiter, transform):
        self.__delimiter=delimiter
        self.__transform=transform
    def parse(self, data):
        log.debug("delimiter %s" % self.__delimiter)
        list = [item.strip() for item in re.split(self.__delimiter, data)]
        result = self.__transform.format(*list)
        log.debug("result %s"%result)
        output = json.loads(result)
        log.debug("output %s"%output)
        output['timestamp'] = int(time.time())
        output['hostname'] = get_hostname()
        return output

class DummyParser(IParser):
    def parse(self, data):
        output = {}
        output['timestamp'] = int(time.time())
        output['hostname'] = get_hostname()
        output['content'] = data.strip()
        return output

class JsonGrepParser(IParser):
    def __init__(self, pattern=None, list_name="list"):
        self.__pattern=pattern
        self.__list_name=list_name
    def parse(self, data):
        output = {}
        output['timestamp'] = int(time.time())
        output['hostname'] = get_hostname()
        try:
            j = json.loads(data)
        except ValueError as e:
            log.exception('Could not load JSON object from input data.')
            raise InputDataError()
        if self.__pattern and len(self.__pattern)>0:
            self.jsongrep(j, map(re.compile, self.__pattern.split(" ")), output)
            if self.__list_name in output and len(output[self.__list_name])==1:
                output[self.__list_name]=output[self.__list_name][0]
        else:
            if isinstance(j, list):
                output[self.__list_name]=j
            else:
                output.update(j)
        return output
    # from http://blogs.fluidinfo.com/terry/2010/11/25/jsongrep-py-python-for-extracting-pieces-of-json-objects/
    def jsongrep(self, d, patterns, output):
        #print "jsongrep %s" % d
        try:
            pattern = patterns.pop(0)
        except IndexError:
            if isinstance(d, dict):
                output.update(d)
            else:
                self.add_value(d, output)
        else:
            if isinstance(d, dict):
                #print "dict"
                keys = filter(pattern.match, d.keys())
            elif isinstance(d, list):
                #print "lsit"
                keys = map(int,
                           filter(pattern.match,
                                  ['%d' % i for i in range(len(d))]))
                #print keys
            else:
                #print "str "+str(d)
                if pattern.match(str(d)):
                    self.add_value(d, output)
                return
            for item in (d[key] for key in keys):
                self.jsongrep(item, patterns[:], output)
    def add_value(self, d, output):
        if not self.__list_name in output:
            output[self.__list_name]=[]
        #print output
        if isinstance(d, list):
            output[self.__list_name].extend(d)
        else:
            output[self.__list_name].append(d)

