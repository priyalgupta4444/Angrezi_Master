# app.py

import os
import json
import logging
import psycopg2
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(override=True)

PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "masterzi")

# PostgreSQL connection setup
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

conn = psycopg2.connect(
    host=DB_HOST,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASS,
    sslmode='require'
)
cursor = conn.cursor()

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Masterzi WhatsApp Bot is running!", 200

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

                            # Check if user exists
                            cursor.execute("SELECT current_level_id FROM users WHERE phone_number = %s", (sender_id,))
                            result = cursor.fetchone()

                            if result:
                                current_level_id = result[0]
                            else:
                                # Insert new user
                                current_level_id = 1
                                cursor.execute("INSERT INTO users (phone_number, current_level_id) VALUES (%s, %s)", (sender_id, current_level_id))
                                conn.commit()

                            # Fetch question from level table
                            cursor.execute("SELECT hindi_question FROM levels WHERE level_id = %s", (current_level_id,))
                            level_row = cursor.fetchone()

                            if level_row:
                                hindi_question = level_row[0]
                                send_whatsapp_message(sender_id, hindi_question)
                            else:
                                send_whatsapp_message(sender_id, "No question found for this level.")

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
