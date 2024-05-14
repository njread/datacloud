import os
import sys
import logging
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Configure logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

try:
    SALESFORCE_DATA_CLOUD_ENDPOINT = os.getenv('SALESFORCE_DATA_CLOUD_ENDPOINT')
    SALESFORCE_ACCESS_TOKEN = os.getenv('SALESFORCE_ACCESS_TOKEN')
    if not SALESFORCE_DATA_CLOUD_ENDPOINT or not SALESFORCE_ACCESS_TOKEN:
        raise ValueError("Missing necessary environment variables.")
except Exception as e:
    logging.error(f"Error loading environment variables: {e}")
    sys.exit(1)

@app.route('/')
def index():
    return 'Hello, this is the home page of your Flask app running on Heroku!'

@app.route('/box-webhook', methods=['POST'])
def box_webhook():
    # Log the request headers and data for debugging
    logging.debug(f"Request headers: {request.headers}")
    logging.debug(f"Request data: {request.data}")
    
    # Process the event without verifying the signature
    event = request.json
    logging.debug(f"Received event: {event}")
    
    # Corrected key check to 'trigger'
    if event.get('trigger') == 'FILE.PREVIEWED':
        user_id = event['created_by']['id']
        file_name = event['source']['name']
        file_id = event['source']['id']
        previewed_at = event['created_at']
        
        logging.debug(f"User {user_id} previewed file {file_name} at {previewed_at}")
        
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
