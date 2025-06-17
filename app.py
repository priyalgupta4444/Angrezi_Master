# app.py

import os
import json
import logging
import requests
from flask import Flask, request
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(override=True)

# Get environment variables from Azure (already set)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "707308075793480")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "masterzi")

# Flask app
app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return "WhatsApp bot is live!", 200

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        logger.info(f"Webhook verification: mode={mode}, token={token}, challenge={challenge}")

        if mode == 'subscribe' and token == VERIFY_TOKEN:
            logger.info("Webhook verified successfully!")
            return challenge, 200
        else:
            logger.warning("Webhook verification failed!")
            return "Verification failed", 403

    elif request.method == 'POST':
        data = request.get_json()
        logger.info("Incoming webhook POST:\n" + json.dumps(data, indent=2))

        if data.get('object') == 'whatsapp_business_account':
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    value = change.get('value', {})
                    messages = value.get('messages', [])
                    for message in messages:
                        sender_id = message['from']
                        if 'text' in message:
                            text = message['text']['body']
                            logger.info(f"User said: {text}")
                            send_message(sender_id, f"You said: {text}")
        return "EVENT_RECEIVED", 200

def send_message(recipient_id, message_text):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "text",
        "text": {
            "body": message_text
        }
    }
    params = {
        "access_token": PAGE_ACCESS_TOKEN
    }

    response = requests.post(url, headers=headers, params=params, json=payload)
    logger.info(f"Message response: {response.status_code} - {response.text}")
