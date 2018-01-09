#!/usr/bin/env python

# Download a monthly vms report from VRB
# It takes two positional command line arguments: YEAR and MONTH
# It also needs secrets from conf.json file in current directory with these fields.
#{
#    "username": "username",
#    "password": "password",
#    "tenant": "vsphere.local"
#}
#
# The report name is vms_YEAR_MONTH.xls. In the file name, MONTH with one digit will be zero padded
# This is one example how it can be used:
# ./dl_vrb_vms_report.py 2018 1
# printf -v fn "vms_%d_%02d.xls" 2018 1
# ls -l $fn
# python scripts/collector.py -c config.yaml --key path --value $fn

import sys
import urllib2
import json

def get_timeframe(year, month):
    if month == 12:
        end_year = year + 1
        end_month = 1
    else:
        end_year = year
        end_month = month + 1
    return "startmonth=%d-%02d&endmonth=%d-%02d" % (year, month, end_year, end_month)

def create_headers(token):
    """Use token to create headers to download a report from VRB"""
    return {
        "Authorization": "Bearer %s" % token,
        "accept-encoding": "gzip",
        "Accept": "text/plain",
        "Content-Type": "text/plain"
    }


if len(sys.argv) != 3:
    sys.exit('Missing arguments: Need starting year and month for downloading monthly report in the format of YEAR MONTH')

year = int(sys.argv[1])
month = int(sys.argv[2])

VRB_AUTH_SERVER = 'https://tangocloud.ersa.edu.au/identity/api/tokens'
VRB_REPORT_URL = 'https://tcvrb-01.ad.ersa.edu.au/itfm-cloud/rest/reports/export-filters/vms?%s' % get_timeframe(year, month)

# Default headers to aquire token
HEADERS = {
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

with open('conf.json') as f:
    conf = json.load(f)

import ssl
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

# this is a very strange way to deal with form data: if not in such format, there will be bad request
form_data = json.JSONEncoder().encode(conf).encode('utf-8')
req = urllib2.Request(url=VRB_AUTH_SERVER, headers=HEADERS, data=form_data)

f = urllib2.urlopen(req)
response = json.loads(f.read().decode('utf-8'))
f.close()

if response:
    token = response['id']
    print(token)
else:
    sys.exit('Failed to aquire Bearer token')

req = urllib2.Request(VRB_REPORT_URL, headers=create_headers(token))
fn = 'vms_%d_%02d.xls' % (year, month)
f = urllib2.urlopen(req)
with open(fn, 'wb') as out:
    out.write(f.read())
f.close()

print("Report has been saved in %s" % fn)
