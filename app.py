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

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(override=True)

# Fetch environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "masterzi")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o")

# Validate essential environment variables
if not all([OPENAI_API_KEY, PAGE_ACCESS_TOKEN, PHONE_NUMBER_ID]):
    raise EnvironmentError("Missing required environment variables.")

# Set up LangChain chat model and memory
chat_model = ChatOpenAI(model=MODEL_NAME, temperature=0.7, api_key=OPENAI_API_KEY)
user_memories = {}

app = Flask(__name__)

def get_memory(user_id: str):
    if user_id not in user_memories:
        user_memories[user_id] = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
    return user_memories[user_id]

@app.route("/", methods=["GET"])
def home():
    return "Masterzi WhatsApp AI Assistant is running!", 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            logger.info("Webhook verification successful.")
            return challenge, 200
        else:
            logger.warning("Webhook verification failed.")
            return "Verification failed", 403

    elif request.method == "POST":
        try:
            data = request.get_json()
            logger.info("Received data: %s", json.dumps(data, indent=2))

            if data.get("object") != "whatsapp_business_account":
                return jsonify({"error": "Invalid object type"}), 400

            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    messages = value.get("messages", [])

                    for message in messages:
                        sender_id = message.get("from")
                        message_text = message.get("text", {}).get("body")

                        if sender_id and message_text:
                            logger.info(f"Received from {sender_id}: {message_text}")

                            memory = get_memory(sender_id)
                            chat_history = memory.load_memory_variables({})["chat_history"]

                            # Call the LLM
                            response = chat_model.invoke([
                                SystemMessage(content="Your name is Masterzi. You are an encouraging and clear English teacher. Keep your responses friendly and focused on language learning."),
                                *chat_history,
                                HumanMessage(content=message_text)
                            ])

                            # Save conversation
                            memory.save_context({"input": message_text}, {"output": response.content})

                            # Send LLM response
                            send_whatsapp_message(sender_id, response.content)

            return "EVENT_RECEIVED", 200

        except Exception as e:
            logger.exception("Error processing webhook data:")
            return jsonify({"error": str(e)}), 500

def send_whatsapp_message(recipient_id: str, message_text: str):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Content-Type": "application/json"}
    params = {"access_token": PAGE_ACCESS_TOKEN}
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": message_text[:4096]
        }
    }

    try:
        response = requests.post(url, headers=headers, params=params, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Message sent successfully to {recipient_id}")
    except requests.RequestException as e:
        logger.error(f"Failed to send message: {e}")
