import schedule
import time
import requests
import os
from datetime import datetime
import pytz
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from slack_sdk.webhook import WebhookClient

##
## Config
##

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


##
## Current Weather
##

def FetchCurrentWeather():
    res = requests.get(current_weather_url)
    if not res.status_code == 200:
        print(res.status_code)
        print(res.content)
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
    print('pinging weather api')
    current_weather = FetchCurrentWeather()
    dt = datetime.fromtimestamp(current_weather['dt']).astimezone(pytz.utc)
    print(dt)
    for key, value in ParseCurrentWeather(current_weather).items():
        point = Point(key).tag("host", hostname).field("value", value).time(dt, WritePrecision.S)
        write_api.write(bucket, org, point)

PingCurrentWeather()
schedule.every(5).minutes.do(PingCurrentWeather)


def job(t):
    print("I'm working...", t)
    response = webhook.send(text=f"Hello from pytask! {t}")
    assert response.status_code == 200
    assert response.body == "ok"
    return

schedule.every().day.at("14:00").do(job,'It is 14:00')

while True:
    schedule.run_pending()
    time.sleep(60) # wait one minute
