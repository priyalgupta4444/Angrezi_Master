# app.py

#VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "masterzi")

import os
import json
import logging
import requests
import psycopg2
from flask import Flask, request, jsonify

# --- Initialization and Configuration ---
app = Flask(__name__)

# Load configuration from environment variables for security
# These should be set in your Azure App Service configuration
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN')
PAGE_ACCESS_TOKEN = os.environ.get('PAGE_ACCESS_TOKEN')
PHONE_NUMBER_ID = os.environ.get('PHONE_NUMBER_ID')

# Azure PostgreSQL database configuration
DB_HOST = os.environ.get('DB_HOST')
DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASS')
DB_PORT = os.environ.get('DB_PORT', '5432') # Default PostgreSQL port

# Setup logging for monitoring and debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- Database Helper Functions ---

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        return conn
    except psycopg2.OperationalError as e:
        logging.error(f"Could not connect to the database: {e}")
        return None

def get_user(phone_number):
    """Fetches a user from the database by phone number."""
    conn = get_db_connection()
    if not conn:
        return None
    user_data = None
    try:
        # Use a 'with' statement for cursor management
        with conn.cursor() as cur:
            cur.execute("SELECT phone_number, current_level_id FROM users WHERE phone_number = %s;", (phone_number,))
            user = cur.fetchone()
            if user:
                user_data = {'phone_number': user[0], 'current_level_id': user[1]}
    except Exception as e:
        logging.error(f"Error fetching user {phone_number}: {e}")
    finally:
        conn.close()
    return user_data

def create_user(phone_number):
    """Creates a new user with current_level_id set to 1."""
    conn = get_db_connection()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            # Start at level 1
            cur.execute("INSERT INTO users (phone_number, current_level_id) VALUES (%s, 1);", (phone_number,))
        conn.commit()
        logging.info(f"Created new user: {phone_number}")
    except Exception as e:
        logging.error(f"Error creating user {phone_number}: {e}")
        conn.rollback()
    finally:
        conn.close()

def update_user_level(phone_number, new_level_id):
    """Updates the user's current level in the database."""
    conn = get_db_connection()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET current_level_id = %s WHERE phone_number = %s;", (new_level_id, phone_number))
        conn.commit()
        logging.info(f"Updated level for user {phone_number} to {new_level_id}")
    except Exception as e:
        logging.error(f"Error updating level for user {phone_number}: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_level_data(level_id):
    """Fetches a level's data (questions) from the database."""
    conn = get_db_connection()
    if not conn:
        return None
    level_data = None
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT level_id, hindi_question, english_question FROM levels WHERE level_id = %s;", (level_id,))
            level = cur.fetchone()
            if level:
                level_data = {'level_id': level[0], 'hindi_question': level[1], 'english_question': level[2]}
    except Exception as e:
        logging.error(f"Error fetching data for level {level_id}: {e}")
    finally:
        conn.close()
    return level_data

# --- WhatsApp API Helper Function ---

def send_whatsapp_message(recipient_id, message_text):
    """Sends a text message to a WhatsApp user via the Graph API."""
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {PAGE_ACCESS_TOKEN}",
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
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        logging.info(f"Message sent to {recipient_id}: {response.status_code} {response.text}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send message to {recipient_id}: {e}")

# --- Core Application Logic ---

def process_user_message(sender_id, message_text):
    """Handles the main logic for processing a user's message."""
    user = get_user(sender_id)

    if not user:
        # New user: create them and send the first question
        logging.info(f"New user detected: {sender_id}. Creating user profile.")
        create_user(sender_id)
        level_1_data = get_level_data(1)
        if level_1_data:
            send_whatsapp_message(sender_id, f"Welcome! Let's start. Your first question is:\n\n{level_1_data['hindi_question']}")
        else:
            logging.error("Could not find data for level 1.")
            send_whatsapp_message(sender_id, "Sorry, there was a problem starting the quiz. Please try again later.")
    else:
        # Existing user: check their answer
        current_level_id = user['current_level_id']
        level_data = get_level_data(current_level_id)

        if not level_data:
            logging.error(f"Could not find data for level {current_level_id} for user {sender_id}.")
            send_whatsapp_message(sender_id, "Sorry, I'm having trouble finding your current question. An administrator has been notified.")
            return

        # Case-insensitive answer check
        correct_answer = level_data['english_question'].strip().lower()
        user_answer = message_text.strip().lower()

        if user_answer == correct_answer:
            # Correct answer: advance to the next level
            logging.info(f"User {sender_id} answered correctly for level {current_level_id}.")
            next_level_id = current_level_id + 1
            next_level_data = get_level_data(next_level_id)

            if next_level_data:
                update_user_level(sender_id, next_level_id)
                send_whatsapp_message(sender_id, f"Correct! 👍\n\nHere is your next question:\n{next_level_data['hindi_question']}")
            else:
                # Quiz completed
                send_whatsapp_message(sender_id, "Congratulations! You have completed all the levels. 🎉")
                logging.info(f"User {sender_id} has completed all levels.")
        else:
            # Incorrect answer: provide correct answer and repeat the question
            logging.info(f"User {sender_id} answered incorrectly for level {current_level_id}.")
            response_text = (
                f"Not quite. The correct answer is: '{level_data['english_question']}'.\n\n"
                f"Let's try that one again:\n{level_data['hindi_question']}"
            )
            send_whatsapp_message(sender_id, response_text)

# --- Flask Webhook Route ---

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """Main webhook endpoint for WhatsApp Cloud API."""
    if request.method == 'GET':
        # Webhook verification (token-based authentication)
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if mode == 'subscribe' and token == VERIFY_TOKEN:
            logging.info("Webhook verified successfully!")
            return challenge, 200
        else:
            logging.warning("Webhook verification failed.")
            return "Verification token is invalid", 403

    if request.method == 'POST':
        # Handle incoming messages
        data = request.get_json()
        logging.info(f"Received webhook data: {json.dumps(data, indent=2)}")

        # Ensure the notification is a message
        if data.get("object") == "whatsapp_business_account":
            try:
                entry = data.get("entry", [])[0]
                change = entry.get("changes", [])[0]
                value = change.get("value", {})
                
                if "messages" in value:
                    message_data = value["messages"][0]
                    if message_data.get("type") == "text":
                        sender_id = message_data["from"]
                        message_text = message_data["text"]["body"]
                        
                        logging.info(f"Processing message from {sender_id}: '{message_text}'")
                        process_user_message(sender_id, message_text)

            except (IndexError, KeyError) as e:
                logging.error(f"Error parsing webhook payload: {e}\nData: {data}")
                # Don't crash, just log the error and return
            except Exception as e:
                logging.error(f"An unexpected error occurred: {e}")
                return "Internal Server Error", 500

        return "EVENT_RECEIVED", 200

    # Handle other methods if necessary
    return "Method Not Allowed", 405

if __name__ == "__main__":
    # This block is for local development.
    # Azure App Service will use a Gunicorn server to run the 'app' object.
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)), debug=True)
