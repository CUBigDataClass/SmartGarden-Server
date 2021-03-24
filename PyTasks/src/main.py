import os
import sys
import logging
import time
from datetime import datetime
import pytz
import requests
import schedule
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from slack_sdk.webhook import WebhookClient


##
## Config
##

# Logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(asctime)s-%(levelname)s: %(message)s')

# Initialize Influx Client
token = os.environ['TOKEN']
org = os.environ['ORG']
bucket = os.environ['BUCKET']

client = InfluxDBClient(url=os.environ['DB_HOST'], token=token)
write_api = client.write_api(write_options=SYNCHRONOUS)
hostname = os.environ['HOSTNAME']

# Initialize Slack WebHook
webhook = WebhookClient(os.environ['WEBHOOK_URL'])

# Config OpenWeatherAPI
key = os.environ['OPEN_WEATHER_API_KEY']
zip_code = os.environ['ZIP_CODE']
open_weather_api_url = 'https://api.openweathermap.org'
params = f'zip={zip_code}&appid={key}&units=metric'
forecast_url = f'{open_weather_api_url}/data/2.5/forecast?{params}'
current_weather_url = f'{open_weather_api_url}/data/2.5/weather?{params}'


def RunFailSafe(job, *args, **kwargs):
    '''Catch all errors to avoid resetting schedule'''
    try:
        job(*args, **kwargs)
    except Exception as e:
        logging.exception(e)


##
## Current Weather
##


def FetchCurrentWeather():
    res = requests.get(current_weather_url)
    if res.status_code != 200:
        logging.error(res.status_code)
        logging.error(res.content)
    assert res.status_code == 200
    return res.json()


def ParseCurrentWeather(current_weather):
    return { # InfluxDB is picky about types
        'open_weather_temp': float(current_weather['main']['temp']),
        'open_weather_humidity': int(current_weather['main']['humidity']),
        'open_weather_wind_speed': float(current_weather['wind']['speed']),
        'open_weather_cloud_cover': int(current_weather['clouds']['all']),
        'open_weather_daylight_hours': float((current_weather['sys']['sunset'] - current_weather['sys']['sunrise']) / (60 * 60)),
    }


def PingCurrentWeather():
    logging.info('pinging weather api')
    current_weather = FetchCurrentWeather()
    dt = datetime.fromtimestamp(current_weather['dt']).astimezone(pytz.utc)
    logging.info(dt)
    for key, value in ParseCurrentWeather(current_weather).items():
        point = Point(key).tag("host", hostname).field("value", value).time(dt, WritePrecision.S)
        write_api.write(bucket, org, point)


RunFailSafe(PingCurrentWeather)
schedule.every(5).minutes.do(RunFailSafe, PingCurrentWeather)


while True:
    schedule.run_pending()
    time.sleep(60) # wait one minute
