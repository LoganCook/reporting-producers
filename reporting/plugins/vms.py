"""VMS report from VRB"""

from math import ceil
import xlrd

from reporting.collectors import IDataSource
from reporting.utilities import init_message


class VMSInput(IDataSource):
    """Read/Parse VMS report in XLS """

    # vm name can be re-used
    # VM Id's and VM MOID's are unique
    # MOID: Managed Object ID
    # https://blogs.vmware.com/vsphere/2012/02/uniquely-identifying-virtual-machines-in-vsphere-and-vcloud-part-1-overview.html

    MAPS = {
        'Monthly Up Time (Hours)': 'span',
        'Monthly Up Time (%)': 'uptime_percent',
        'VM MOID': 'server_id',
        'vCPUs': 'core',
        'RAM GB (Configured)': 'ram',
        'Storage Used (GB)': 'storage',
        'OS Name': 'os',
        'VM Name': 'server',
        'Business Unit': 'business_unit',
        'Month': 'month'
    }

    MAPPING_KEYS = MAPS.keys()

    INT_TYPES = ('core', 'ram')

    EXCLUDING_BUs = ('', 'eRSA')

    def __init__(self, path):
        self._path = path

    @classmethod
    def _read_data(cls, xls_path):
        """Read from XLS sheet vm and return a list of dicts"""
        book = xlrd.open_workbook(xls_path)
        # open the only sheet named as vm
        data_sheet = book.sheet_by_name('vm')

        headers = []
        cols = range(data_sheet.ncols)
        for col in cols:
            headers.append(data_sheet.cell(0, col).value)

        vms = []

        row = 1
        for row in range(1, data_sheet.nrows):
            values = []
            for col in range(data_sheet.ncols):
                values.append(data_sheet.cell(row, col).value)
            vms.append(dict(zip(headers, values)))
            row += 1

        vms_with_filtered_fields = []
        for vm in vms:
            if vm['Business Unit'].strip() not in cls.EXCLUDING_BUs:
                filtered = {}
                for k in cls.MAPPING_KEYS:
                    filtered[cls.MAPS[k]] = vm[k]
                for k in cls.INT_TYPES:
                    filtered[k] = ceil(float(filtered[k]))
                vms_with_filtered_fields.append(filtered)

        return vms_with_filtered_fields

    def get_data(self, **kwargs):
        """Package VRB report vms from an XLS file"""
        data = init_message()
        data['instances'] = self._read_data(self._path)
        return data
