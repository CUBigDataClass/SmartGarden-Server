import requests
import os
import io
from PIL import Image

key = os.environ['SHINOBI_TOKEN']
base_url = os.environ['SHINOBI_URL']
monitor_id = os.environ['SHINOBI_MONITOR_ID']
group_key = os.environ['SHINOBI_GROUP_KEY']

IMAGE_DIR = "images"


def JpegUrl(monitor_id, group_key):
    '''Generage url for a given monitor and group'''
    return f'{base_url}/{key}/jpeg/{group_key}/{monitor_id}/s.jpg'


def GetMonitorImage(monitor_id, group_key):
    '''
    Get image and save to disk.
    (Slack expects downloaded image, not in memory)
    '''
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)
    res = requests.get(JpegUrl(monitor_id, group_key))
    assert res.status_code == 200
    im = Image.open(io.BytesIO(res.content))
    output_dir = os.path.join(IMAGE_DIR, f'{monitor_id}.jpg')
    im.save(output_dir)
    return output_dir
