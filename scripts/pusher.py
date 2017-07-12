#!/usr/bin/env python

"""Demo: how to take a input and push it"""

import argparse
import os
import sys
import logging
import logging.handlers

from utils import create_logger, create_output, generate_payload, read_config_file
from reporting.utilities import init_object


def create_input(input_config, **kwargs):
    # Only support class type now
    # these class needs to take whatever caller set

    if 'class' in input_config:
        class_name = input_config['class']
    else:
        assert input_config['type'] == 'class'
        class_name = input_config['name']

    if kwargs is None:
        if 'arguments' in input_config:
            kwargs = input_config['arguments']
    return init_object(class_name, **kwargs)


if __name__ == "__main__":
    config = read_config_file()

    log = create_logger('reporting', config)
    # Create an input
    slurm = create_input(config['input'], path='tests/sacct-with-start-end.txt')
    # Generate a payload
    payload = generate_payload(slurm.get_data(), config['metadata'])
    log.debug(payload)
    # Create an output
    output_handler = create_output(config['output'])
    # Push to target
    output_handler.push(payload)
