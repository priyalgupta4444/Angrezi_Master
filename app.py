# app.py

import os
import json
import logging
import requests
from flask import Flask, request, jsonify
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.memory import ConversationBufferMemory
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "707308075793480")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "masterzi")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

if not OPENAI_API_KEY or not PAGE_ACCESS_TOKEN:
    raise ValueError("Missing required environment variables")

chat_model = ChatOpenAI(model=MODEL_NAME, temperature=0.7, api_key=OPENAI_API_KEY)
user_memories = {}

app = Flask(__name__)

def get_memory(phone_number: str):
    if phone_number not in user_memories:
        user_memories[phone_number] = ConversationBufferMemory(
            memory_key="chat_history", return_messages=True
        )
    return user_memories[phone_number]

@app.route('/', methods=['GET'])
def index():
    return "Masterzi WhatsApp AI Assistant is running!", 200

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            return challenge, 200
        return "Verification failed", 403

    elif request.method == 'POST':
        try:
            data = request.get_json()
            logger.info("Received message: %s", json.dumps(data, indent=2))

            if data.get('object') != 'whatsapp_business_account':
                return jsonify({"status": "invalid object type"}), 400

            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    value = change.get('value', {})
                    for message in value.get('messages', []):
                        sender = message['from']
                        if 'text' in message:
                            text = message['text']['body']
                            logger.info(f"Message from {sender}: {text}")

                            memory = get_memory(sender)
                            chat_history = memory.load_memory_variables({})['chat_history']
                            response = chat_model.invoke([
                                SystemMessage(content="Your Name is Masterzi, and you're a helpful English teacher."),
                                *chat_history,
                                HumanMessage(content=text)
                            ])

                            memory.save_context({"input": text}, {"output": response.content})
                            send_whatsapp_message(sender, response.content)

            return "EVENT_RECEIVED", 200
        except Exception as e:
            logger.error(f"Processing error: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

def send_whatsapp_message(to: str, text: str):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Content-Type": "application/json"}
    params = {"access_token": PAGE_ACCESS_TOKEN}
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": text[:4096]
        }
    }

    try:
        response = requests.post(url, headers=headers, params=params, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Message sent to {to}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send message: {e}")
