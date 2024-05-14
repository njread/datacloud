import os
import sys
import logging
from flask import Flask, request, jsonify
import requests
import hmac
import hashlib
import base64
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configure logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

try:
    SALESFORCE_DATA_CLOUD_ENDPOINT = os.getenv('SALESFORCE_DATA_CLOUD_ENDPOINT')
    SALESFORCE_ACCESS_TOKEN = os.getenv('SALESFORCE_ACCESS_TOKEN')
    BOX_WEBHOOK_SECRET = os.getenv('BOX_WEBHOOK_SECRET')

    if not SALESFORCE_DATA_CLOUD_ENDPOINT or not SALESFORCE_ACCESS_TOKEN or not BOX_WEBHOOK_SECRET:
        raise ValueError("Missing necessary environment variables.")
except Exception as e:
    logging.error(f"Error loading environment variables: {e}")
    sys.exit(1)

def verify_signature(request):
    signature = request.headers.get('Box-Signature')
    if not signature:
        return False
    signature_parts = signature.split(',')
    primary_signature = signature_parts[0].split('=')[1]
    payload = request.data + BOX_WEBHOOK_SECRET.encode()
    expected_signature = base64.b64encode(hmac.new(BOX_WEBHOOK_SECRET.encode(), payload, hashlib.sha256).digest()).decode()
    return hmac.compare_digest(primary_signature, expected_signature)

@app.route('/')
def index():
    return 'Hello, this is the home page of your Flask app running on Heroku!'

@app.route('/box-webhook', methods=['POST'])
def box_webhook():
    if not verify_signature(request):
        return jsonify({'status': 'error', 'message': 'Invalid signature'}), 403

    event = request.json
    if event['event_type'] == 'FILE.PREVIEWED':
        user_id = event['source']['created_by']['id']
        file_name = event['source']['name']
        file_id = event['source']['id']
        previewed_at = event['created_at']

        data = {
            'userId': user_id,
            'fileName': file_name,
            'fileId': file_id,
            'previewedAt': previewed_at
        }

        headers = {
            'Authorization': f'Bearer {SALESFORCE_ACCESS_TOKEN}',
            'Content-Type': 'application/json'
        }
        response = requests.post(SALESFORCE_DATA_CLOUD_ENDPOINT, json=data, headers=headers)

        if response.status_code == 200:
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify({'status': 'error', 'message': response.text}), response.status_code

    return jsonify({'status': 'ignored'}), 200

if __name__ == '__main__':
    app.run(port=3000)
