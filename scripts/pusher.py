#!/usr/bin/env python

# pylint: disable=invalid-name
"""Take a input, parse it and push it"""

import argparse
import os
import sys
import logging
import logging.handlers
import yaml

# To allow running from package's top location: script/pusher.py
sys.path.insert(1, ".")

from reporting.utilities import getLogger, get_log_level, init_object
from utils import generate_payload

log = getLogger(__name__)
LOG_FORMAT = '%(asctime)s %(levelname)s %(module)s %(filename)s %(lineno)d: %(message)s'
SAN_MS_DATE = '%Y-%m-%d %H:%M:%S'
LOG_FORMATTER = logging.Formatter(LOG_FORMAT, SAN_MS_DATE)

def create_input(input_config, **kwargs):
    # Only support class type now
    # these class needs to take whatever caller set
    assert 'class' in input_config
    if kwargs is None:
        if 'arguments' in input_config:
            kwargs = input_config['arguments']
    return init_object(input_config['class'], **kwargs)


def create_output_handler(output_config):
    # Create an output handler by the full name of class
    return init_object(output_config['class'], output_config['arguments'])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse an input, e.g. a file and push to a target.')
    parser.add_argument('-c', '--conf', default='config.yaml',
                        help='Path to config yaml file. Default = config.yaml')

    args = parser.parse_args()
    config_file = args.conf

    if not os.path.exists(config_file) or not os.path.isfile(config_file):
        sys.exit("Config file %s does not exist or is not a file." % config_file)

    # Config format: four sections: input, output, metadata and logging
    # input and output can take any supported in reporting package.
    # See reporting package for more deatails.
    # input:
    #     class: reporting.plugins.slurm.SlurmInput
    #     arguments:
    #         path: tests/sacct-with-start-end.txt
    # output:
    #     class: reporting.outputs.HCPOutput
    #     arguments:
    #       url: s3.ersa.edu.au
    #       bucket: mybucket
    #       prefix: test
    #       id: myid
    #       secret: mysecret
    #       timeout: 10
    # metadata:
    #     schema: hpc.slurm
    #     version: 1
    # logging:
    #     log_format: "%(asctime)s - %(levelname)s - %(filename)s - %(lineno)d - %(processName)s - %(threadName)s - %(message)s"

    config = yaml.load(open(config_file, "r"))

    log_handler = logging.StreamHandler(sys.stderr)
    if 'logging' in config:
        # logging can be configured by its level, format and type: either a rotating or watched one
        # all three has default
        if 'log_level' in config['logging']:
            log.setLevel(get_log_level(config['logging']['log_level']))
        else:
            log.setLevel(logging.DEBUG)

        log_format = config['logging']['log_format'] if 'log_format' in config['logging'] else LOG_FORMAT
        log_formatter = logging.Formatter(LOG_FORMAT, SAN_MS_DATE)

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

            log_handler.setFormatter(log_formatter)
    else:
        # Use the default format and level
        log_handler.setLevel(logging.DEBUG)
        log_handler.setFormatter(LOG_FORMATTER)

    log.addHandler(log_handler)

    log.debug(config)

    slurm = create_input(config['input'], path='tests/sacct-with-start-end.txt')
    payload = generate_payload(slurm.get_data(), config['metadata'])

    log.debug(payload)
    output_handler = create_output_handler(config['output'])
    output_handler.push(payload)
