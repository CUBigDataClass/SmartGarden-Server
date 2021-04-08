import requests
import json

token = os.environ['SHINOBI_TOKEN']
headers = {
    'Authorization': f'Bearer {token}',
    'content-type': 'application/json'
}
base_url = 'http://home.lan'
api_url = f'{base_url}/api'
service_url = f'{api_url}/services/homeassistant'
state_url = f'{api_url}/states'

def GetState(entity_id):
    res = requests.get(f'{state_url}/{entity_id}', headers=headers)
    if res.status_code != 200:
        print(res.content)
        assert res.status_code == 200
    return res.json()

def CallService(service, payload):
    res = requests.post(f'{service_url}/{service}', headers=headers, data=json.dumps(payload))
    if res.status_code != 200:
        print(res.content)
        assert res.status_code == 200
    return res.json()
