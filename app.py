#THIS IS A LOCAL SERVER HOSTEL ECHO WORKING MODEL. USED NGROK FLASK AND WHATSAPP WEBHOOKS

import json
import requests
from flask import Flask, request

app = Flask(__name__)

# Replace with your own tokens
VERIFY_TOKEN = 'master'
PAGE_ACCESS_TOKEN = 'EAAf1LuaZAdXYBO3ElRpQU9QEyXGjNFInOcxfJT9erbqsR2ekk6MgRqWFvkrZCrlPEZBVWWNPRxAMSBQNNiiUGa2iZBYZCSZCPTTfpB34AHvW0ZBPkmKQHuG4pgpMxPTj88RyuOcyZCvGYsbaucVELzZCxU7zMbZCf8pqRK1i8tI8zo91MZAwVG1n4WHNSVvtvHqrvc8vIG3FoTMgGRD9cfx6VYlK0oaa3ZCXgXZCC' 
PHONE_NUMBER_ID = '722691857585490'  # Replace this with your actual phone number ID

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

if __name__ == "__main__":
    app.run(debug=True)
