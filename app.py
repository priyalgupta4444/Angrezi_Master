import json
import requests
from flask import Flask, request
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.memory import ConversationBufferMemory

app = Flask(__name__)

# Configuration - replace these with your actual credentials
VERIFY_TOKEN = 'masterzi'
PAGE_ACCESS_TOKEN = 'EAAbfRdydpyUBO2a8Mqs1t1aFgYmik8YgBZBKIqLGk03FHQZBEDSFzrZC63wHOGiS7GnnESEcDSQ92ZBEPZB9ehHFJvlx4xG6LAmUM583IOEJZAYaOw1ZCE9nNBqhXshhJQMDMHkvUFilEP6MvjPSZBpTWvBsSZClHPOBsuybUOQMUn2My3T3gqZALQ1AGMibcdtamSz4fihfSZAIfgrZA3dnX1B5W5IglzrQPxMZD'
PHONE_NUMBER_ID = '707308075793480'
OPENAI_API_KEY = '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'

# Initialize LLM components
chat_model = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7, api_key=OPENAI_API_KEY)
user_memories = {}  # {phone_number: ConversationBufferMemory}

def get_memory(phone_number: str):
    """Get or create conversation memory for a user"""
    if phone_number not in user_memories:
        user_memories[phone_number] = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
    return user_memories[phone_number]

@app.route('/', methods=['GET'])
def index():
    return "WhatsApp bot is live!", 200

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Webhook verification - PRESERVED AZURE PATTERN
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

        # PRESERVED AZURE MESSAGE PROCESSING STRUCTURE
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

                            # LLM PROCESSING - INTEGRATED WHILE PRESERVING FLOW
                            try:
                                memory = get_memory(sender_id)
                                chat_history = memory.load_memory_variables({})['chat_history']
                               
                                response = chat_model.invoke([
                                    SystemMessage(content="You're a helpful English teacher."),
                                    *chat_history,
                                    HumanMessage(content=message_text)
                                ])
                               
                                # Save context
                                memory.save_context(
                                    {"input": message_text},
                                    {"output": response.content}
                                )
                               
                                # Send response using preserved Azure pattern
                                print(f"Sending response to {sender_id}")
                                send_message(sender_id, response.content)
                               
                            except Exception as e:
                                print(f"Error in LLM processing: {str(e)}")
                                # Fallback to echo pattern on error
                                send_message(sender_id, f"Echo: {message_text}")

        return "EVENT_RECEIVED", 200

def send_message(recipient_id, message_text):
    """PRESERVED AZURE MESSAGE SENDING PATTERN"""
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
