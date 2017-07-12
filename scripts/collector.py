"""Run as a collector but just once"""
#!/usr/bin/env python

# pylint: disable=star-args
import collections

from utils import create_logger, create_output, generate_payload, read_config_file
from reporting.collectors import CommandRunner, HTTPReader, FileReader
from reporting.parsers import MatchParser, SplitParser, DummyParser, JsonGrepParser
from reporting.tailer import Tailer
from reporting.utilities import init_object


log = None

class Collector(object):
    """Collect from an input, process it and push by an output"""
    def __init__(self, configuration):
        self.config = configuration
        self.input = None
        self.parser = None
        self.metadata = None

        # Input is required
        arguments = {}
        if 'arguments' in self.config['input']:
            arguments = self.config['input']['arguments']
        if self.config['input']['type'] == 'command':
            self.input = CommandRunner(**arguments)
        elif self.config['input']['type'] == 'file':
            self.input = FileReader(**arguments)
        elif self.config['input']['type'] == 'http':
            self.input = HTTPReader(**arguments)
        elif self.config['input']['type'] == 'class':
            self.input = init_object(self.config['input']['name'], **arguments)
        elif self.config['input']['type'] == 'tailer':
            if 'tailer' in config:
                self.input = Tailer(config['tailer'])
            else:
                raise AttributeError("Missing tailer in config file for tailer type input")

        assert self.input

        # parser is optional for parsing data collected by input
        if 'parser' in self.config:
            arguments = {}
            if 'arguments' in self.config['parser']:
                arguments = self.config['parser']['arguments']
            if self.config['parser']['type'] == 'match':
                self.parser = MatchParser(self.config['parser']['pattern'].strip(),
                                          self.config['parser']['transform'].strip())
            elif self.config['parser']['type'] == 'split':
                self.parser = SplitParser(self.config['parser']['delimiter'].strip(),
                                        self.config['parser']['transform'].strip())
            elif self.config['parser']['type'] == 'dummy':
                self.parser = DummyParser()
            elif self.config['parser']['type'] == 'json':
                self.parser = JsonGrepParser(**arguments)
            elif self.config['parser']['type'] == 'class':
                self.parser = init_object(self.config['parser']['name'], **arguments)

        self._max_error_count = self.config['input'].get('max_error_count', -1)
        self._current_data = None
        self._number_collected = 0
        self._number_failed = 0
        self._error_count = 0

        self._output = create_output(config['output'])

        if 'metadata' in self.config:
            self.metadata = self.config['metadata']

    def collect(self):
        """Collect data and output to target"""
        error_count = 0
        args = {'config': self.config['input']}
        log.debug("Starting to collect data.")
        data = None
        no_msgs = 1
        try:
            data = self.input.get_data(**args)
            if isinstance(data, collections.deque) or isinstance(data, list):
                self._current_data = [l.decode('ASCII', 'ignore') for l in data]
                payload = []
                no_msgs = len(data)
                for line in data:
                    log.debug("Raw data: %s", line)
                    payload.append(self.generate_package(str(line.decode('ASCII', 'ignore'))))
                if len(payload) > 0:
                    self._output.push(payload)
            else:
                # a block of data: either string to be parsed or dict
                self._current_data = data
                log.debug("Raw data: %s", data)
                if isinstance(data, str):
                    payload = self.generate_package(str(data.decode('ASCII', 'ignore')))
                else:
                    payload = self.generate_package(data)
                self._output.push(payload)
        except:
            self._current_data = data
            log.exception('Unable to get or parse data. data: %s', data)
            error_count += 1
            if self._max_error_count > 0 and error_count >= self._max_error_count:
                self._error_count = error_count
            self._number_failed += no_msgs
            if self.config['input']['type'] == 'tailer':
                self.input.fail(**args)
        else:
            error_count = 0
            self._number_collected += no_msgs
            if self.config['input']['type'] == 'tailer':
                self.input.success(**args)
        self._error_count = error_count

        self._output.close()

    def generate_package(self, data):
        """Parse raw data and package the result in required format"""
        if self.parser:
            data = self.parser.parse(data)
            log.debug("Parser %s parsed data %s: ", self.parser.__class__.__name__, data)

        log.debug("Data to be packaged: %s", data)
        return generate_payload(data, self.metadata)

if __name__ == "__main__":
    # A demo code to show how Collector is used
    config = read_config_file()
    log = create_logger(__name__, config)
    slurm_collector = Collector(config)
    slurm_collector.collect()
