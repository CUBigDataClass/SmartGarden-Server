import os
import requests
import logging
import sys
import time
from datetime import datetime

# Logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(asctime)s-%(levelname)s: %(message)s')

# Config OpenWeatherAPI
key = os.environ['OPEN_WEATHER_API_KEY']
zip_code = os.environ['ZIP_CODE']
open_weather_api_url = 'https://api.openweathermap.org'
forecast_url = f'{open_weather_api_url}/data/2.5/onecall'
current_weather_url = f'{open_weather_api_url}/data/2.5/weather'


##
## Current Weather
##

def FetchCurrentWeather():
    res = requests.get(current_weather_url, params={
        'zip': '80124',
        'appid': key,
        'units': 'metric'
    })
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


##
## Forecast
##

def FetchForecast():
    res = requests.get(forecast_url, params={
        'appid': key,
        'lon': -104.8863,
        'lat': 39.5517,
        'exclude': 'current,minutely,daily',
        'units': 'metric',
    })
    if res.status_code != 200:
        logging.error(res.status_code)
        logging.error(res.content)
    assert res.status_code == 200
    return res.json()


def CheckForecast(forecast):
    points = {
        'temp': '',
        'wind': '',
        'rain': '',
    }

    for hour in forecast['hourly']:
        dt = datetime.fromtimestamp(hour['dt'])

        weekday_map = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        if dt.hour == 0:
            for key in points:
                points[key] += f'|{weekday_map[dt.weekday()]}'

        if dt.hour % 6 == 0:
            for key in points:
                points[key] += f'|{dt.hour}|'

        default_symbol = '・'

        temp_status = default_symbol
        if hour['temp'] < 0: # CRIT: Low Temp
            temp_status = '🥶'
        elif hour['temp'] < 10: # WARN: Low Temp
            temp_status = '❄️'
        elif hour['temp'] > 32: # CRIT: High Temp
            temp_status = '🥵'
        elif hour['temp'] > 28: # WARN: High Temp
            temp_status = '🔥'

        points['temp'] += temp_status


        wind_status = default_symbol
        # CRIT: High Wind
        if hour['wind_speed'] > 12 or hour['wind_gust'] > 15:
            wind_status = '🌪'
        elif hour['wind_speed'] > 7 or hour['wind_gust'] > 10:
            # WARN: High Wind
            wind_status = '💨'

        points['wind'] += wind_status

        rain_status = default_symbol
        if hour['pop'] > 0.5: # WARN: Rain
            rain_status = '🌧'
        points['rain'] += rain_status

    message = '\n'.join([
        f'{k}: {v}' for k,v in points.items()
    ])
    return message
