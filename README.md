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
  - parser: optional, called in `Collector::generate_payload` before sending out
  - output: one of output handlers defined at the top level
  - metadata
- tailer: if input type is a tailer, database file name and related information
- logging: logging related, verbose level: 0: error, 1: warning, 2: info. default: debug
- output: output handler configuration
  - kafka-http: Reporting API server (eRSA Kafka gateway)
  - buffer: local cache that holds parsed data temporarily (without packaging)
            before pushing to server. file names is message id.
  - file:  file output for testing (everything message will be saved into this file)
- pusher: a pusher to push data in local cache


### Attributes of a `collector`

- input:

  - type: define the type of source from which information is collected
    - file: single file
    - command: an executable which generates information for collecting
    - tailer: a directory with a tracking sqlite database to remember which file was the last processed
      - `collect_history_data`: only used when no tracker found - either new database or file is gone.
         If is `True`, set the tracker to be the oldest, aka collect all files in the directory. If it is
         `False`, set the tracker to be the newest in the directory, aka all files in the directory have
         been collected. Default is `False`.


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

### Library dependencies on operating system

Run this command to install them if on Debian like system:

`sudo apt-get install -y python-dev liblzma-dev`

### Test

Tests are designed to run with `nosetests` (an optional dependency). So you can simply run `nosetests` or with a particular one:

`nosetests tests/test_plug_slurm.py`

### Run `producer.py`

By default it runs in non-daemon mode. You can change it to run in daemon mode by call it with `-b` or `--background`

```shell
# run it in foreground with highest logging verbose level
./producer.py -c config.yaml -vvv -f
```

#### Scripts

Some [scripts](scripts) were created for simple tasks.
  1. [`pusher.py`](scripts/pusher.py) is a demo of reading a file, packaging and pushing.
     In this case, you can say only what input class you need without providing initialization arguments
     in the config file. *`input` in config usually has one key-value: `class: what.class`, DOES NOT have
     type key-value pair. This is different to the config used by `collector.py`*
  2. [`collector.py`](scripts/collector.py) is a demo of how to do what `producer.py` does but just once.

These scripts use reduced configuration files (an example is `config.runonce.yaml.exaple`): they still
have at least three sections: *input*, *output*, *metadata*.
Even omitting *metadata* will not stop code running but it should be set. *parse* and *logging* are optional.
See reporting package for more details.

**Note**: the names of arguments have to match what they are called when an *input* or *parser* is initialised because
these scripts DO NOT translate them as they are done in [collectors.py](reporting/collectors.py).

For *input*, if it has *arguments*, one of its key-value pairs can be overridden at run time by calling script with:
`--key KEY --value VALUE`. This is useful when one of `input->arguments` is treated as a default for a collector.
For example, if a collector is to collect a different file every month, you can define a default
`path: tests/sacct-with-start-end.txt` in `config.yaml` as a place holder, call it by overriding `path` argument like this

`python scripts/collector.py -c config.yaml --key path --value my_other_file_path`.

if `config.yaml` is:

```yaml
input:
    class: reporting.plugins.slurm.SlurmInput
    arguments:
        path: tests/sacct-with-start-end.txt
metadata:
    schema: hpc.slurm
    version: 1
output:
    class: reporting.outputs.AWSOutput
    arguments:
      url: s3.ersa.edu.au
      bucket: mybucket
      prefix: test
      id: myid
      secret: mysecret
      timeout: 10
logging:
    log_format: "%(asctime)s - %(levelname)s - %(filename)s - %(lineno)d - %(processName)s - %(threadName)s - %(message)s"
```
