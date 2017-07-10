#!/usr/bin/env python

# pylint: disable=broad-except

import logging
import sys
import random
import string
import socket
import datetime
import platform
import time
import os
from reporting.exceptions import PluginInitialisationError

global_vars=None

def set_global(vars):
    global global_vars
    global_vars = vars

def getLogger(name):
    """Get logging.Logger instance with logger name convention
    """
    if "." in name:
        name = "producer.%s" % name.rpartition(".")[-1]
    return logging.getLogger(name)

log = getLogger(__name__)

def excepthook(exc_type, exc_value, exc_traceback):
    """Except hook used to log unhandled exceptions to log
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    getLogger("producer").critical(
        "Unhandled exception in reporting producer:", exc_info=(exc_type, exc_value, exc_traceback))
    #return sys.__excepthook__(exctype, value, traceback)

def get_log_level(verbose):
    if verbose <= 0:
        return logging.ERROR
    elif verbose == 1:
        return logging.WARNING
    elif verbose == 2:
        return logging.INFO
    return logging.DEBUG

def get_hostname():
    """Get the host name of a producer"""
    global global_vars
    if global_vars is not None and 'hostname' in global_vars:
        return global_vars['hostname']
    try:
        return socket.getfqdn()
    except:
        return platform.node()

def list_to_dict(d, l, value):
    if len(l) == 1:
        d[l[0]] = value
    else:
        if l[0] not in d:
            d[l[0]] = {}
        list_to_dict(d[l[0]], l[1:], value)

def formatExceptionInfo():
    """ Consistently format exception information """
    cla, exc = sys.exc_info()[:2]
    return (cla.__name__, str(exc))

def init_message():
    return {'timestamp': int(time.time()), 'hostname': get_hostname()}

def init_object(class_name, *args, **kwargs):
    mod_name = '.'.join(class_name.split('.')[:-1])
    class_name = class_name.split('.')[-1]
    log.debug("Loading plugin %s %s"%(mod_name, class_name))
    try:
        mod = __import__(mod_name, globals(), locals(), [class_name])
    except SyntaxError as e:
        raise PluginInitialisationError(
            "Plugin %s (%s) contains a syntax error at line %s" %
            (class_name, e.filename, e.lineno))
    except ImportError as e:
        log.exception(e)
        raise PluginInitialisationError(
            "Failed to import plugin %s: %s" %
            (class_name, e[0]))
    klass = getattr(mod, class_name, None)
    if not klass:
        raise PluginInitialisationError(
            'Plugin class %s does not exist' % class_name)
    try:
        return klass(*args, **kwargs)
    except Exception as exc:
        raise PluginInitialisationError(
            "Failed to load plugin %s with "
            "the following error: %s - %s" %
            (class_name, exc.__class__.__name__, exc.message))

def touch(fname, times=None):
    with open(fname, 'a'):
        os.utime(fname, times)