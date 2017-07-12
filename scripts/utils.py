"""Util functions for scripts"""

import argparse
import logging
import os
import sys
import uuid
import yaml

# To allow running from package's top location: script/pusher.py
sys.path.insert(1, ".")
from reporting.utilities import init_object, get_log_level

LOG_FORMAT = '%(asctime)s %(levelname)s %(module)s %(filename)s %(lineno)d: %(message)s'
SAN_MS_DATE = '%Y-%m-%d %H:%M:%S'
LOG_FORMATTER = logging.Formatter(LOG_FORMAT, SAN_MS_DATE)

def create_logger(name, config):
    """
    Create a named logger

    Can be defined in config. Level, type and format are all optional.
    Default level is DEBUG, and handler is stream log handler.
    """
    log = logging.getLogger(name)
    if 'logging' in config:
        # logging can be configured by its level, format and type: either a rotating or watched one
        # all three have default
        # log to a file
        if 'log_location' in config['logging']:
            if 'log_max_size' in config['logging']:
                log_handler = logging.handlers.RotatingFileHandler(
                                                config['logging']['log_location'],
                                                maxBytes=config['logging']['log_max_size'],
                                                backupCount=3)
            else:
                try:
                    log_handler = logging.handlers.WatchedFileHandler(
                                                config['logging']['log_location'],)
                except AttributeError:
                    # Python 2.5 doesn't support WatchedFileHandler
                    log_handler = logging.handlers.RotatingFileHandler(
                                                config['logging']['log_location'],)
        else:
            log_handler = logging.StreamHandler(sys.stderr)

        if 'log_level' in config['logging']:
            log.setLevel(get_log_level(config['logging']['log_level']))
        else:
            log.setLevel(logging.DEBUG)

        log_format = config['logging']['log_format'] if 'log_format' in config['logging'] else LOG_FORMAT
        log_formatter = logging.Formatter(log_format, SAN_MS_DATE)

        log_handler.setFormatter(log_formatter)
    else:
        # Use the default format and level and handler
        log.setLevel(logging.DEBUG)
        log_handler = logging.StreamHandler(sys.stderr)
        log_handler.setFormatter(LOG_FORMATTER)

    # Only support one log handler
    log.addHandler(log_handler)
    return log

def create_output(config):
    """Create an output object"""
    # all output classes take one single config argument
    # this is different to input classes
    arguments = {}
    if 'arguments' in config:
        arguments = config['arguments']
    return init_object(config['class'], arguments)

def generate_payload(data, metadata=None):
    """Generate a payload with data and optional metadata"""

    # it has only three required keys as below
    payload = {"id": str(uuid.uuid4()),
               "session": str(uuid.uuid4()),
               "data": data
              }

    # metadata is optional but recommended
    if metadata:
        for meta in metadata:
            payload[meta] = metadata[meta]
    return payload

def read_config_file():
    """Parse command line argument -c or --conf to get a configuration dict"""
    parser = argparse.ArgumentParser(
        description=('Collect and parse an input, e.g. a file and push to a target defined in config file. '
                     'At runtime, you can change ONE input argument defined in config file '
                     'if you set --key KEY AND --value VALUE, input.arguments.KEY will '
                     'be replaced by VALUE without the need of editing config file.'))
    parser.add_argument('-c', '--conf', default='config.yaml',
                        help='Path to config yaml file. Default = config.yaml')

    # Provide runtime overwrite of key-value pair in arguments of input in config file.
    # Say, you have a cron job which creates a file to be collected with different name
    # not defined in config file. If the name is shell variable, $output, you can call
    # from your cron like this:
    # python scripts/collector.py -c config.collector.runonce.yaml --key path --value $output
    parser.add_argument('--key', default='',
                        help='What *arguments* key to be overwritten in *input* of the config file')
    parser.add_argument('--value', default='',
                        help='What value to be set for the overwrite *arguments* key in *input* of the config file')

    args = parser.parse_args()
    config_file = args.conf

    if not os.path.exists(config_file) or not os.path.isfile(config_file):
        sys.exit("Config file %s does not exist or is not a file." % config_file)

    config = yaml.load(open(config_file, "r"))

    if 'arguments' in config['input'] and args.key and args.value:
        if args.key in config['input']['arguments']:
            config['input']['arguments'][args.key] = args.value
        else:
            keys = ','.join(config['input']['arguments'].keys())
            sys.exit('Unknown key %s for input.arguments. Key(s) can be overwrite: \t %s'
                     % (args.key, keys))

    return config
