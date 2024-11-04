#author Nick Read
import os
import sys
import logging
import requests
from flask import Flask, request, jsonify
from threading import Thread
import json
from utils import (
    get_preview_count,
    fetch_all_metadata_suggestions,
    update_salesforce,
    apply_metadata_to_file,
    template_extractors,
    list_metadata_templates,
    get_template_schema,
    update_metadata,
    is_metadata_template_applied,
    get_available_templates,
    calculate_filled_percentage,
    fetch_metadata_suggestions_via_ai,
    generate_prompt_from_template
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
    user_id = event['created_by']['id']
    item_id = event['source']['id']
    user_email = event['created_by']['login']
    file_name = event['source']['name']
    file_id = event['source']['id']
    folder_id = event['source']['parent']['id']
    folder_name = event['source']['parent']['name']

    logging.info(f"User {user_id} triggered {event_type} event for file {file_name} (ID: {file_id})")

    # Default data to send to Salesforce
    data = {
        "data": [{
            "Boxuserid": user_id,
            "itemID": item_id,
            "BoxFilename": file_name,
            "BoxFileID": file_id,
            "BoxFileID_Text": file_id,
            "Boxenterpriseid": 1164695563,
            "BoxCountOfPreviews": 0,
        }]
    }

    if event_type == 'preview':
        preview_count = get_preview_count(file_id, BOX_API_TOKEN)
        data['data'][0]["BoxCountOfPreviews"] = preview_count
        logging.info(f"User {user_id} previewed file {file_name} (ID: {file_id}) with a preview count of {preview_count}")

    available_templates = get_available_templates(BOX_API_TOKEN)
    all_suggestions = fetch_all_metadata_suggestions(file_id, BOX_API_TOKEN, available_templates)

    highest_percentage_filled = 0
    best_template_key = None
    best_template_suggestions = None
    templates_to_apply = []

    for template_key, suggestions in all_suggestions:
        if template_key not in template_schemas:
            template_schemas[template_key] = get_template_schema(template_key, BOX_API_TOKEN)

        schema = template_schemas[template_key]
        filled_percentage = calculate_filled_percentage(suggestions, schema)

        logging.info(f"Template {template_key} has {filled_percentage * 100}% fields filled.")

        if filled_percentage > highest_percentage_filled:
            highest_percentage_filled = filled_percentage
            best_template_key = template_key
            best_template_suggestions = suggestions
        
        # Check if template is over 80% filled
        if filled_percentage >= 0.50:
            templates_to_apply.append((template_key, suggestions))

    if best_template_key and best_template_suggestions:
        templates_to_apply.append((best_template_key, best_template_suggestions))

    for metadata_template, best_template_suggestions in templates_to_apply:
        schema = template_schemas[metadata_template]
        extractor = template_extractors.get(metadata_template, lambda x, y: {})
        metadata_attributes = extractor(best_template_suggestions, schema)
        metadata_str = ', '.join(f"{k}: {v}" for k, v in metadata_attributes.items())

        # Check if metadata template is already applied
        is_applied, existing_metadata = is_metadata_template_applied(file_id, metadata_template, BOX_API_TOKEN)
        if is_applied:
            logging.info(f"Metadata template {metadata_template} already applied to file {file_id}. Updating metadata.")
            update_metadata(file_id, metadata_attributes, metadata_template, BOX_API_TOKEN)
        else:
            logging.info(f"Metadata template {metadata_template} not applied to file {file_id}. Applying metadata.")
            apply_metadata_to_file(file_id, metadata_attributes, metadata_template, BOX_API_TOKEN)

        data['data'][0].update({
            "BoxMetadatatemplate": metadata_template,
            "BoxMetadataAttribute": metadata_str,
            "BoxFolderID": folder_id,
            "BoxFolderID_Text": folder_id,
            "BoxFoldername": folder_name,
            "Boxuser": user_email,
        })
    logging.info(f"Data to send to Salesforce: {data}")
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