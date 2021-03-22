import schedule
import time
import requests
from datetime import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from slack_sdk.webhook import WebhookClient

# Initialize Influx Client
token = "bSxqkjOZfiS4Yw8qWYyolME1RbUr0SWKuKlJAQbzQUjiuwNs5DGxSu4L4Q_T5VKWtG6P6KO1XrwKGQMKT9wyYw=="
org = "Falkreath Hold"
bucket = "GardenBucket"

client = InfluxDBClient(url="http://namira.lan:8086", token=token)
write_api = client.write_api(write_options=SYNCHRONOUS)

# Initialize Slack WebHook
url = "https://hooks.slack.com/services/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"
webhook = WebhookClient(url)

# Config OpenWeatherAPI
key = '7b3b6150c34c662331a4bdd1ebb9d3e2'
zip_code = 80124
open_weather_api_url = 'https://api.openweathermap.org'
params = f'zip={zip_code}&appid={key}&units=metric'
forecast_url = f'{open_weather_api_url}/data/2.5/forecast?{params}'
current_weather_url = f'{open_weather_api_url}/data/2.5/weather?{params}'

def ping_current_weather():
    res = requests.get(current_weather_url)
    assert res.status_code == 200
    data = res.json()
    dt = datetime.fromtimestamp(data['dt'])
    write = {
        'open_weather_temp': data['main']['temp'],
        'open_weather_humidity': data['main']['humidity'],
        'open_weather_wind_speed': data['wind']['speed'],
        'open_weather_cloud_cover': data['clouds']['all'],
        'open_weather_daylight_hours': (data['sys']['sunset'] - data['sys']['sunrise']) / (60 * 60),
    }
    for key in write:
        point = Point(key).tag("host", "server").field("value", write[key]).time(dt, WritePrecision.S)
        write_api.write(bucket, org, point)

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
