# app.py

import os
import json
import logging
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "707308075793480")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "masterzi")
#MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")


app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return "WhatsApp bot is live!", 200

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Webhook verification
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if mode == 'subscribe' and token == VERIFY_TOKEN:
            print("Webhook verified!")
            return challenge, 200
        else:
            return "Verification failed", 403

    elif request.method == 'POST':
        data = request.get_json()
        print("Received POST data:", json.dumps(data, indent=4))

        # Important: The incoming webhook 'object' is 'whatsapp_business_account' in your logs
        if data.get('object') == 'whatsapp_business_account':
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    value = change.get('value', {})
                    messages = value.get('messages', [])
                    for message in messages:
                        sender_id = message['from']
                        if 'text' in message:
                            message_text = message['text']['body']
                            print(f"Received message: {message_text}")

                            # Debug print before sending response
                            print(f"Sending echo to {sender_id}")
                            send_message(sender_id, f"You said: {message_text}")

        return "EVENT_RECEIVED", 200

def send_message(recipient_id, message_text):
    """Send a message back to the user via WhatsApp Business API"""
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
    print("Message sent:", response.status_code, response.text)

     
