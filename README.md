# reporting-producers
Reporting Producers - collecting data on anything and everything for eRSA reporting purposes.

Ease of use currently trumps performance concerns, so everything is dumped out as JSON for now. (The JSON is consumed by a [Dropwizard](http://www.dropwizard.io) API which pushes it into [Kafka](http://kafka.apache.org).)

Required JSON structure is as follows. Note that `timestamp` and `hostname` are required keys of the `data` dictionary; all other contents of the dictionary are user-defined.

```json
{
  "schema": "the type of this record (e.g. zfs.kstat)",
  "version": "the version of the above type (e.g. 1, 2, 3, ...)",
  "id": "a uuid for this record",
  "session": "a uuid for this session (session = a single execution of the producer)",
  "data": {
    "timestamp": "seconds since epoch (integer) (required)",
    "hostname": "host which generated this record (e.g. blah.ersa.edu.au) (required)",
    "a" : "dictionary",
    "containing" : [ "the", "relevant", "data" ],
    "ps" : {
      "you" : "can nest it",
      "if" : "desired"
    }
  }
}
```

Example:

```json
{
  "schema": "iostat.osx",
  "version": 1,
  "id": "c924dafc-e9ed-47ca-93d9-3ede92516391",
  "session": "b88ab7e6-86f6-40cf-9c2d-c8a5a8a8da1b",
  "data": {
    "timestamp": 1428374675,
    "hostname": "my-random-vm.local",
    "kb/t": 110.78,
    "tps": 23,
    "mb/s": 2.47
  }
}
```

The server will populate the top level of the dictionary with the following metadata keys. These indicate the time a message was received and the address from which it was received.

```json
{
  "timestamp": "seconds since epoch (integer)",
  "hostname": "host which generated this record (e.g. blah.ersa.edu.au)"
}
```
