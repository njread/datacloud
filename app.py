import os
import sys
import logging
from flask import Flask, request, jsonify
from threading import Thread
from utils import get_preview_count, fetch_metadata_suggestions, update_salesforce, apply_metadata_to_file, template_extractors, list_metadata_templates

app = Flask(__name__)

# Configure logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

# Environment Variables
try:
    SALESFORCE_DATA_CLOUD_ENDPOINT = os.getenv('SALESFORCE_DATA_CLOUD_ENDPOINT')
    SALESFORCE_DATA_CLOUD_ACCESS_TOKEN = os.getenv('SALESFORCE_ACCESS_TOKEN')
    BOX_API_TOKEN = os.getenv('BOX_API_TOKEN')  # Add your Box API token
    if not SALESFORCE_DATA_CLOUD_ENDPOINT or not SALESFORCE_DATA_CLOUD_ACCESS_TOKEN or not BOX_API_TOKEN:
        raise ValueError("Missing necessary environment variables.")
except Exception as e:
    logging.error(f"Error loading environment variables: {e}")
    sys.exit(1)

list_metadata_templates(BOX_API_TOKEN)  # List templates at startup for verification

def process_preview_event(event):
    item_id = event['source']['id']
    user_id = event['created_by']['id']
    user_email = event['created_by']['login']
    file_name = event['source']['name']
    file_id = event['source']['id']
    folder_id = event['source']['parent']['id']
    folder_name = event['source']['parent']['name']

    preview_count = get_preview_count(file_id, BOX_API_TOKEN)
    print(f"User {user_id} previewed file {file_name} (ID: {file_id}) with a preview count of {preview_count}")

    ai_response = fetch_metadata_suggestions(file_id, BOX_API_TOKEN)
    if ai_response.status_code == 200 and ai_response.content:
        ai_data = ai_response.json()
        metadata_template = ai_data.get('$templateKey')
        suggestions = ai_data.get('suggestions', {})

        # Select and call the appropriate extraction function
        extractor = template_extractors.get(metadata_template, lambda x: {})
        metadata_attributes = extractor(suggestions)
        metadata_str = ', '.join(f"{k}: {v}" for k, v in metadata_attributes.items())

        # Apply metadata to the file in Box
        apply_metadata_to_file(file_id, metadata_attributes, metadata_template, BOX_API_TOKEN)
    else:
        metadata_template = "ContractAI"
        metadata_str = "Client:, Project Name:, Assessment and Planning:, Configuration and Setup:, Deliverables:, Client Specific Dependencies:, Project Personnel:, Total Estimated Service Fees:, Milestone or Deliverables:"

    data = {
        "data": [{
            "Boxuserid": user_id,
            "BoxFilename": file_name,
            "BoxFileID": file_id,
            "itemID": item_id,
            "BoxMetadatatemplate": metadata_template,
            "BoxMetadataAttribute": metadata_str,
            "BoxFolderID": folder_id,
            "BoxFoldername": folder_name,
            "Boxuser": user_email,
            "BoxCountOfPreviews": preview_count
        }]
    }
    response = update_salesforce(data, SALESFORCE_DATA_CLOUD_ENDPOINT, SALESFORCE_DATA_CLOUD_ACCESS_TOKEN)
    if response.status_code == 202:
        print("Salesforce data cloud update success")
    else:
        print(f"Salesforce data cloud update error: {response.text}")

def process_upload_event(event):
    user_id = event['created_by']['id']
    item_id = event['source']['id']
    user_email = event['created_by']['login']
    file_name = event['source']['name']
    file_id = event['source']['id']
    uploaded_at = event['created_at']
    folder_id = event['source']['parent']['id']
    folder_name = event['source']['parent']['name']

    print(f"User {user_id} uploaded file {file_name} (ID: {file_id}) at {uploaded_at}")

    data = {
        "data": [{
            "Boxuserid": user_id,
            "itemID": item_id,
            "BoxFilename": file_name,
            "BoxFileID": file_id,
            "Boxenterpriseid": 1164695563,
            "BoxCountOfPreviews": 0,
        }]
    }

    response = update_salesforce(data, SALESFORCE_DATA_CLOUD_ENDPOINT, SALESFORCE_DATA_CLOUD_ACCESS_TOKEN)
    if response.status_code == 202:
        print('Salesforce data cloud update success')
    else:
        print(f'Salesforce data cloud update error: {response.text}')

    ai_response = fetch_metadata_suggestions(file_id, BOX_API_TOKEN)
    if ai_response.status_code == 200 and ai_response.content:
        ai_data = ai_response.json()
        metadata_template = ai_data.get('$templateKey')
        suggestions = ai_data.get('suggestions', {})

        # Select and call the appropriate extraction function
        extractor = template_extractors.get(metadata_template, lambda x: {})
        metadata_attributes = extractor(suggestions)
        metadata_str = ', '.join(f"{k}: {v}" for k, v in metadata_attributes.items())

        # Apply metadata to the file in Box
        apply_metadata_to_file(file_id, metadata_attributes, metadata_template, BOX_API_TOKEN)
        
        data = {
            "data": [{
                "Boxuserid": user_id,
                "BoxFilename": file_name,
                "BoxFileID": file_id,
                "itemID": item_id,
                "BoxMetadatatemplate": metadata_template,
                "BoxMetadataAttribute": metadata_str,
                "BoxFolderID": folder_id,
                "BoxFoldername": folder_name,
                "Boxuser": user_email,
                "BoxCountOfPreviews": "0",
            }]
        }
        response = update_salesforce(data, SALESFORCE_DATA_CLOUD_ENDPOINT, SALESFORCE_DATA_CLOUD_ACCESS_TOKEN)
        if response.status_code == 202:
            print("Salesforce data cloud update success")
        else:
            print(f"Salesforce data cloud update error: {response.text}")
    else:
        print(f"Metadata update failed: {ai_response.text}")

# Dispatcher to handle events
def process_webhook(event):
    trigger_handlers = {
        'FILE.PREVIEWED': process_preview_event,
        'FILE.UPLOADED': process_upload_event
    }
    trigger = event.get('trigger')
    handler = trigger_handlers.get(trigger)
    if handler:
        handler(event)
    else:
        logging.warning(f"No handler for trigger: {trigger}")

@app.route('/', methods=['GET'])
def index():
    return 'Hello, Heroku App Is UP!'

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/box-webhook', methods=['POST'])
def box_webhook():
    event = request.json
    thread = Thread(target=process_webhook, args=(event,))
    thread.start()
    return jsonify({'status': 'Webhook received'}), 202

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
