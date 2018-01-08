[![Build Status](https://travis-ci.org/eResearchSA/reporting-producers.svg?branch=master)](https://travis-ci.org/eResearchSA/reporting-producers)

# reporting-producers
Reporting Producers - collecting data on anything and everything for eRSA reporting purposes.

### Example config file

```yaml
global:
    # you can overwrite the hostname here
    hostname: alias.host.name

collector:
    cpu:
        input:
            type: file
            path: "/proc/stat"
            frequency: 10
        parser:
            type: class
            name: reporting.plugins.linux.CPUParser
        output: buffer
        metadata:
            schema: linux.cpu
            version: 1
```

### Sections in a config YAML file

- global
- collector: aka producers and each has:
  - input:
    - type: one of *file*, *command*, *tailer*
    - frequency: how often to collect
    - other key(s): depends on type, can have other keys, e.g. path of a file to read, or command detail
  - parser
  - output: one of output handlers defined at the top level
  - metadata
- tailer: if input type is a tailer, database file name and related information
- logging: logging related, verbose level: 0: error, 1: warning, 2: info. default: debug
- output: output handler configuration
  - kafka-http: Reporting API server (kafka's http front end)
  - buffer: local cache that holds data temporarily before pushing to server
  - file:  file output for testing (everything message will be saved into this file)
- pusher: a pusher to push data in local cache, optional?


### Attributes of a `collector`

- input:

  - type: define the type of source from which information is collected
    - file: single file
    - command: an executable which generates information for collecting
    - tailer: a directory with a tracking sqlite db to remember which file was the last processed


### Example config of a collector to parse one pbs accounting log

```yaml
collector:
    pbs_accounting_log:
        input:
            type: file
            path: /home/user/Documents/ersa/reporting-producers/tests/data/pbs_accounting_log/20160102
            collect_history_data: True
            frequency: 1
        parser:
            type: class
            name: reporting.plugins.pbs.AccountingLogParser
        output: buffer
        metadata:
            schema: pbs.accounting.log
            version: 1
```

### Expected JSON structure with all required keys:

```json
{
  "schema": "the type of this record (e.g. zfs.kstat)",
  "version": "the version of the above type (e.g. 1, 2, 3, ...)",
  "id": "a uuid for this record",
  "session": "a uuid for this session (session = a single execution of the producer)",
  "data": {
    "a" : "dictionary",
    "containing" : [ "the", "relevant", "data" ],
    "ps" : {
      "you" : "can nest it",
      "if" : "desired"
    }
  }
}
```

Example of an actual content of a message with extra optional keys:

```json
{
  "id": "d87ad526-00b7-4398-b4b5-7f2da16f52d4",
  "schema": "nova.list",
  "session": "69212ffa-aae9-492b-a24d-3c968886f5f0",
  "source": "130.220.207.169",
  "timestamp": 1467374594114,
  "user_agent": "Python-urllib/2.7",
  "version": 1,
  "data": {
    "timestamp": 1497054079,
    "hostname": "cw-monitoring.sa.nectar.org.au",
    "kb/t": 110.78,
    "tps": 23,
    "mb/s": 2.47
  }
}
```

### Library dependencies

Run this command to install them if on Debian like system:

`sudo apt-get intall -y python-dev liblzma-dev`

### Run it

By default it runs in non-daemon mode. You can change it to run in daemon mode by call it with `-b` or `--background`

```shell
# run it in foreground with highest logging verbose level
./producer.py -c config.yaml -vvv -f
```
