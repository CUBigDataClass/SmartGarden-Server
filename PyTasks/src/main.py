import schedule
import time
import requests
import os
from datetime import datetime
import pytz
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from slack_sdk.webhook import WebhookClient

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

def ping_current_weather():
    print('pinging weather api')
    res = requests.get(current_weather_url)
    assert res.status_code == 200
    data = res.json()
    dt = datetime.fromtimestamp(data['dt']).astimezone(pytz.utc)
    print(dt)
    write = { # InfluxDB is picky about types
        'open_weather_temp': float(data['main']['temp']),
        'open_weather_humidity': int(data['main']['humidity']),
        'open_weather_wind_speed': float(data['wind']['speed']),
        'open_weather_cloud_cover': int(data['clouds']['all']),
        'open_weather_daylight_hours': float((data['sys']['sunset'] - data['sys']['sunrise']) / (60 * 60)),
    }
    for key in write:
        point = Point(key).tag("host", hostname).field("value", write[key]).time(dt, WritePrecision.S)
        write_api.write(bucket, org, point)

ping_current_weather()
schedule.every(5).minutes.do(ping_current_weather)


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
