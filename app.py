import os
import sys
import logging
from flask import Flask, request, jsonify
from threading import Thread
from utils import (
    get_preview_count,
    fetch_metadata_suggestions,
    update_salesforce,
    apply_metadata_to_file,
    template_extractors,
    list_metadata_templates,
    get_template_schema
)

app = Flask(__name__)

# Configure logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

# Environment Variables
required_env_vars = [
    'SALESFORCE_DATA_CLOUD_ENDPOINT',
    'SALESFORCE_ACCESS_TOKEN',
    'BOX_API_TOKEN'
]

missing_env_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_env_vars:
    logging.error(f"Missing environment variables: {', '.join(missing_env_vars)}")
    sys.exit(1)

SALESFORCE_DATA_CLOUD_ENDPOINT = os.getenv('SALESFORCE_DATA_CLOUD_ENDPOINT')
SALESFORCE_DATA_CLOUD_ACCESS_TOKEN = os.getenv('SALESFORCE_ACCESS_TOKEN')
BOX_API_TOKEN = os.getenv('BOX_API_TOKEN')

list_metadata_templates(BOX_API_TOKEN)  # List templates at startup for verification

# Cache for template schemas to avoid repeated API calls
template_schemas = {}

def process_event(event, event_type):
    item_id = event['source']['id']
    user_id = event['created_by']['id']
    user_email = event['created_by']['login']
    file_name = event['source']['name']
    file_id = event['source']['id']
    folder_id = event['source']['parent']['id']
    folder_name = event['source']['parent']['name']
    data = {
        "data": [{
            "Boxuserid": user_id,
            "BoxFilename": file_name,
            "BoxFileID": file_id,
            "itemID": item_id,
            "BoxFolderID": folder_id,
            "BoxFoldername": folder_name,
            "Boxuser": user_email,
            "BoxCountOfPreviews": 0  # Default value
        }]
    }

    if event_type == 'preview':
        preview_count = get_preview_count(file_id, BOX_API_TOKEN)
        data['data'][0]["BoxCountOfPreviews"] = preview_count
        logging.info(f"User {user_id} previewed file {file_name} (ID: {file_id}) with a preview count of {preview_count}")

    ai_response = fetch_metadata_suggestions(file_id, BOX_API_TOKEN)
    if ai_response.status_code == 200 and ai_response.content:
        ai_data = ai_response.json()
        metadata_template = ai_data.get('$templateKey')
        suggestions = ai_data.get('suggestions', {})

        if metadata_template not in template_schemas:
            template_schemas[metadata_template] = get_template_schema(metadata_template, BOX_API_TOKEN)

        schema = template_schemas[metadata_template]
        extractor = template_extractors.get(metadata_template, lambda x, y: {})
        metadata_attributes = extractor(suggestions, schema)
        metadata_str = ', '.join(f"{k}: {v}" for k, v in metadata_attributes.items())
        apply_metadata_to_file(file_id, metadata_attributes, metadata_template, BOX_API_TOKEN)
        data['data'][0].update({
            "BoxMetadatatemplate": metadata_template,
            "BoxMetadataAttribute": metadata_str
        })
    else:
        logging.error(f"Failed to fetch metadata suggestions for file {file_id}: {ai_response.text}")

    response = update_salesforce(data, SALESFORCE_DATA_CLOUD_ENDPOINT, SALESFORCE_DATA_CLOUD_ACCESS_TOKEN)
    if response.status_code == 202:
        logging.info("Salesforce data cloud update success")
    else:
        logging.error(f"Salesforce data cloud update error: {response.text}")

def process_webhook(event):
    trigger_handlers = {
        'FILE.PREVIEWED': lambda e: process_event(e, 'preview'),
        'FILE.UPLOADED': lambda e: process_event(e, 'upload')
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
