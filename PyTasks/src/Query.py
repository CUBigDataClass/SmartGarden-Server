import os
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# Initialize Influx Client
token = os.environ['TOKEN']
org = os.environ['ORG']
bucket = os.environ['BUCKET']

client = InfluxDBClient(url=os.environ['DB_HOST'], token=token)
query_api = client.query_api()


def readResults(res):
    results = []
    for table in res:
        for record in table.records:
            results.append((record['_measurement'], record["_value"]))
    return results


def HoursOfSunlight():
    query = f'from(bucket: "{bucket}")'
    query += '''
      |> range(start: -1d, stop: now())
      |> filter(fn: (r) => r["_measurement"] == "light")
      |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
      |> filter(fn: (r) => r["_value"] > 100)
      |> aggregateWindow(every: 1d, fn: count, createEmpty: false)
      |> toFloat()
      |> map(fn: (r) => ({
          r with
          _value: r._value / 60.0
        })
      )
      |> last()
    '''

    results = query_api.query(org=org, query=query)
    results = readResults(results)
    assert len(results) == 1
    return results[0][1]


def TempRange():
    query = f'from(bucket: "{bucket}")'
    query += '''
      |> range(start: -1d, stop: now())
      |> filter(fn: (r) => r["_measurement"] == "temperature")
      |> filter(fn: (r) => r["host"] == "pi")
      |> group(columns: ["_measurement"], mode: "by")
      |> aggregateWindow(every: 1d, fn: min, createEmpty: false)
      |> last()
    '''
    results = query_api.query(org=org, query=query)
    results = readResults(results)
    assert len(results) == 1
    min_temp = results[0][1]

    query = f'from(bucket: "{bucket}")'
    query += '''
      |> range(start: -1d, stop: now())
      |> filter(fn: (r) => r["_measurement"] == "temperature")
      |> filter(fn: (r) => r["host"] == "pi")
      |> group(columns: ["_measurement"], mode: "by")
      |> aggregateWindow(every: 1d, fn: max, createEmpty: false)
      |> last()
    '''
    results = query_api.query(org=org, query=query)
    results = readResults(results)
    assert len(results) == 1
    max_temp = results[0][1]

    return (min_temp, max_temp)
