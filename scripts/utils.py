"""Util functions for scripts"""

import argparse
import os
import sys
import uuid
import yaml

# To allow running from package's top location: script/pusher.py
sys.path.insert(1, ".")
from reporting.utilities import init_object

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
        description='Parse an input, e.g. a file and push to a target.')
    parser.add_argument('-c', '--conf', default='config.yaml',
                        help='Path to config yaml file. Default = config.yaml')

    args = parser.parse_args()
    config_file = args.conf

    if not os.path.exists(config_file) or not os.path.isfile(config_file):
        sys.exit("Config file %s does not exist or is not a file." % config_file)

    return yaml.load(open(config_file, "r"))
