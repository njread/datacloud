import os
import sys
import logging
from flask import Flask, request, jsonify
import requests
from threading import Thread

app = Flask(__name__)

# Configure logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

# Environment Variables
try:
    SALESFORCE_DATA_CLOUD_ENDPOINT = os.getenv('SALESFORCE_DATA_CLOUD_ENDPOINT')
    SALESFORCE_DATA_CLOUD_ACCESS_TOKEN = os.getenv('SALESFORCE_ACCESS_TOKEN')
    if not SALESFORCE_DATA_CLOUD_ENDPOINT or not SALESFORCE_DATA_CLOUD_ACCESS_TOKEN:
        raise ValueError("Missing necessary environment variables.")
except Exception as e:
    logging.error(f"Error loading environment variables: {e}")
    sys.exit(1)

# Helper functions
def get_preview_count(file_id):
    response = requests.get(
        url=f"https://api.box.com/2.0/file_access_stats/{file_id}",
        headers={"Authorization": "Bearer R58TdhQbsPkTmAQFBQJgjCjh1N5N77J8"}
    )
    response_data = response.json()
    return response_data.get('preview_count', 0)

def fetch_metadata_suggestions(file_id):
    response = requests.get(
        url=f"https://api.box.com/2.0/metadata_instances/suggestions?item=file_{file_id}&scope=enterprise_964447513&template_key=contractAi&confidence=experimental",
        headers={"Authorization": "Bearer R58TdhQbsPkTmAQFBQJgjCjh1N5N77J8"}
    )
    return response

def update_salesforce(data):
    headers = {
        'Authorization': f'Bearer {SALESFORCE_DATA_CLOUD_ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }
    response = requests.post(SALESFORCE_DATA_CLOUD_ENDPOINT, json=data, headers=headers)
    return response

def process_preview_event(event):
    item_id = event['source']['id']
    user_id = event['created_by']['id']
    user_email = event['created_by']['login']
    file_name = event['source']['name']
    file_id = event['source']['id']
    folder_id = event['source']['parent']['id']
    folder_name = event['source']['parent']['name']

    preview_count = get_preview_count(file_id)
    print(f"User {user_id} previewed file {file_name} (ID: {file_id}) with a preview count of {preview_count}")

    ai_response = fetch_metadata_suggestions(file_id)
    if ai_response.status_code == 200:
        ai_data = ai_response.json()
        metadata_template = ai_data.get('$templateKey')
        suggestions = ai_data.get('suggestions', {})
        metadata_attributes = {
            "Client": suggestions.get('client'),
            "Project Name": suggestions.get('projectName'),
            "Assessment and Planning": suggestions.get('assessmentAndPlanning'),
            "Configuration and Setup": suggestions.get('configurationAndSetup'),
            "Deliverables": suggestions.get('deliverables'),
            "Client Specific Dependencies": suggestions.get('clientspecificDependencies'),
            "Project Personnel": suggestions.get('projectPersonnel'),
            "Total Estimated Service Fees": suggestions.get('totalEstimatedServiceFees'),
            "Milestone or Deliverables": suggestions.get('milestoneOrDeliverables')
        }
        metadata_str = ', '.join(f"{k}: {v}" for k, v in metadata_attributes.items())
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
    response = update_salesforce(data)
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

    response = update_salesforce(data)
    if response.status_code == 202:
        print('Salesforce data cloud update success')
    else:
        print(f'Salesforce data cloud update error: {response.text}')

    ai_response = fetch_metadata_suggestions(file_id)
    if ai_response.status_code == 200:
        ai_data = ai_response.json()
        metadata_template = ai_data.get('$templateKey')
        suggestions = ai_data.get('suggestions', {})
        metadata_attributes = {
            "Client": suggestions.get('client'),
            "Project Name": suggestions.get('projectName'),
            "Assessment and Planning": suggestions.get('assessmentAndPlanning'),
            "Configuration and Setup": suggestions.get('configurationAndSetup'),
            "Deliverables": suggestions.get('deliverables'),
            "Client Specific Dependencies": suggestions.get('clientspecificDependencies'),
            "Project Personnel": suggestions.get('projectPersonnel'),
            "Total Estimated Service Fees": suggestions.get('totalEstimatedServiceFees'),
            "Milestone or Deliverables": suggestions.get('milestoneOrDeliverables')
        }
        metadata_str = ', '.join(f"{k}: {v}" for k, v in metadata_attributes.items())
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
        response = update_salesforce(data)
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
