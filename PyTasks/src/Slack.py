import os
from slack_sdk import WebClient
from slack_sdk.webhook import WebhookClient
from slack_sdk.errors import SlackApiError

client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])
# Initialize Slack WebHook
webhook = WebhookClient(os.environ['WEBHOOK_URL'])


def SendMessage(message):
    '''Send a simple text message to the #garden channel.'''
    response = webhook.send(text=message)
    assert response.status_code == 200


def UploadFile(filepath, filename):
    '''
    Upload a file on disk (at filepath) to Slack.
    Filename changes the target name in the Slack Channel. Does not relate to the filename on disk.
    '''
    try:
        response = client.files_upload(channels='garden', file=filepath, title=filename)
        assert response["file"]  # the uploaded file
    except SlackApiError as e:
        # You will get a SlackApiError if "ok" is False
        assert e.response["ok"] is False
        assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
        print(f"Got an error: {e.response['error']}")
