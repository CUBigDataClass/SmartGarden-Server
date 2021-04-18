import os
import sys
import logging
import time
from datetime import datetime
import pytz
import schedule
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

import Weather
import Slack
import Shinobi
import Query

'''
Config
'''
# Logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(asctime)s-%(levelname)s: %(message)s')

# Initialize Influx Client
token = os.environ['TOKEN']
org = os.environ['ORG']
bucket = os.environ['BUCKET']

client = InfluxDBClient(url=os.environ['DB_HOST'], token=token)
write_api = client.write_api(write_options=SYNCHRONOUS)
hostname = os.environ['HOSTNAME']


def PingCurrentWeather():
    '''
    Get current Weather from OpenWeatherAPI.
    Write data to InfluxDB.
    '''
    logging.info('checking current weather')
    current_weather = Weather.FetchCurrentWeather()
    dt = datetime.fromtimestamp(current_weather['dt']).astimezone(pytz.utc)
    logging.info(dt)
    for key, value in Weather.ParseCurrentWeather(current_weather).items():
        point = Point(key).tag("host", hostname).tag('tag', 'Open_Weather_API').tag('subtag', 'API').field("value", float(value)).time(dt, WritePrecision.S)
        write_api.write(bucket, org, point)


def PingForecast():
    '''Check hourly 2-day forcast and send summary to Slack.'''
    logging.info('Checking hourly forecast')
    forecast = Weather.FetchForecast()
    status = Weather.CheckForecast(forecast)
    message = Weather.ForecastMessage(status)
    # Send status to slack
    Slack.SendMessage(message='2 day Forecast:\n' + message)


def PingShinobi():
    '''Check Cameras and send picture to Slack.'''
    # TODO: Configure monitor_id and group_key in env variables.
    logging.info('Checking Shinobi')
    image_loc = Shinobi.GetMonitorImage('tFQOqEJbXK', 'QqMhCbk4hz')
    Slack.UploadFile(image_loc, 'test.jpg')


def DailySummary():
    message_lines = []
    sunlight = Query.HoursOfSunlight()
    message_lines.append(f'{sunlight:.1f} hours of sunlight in the last 24 hours')
    temp_range = Query.TempRange()
    message_lines.append(f'Temp range: {temp_range} Celcius')
    Slack.SendMessage(message='\n'.join(message_lines))


def SetSchedule():
    PingCurrentWeather()
    schedule.every(5).minutes.do(PingCurrentWeather)

    PingForecast()
    schedule.every().day.at("09:00").do(PingForecast)
    schedule.every().day.at("18:00").do(PingForecast)

    PingShinobi()
    schedule.every().day.at("09:00").do(PingShinobi)

    DailySummary()
    schedule.every().day.at("09:00").do(DailySummary)


if __name__ == '__main__':
    SetSchedule()
    while True:
        try:
            schedule.run_pending()
        except Exception as e:
            logging.exception(e)
        time.sleep(60)  # wait one minute
