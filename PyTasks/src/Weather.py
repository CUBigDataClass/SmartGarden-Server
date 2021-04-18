import os
import requests
import logging
import sys
import re
from datetime import datetime

# Logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(asctime)s-%(levelname)s: %(message)s')

# Config OpenWeatherAPI
key = os.environ['OPEN_WEATHER_API_KEY']
zip_code = os.environ['ZIP_CODE']
open_weather_api_url = 'https://api.openweathermap.org'
forecast_url = f'{open_weather_api_url}/data/2.5/onecall'
current_weather_url = f'{open_weather_api_url}/data/2.5/weather'


'''
Current Weather
'''


def FetchCurrentWeather():
    '''Get current weather from OpenWeatherAPI'''
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
    '''Renames and returns only the important fields from raw OpenWeatherAPI response'''
    return {  # InfluxDB is picky about types
        'open_weather_temp': float(current_weather['main']['temp']),
        'open_weather_humidity': int(current_weather['main']['humidity']),
        'open_weather_wind_speed': float(current_weather['wind']['speed']),
        'open_weather_cloud_cover': int(current_weather['clouds']['all']),
        'open_weather_daylight_hours': float((current_weather['sys']['sunset'] - current_weather['sys']['sunrise']) / (60 * 60)),
    }


'''
Forecast
'''


def FetchForecast():
    '''Get 2-day hourly forcast via OneCall API'''
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
    '''Generates a string showing a summary of the 2-day, hourly forecast.'''
    warnings = {}
    time = ''

    tracking = {
        'temp_low': {
            'W': lambda x: x['temp'] < 10,
            'C': lambda x: x['temp'] < 0,
        },
        'temp_high': {
            'W': lambda x: x['temp'] > 25,
            'C': lambda x: x['temp'] > 30,
        },
        'high_wind': {
            'W': lambda x: x['wind_speed'] > 7 or x['wind_gust'] > 10,
            'C': lambda x: x['wind_speed'] > 12 or x['wind_gust'] > 15,
        },
        'rain': {
            'W': lambda x: x['pop'] > 0,
            'C': lambda x: x['pop'] >= 0.5,
        }
    }

    for hour in forecast['hourly']:  # Assumes forecast is sorted in datetime order
        dt = datetime.fromtimestamp(hour['dt'])

        weekday_map = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        time += f'{weekday_map[dt.weekday()]}{dt.hour}'

        for metric in tracking:
            if metric not in warnings:
                warnings[metric] = ''

            status = '.'
            if 'W' in tracking[metric]:
                if tracking[metric]['W'](hour):
                    status = 'W'
            if 'C' in tracking[metric]:
                if tracking[metric]['C'](hour):
                    status = 'C'
            warnings[metric] += status

    return {
        'warnings': warnings,
        'time': time
    }


def SummarizeWarning(warning, time):
    summaries = []
    for x in re.finditer('W*[WC]C*W*', warning):
        span = x.span()
        start = time[span[0]]
        end = time[min(span[1], len(time) - 1)]
        summary = f'{start[0]} at {start[1]}:00 until {end[0]} at {end[1]}:00: {x.group(0)}'
        summaries.append(summary)
    return summaries


def ForecastMessage(summary):
    time = re.findall('([A-Za-z]+)(\d+)', summary['time'])
    message_lines = []
    for metric in summary['warnings']:
        summaries = SummarizeWarning(summary['warnings'][metric], time)
        if summaries:
            message_lines.append(metric.upper())
            message_lines += summaries + ['']

    message_lines += ['```'] + [f'{k.upper():<9}: {v}' for k, v in summary['warnings'].items()] + ['```']
    return '\n'.join(message_lines)
