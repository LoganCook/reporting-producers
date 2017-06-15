from reporting.parsers import IParser
from reporting.utilities import init_message


class SlurmParser(IParser):
    """To be used to parse Accounting information from Slurm"""

    def parse(self, data):
        """Parse"""
        print "Raw data:"
        print data
        output = init_message()
        output['slurm'] = 'content to come'
        raise ValueError('No parsing logic for data')
        return output
