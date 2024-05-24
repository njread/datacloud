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
    SALESFORCE_DATA_CLOUD_ACCESS_TOKEN = os.getenv('SALESFORCE_ACCESS_TOKEN')
    if not SALESFORCE_DATA_CLOUD_ENDPOINT or not SALESFORCE_DATA_CLOUD_ACCESS_TOKEN:
        raise ValueError("Missing necessary environment variables.")
except Exception as e:
    logging.error(f"Error loading environment variables: {e}")
    sys.exit(1)

# In-memory store for simplicity (use a database in production)
preview_counts = {}

@app.route('/')
def index():
    return 'Hello, this is the home page of your Flask app running on Heroku!'

@app.route('/box-webhook', methods=['POST'])
def box_webhook():
    event = request.json
    
    if event.get('trigger') == 'FILE.PREVIEWED':
        handle_file_previewed(event)
    elif event.get('trigger') == 'FILE.UPLOADED':
        handle_file_uploaded(event)
    
    return jsonify({'status': 'ignored'}), 200

def handle_file_previewed(event):
    user_id = event['created_by']['id']
    file_id = event['source']['id']
    
    # Update the preview count
    if file_id not in preview_counts:
        preview_counts[file_id] = 0
    preview_counts[file_id] += 1
    
    previewed_at = event['created_at']
    preview_count = preview_counts[file_id]
    
    data = {
        "data": [{
            "Boxuser": user_id,
            "BoxFileID": file_id,
            "Boxenterpriseid": 1164695563,
            "PreviewCount": preview_count,
            "PreviewedAt": previewed_at
        }]
    }

    headers = {
        'Authorization': f'Bearer {SALESFORCE_DATA_CLOUD_ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    response = requests.post(SALESFORCE_DATA_CLOUD_ENDPOINT, json=data, headers=headers)
    
    if response.status_code == 202:
        logging.info('Salesforce data cloud update success for preview')
    else:
        logging.error('Salesforce data cloud update error for preview: ' + response.text)

def handle_file_uploaded(event):
    user_id = event['created_by']['id']
    user_email = event['created_by']['login']
    file_name = event['source']['name']
    file_id = event['source']['id']
    uploaded_at = event['created_at']
    folder_id = event['source']['parent']['id']
    folder_name = event['source']['parent']['name']
    
    print(f"User {user_id} uploaded file {file_name} file id {file_id} at {uploaded_at}")
    
    data = {
        "data": [{
            "Boxuserid": user_id,
            "BoxFilename": file_name,
            "BoxFileID": file_id,
            "Boxenterpriseid": 1164695563,
        }]
    }

    headers = {
        'Authorization': f'Bearer {SALESFORCE_DATA_CLOUD_ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    response = requests.post(SALESFORCE_DATA_CLOUD_ENDPOINT, json=data, headers=headers)
    
    if response.status_code == 202:
        logging.info('Salesforce data cloud update success for upload')
    else:
        logging.error('Salesforce data cloud update error for upload: ' + response.text)
        return jsonify({'status': 'error', 'message': response.text}), response.status_code

    # Metadata update and script execution
    try:
        # Update metadata with AI insights
        AIresponse = requests.get(url=f"https://api.box.com/2.0/metadata_instances/suggestions?item=file_{file_id}&scope=enterprise_964447513&template_key=aitest&confidence=experimental",
                                  headers={"Authorization": "Bearer CB0mFZO18AeE2exZwodJHxY49pvZu5Ll"})
        print(AIresponse.text)
        
        if AIresponse.status_code == 200:
            print(f"Metadata update successful: {AIresponse.text}")
            AIresponsedata = AIresponse.json()
            MetadtaDataTemplate = AIresponsedata['$templateKey']
            order_number = AIresponsedata['suggestions']['orderNumber']
            invoice_number = AIresponsedata['suggestions']['invoiceNumber']
            invoice_date = AIresponsedata['suggestions']['invoiceDate']
            total_amount = AIresponsedata['suggestions']['total']
            
            metadata_data = {
                "data": [{
                    "Boxuserid": user_id,
                    "BoxFilename": file_name,
                    "BoxFileID": file_id,
                    "BoxMetadatatemplate": MetadtaDataTemplate,
                    "BoxMetadataAttribute": f"Order Number:{order_number}, Invoice Number: {invoice_number}, Invoice Date: {invoice_date}, Total Amount: {total_amount}",
                    "BoxFolderID": folder_id,
                    "BoxFoldername": folder_name,
                    "Boxuser": user_email,
                    "BoxCountOfPreviews": preview_counts.get(file_id, 0)
                }]
            }

            response = requests.post(SALESFORCE_DATA_CLOUD_ENDPOINT, json=metadata_data, headers=headers)
            
            if response.status_code == 202:
                logging.info('Metadata data cloud update success')
            else:
                logging.error('Metadata data cloud update error: ' + response.text)
        else:
            print(f"Metadata update failed: {AIresponse.text}")

    except Exception as e:
        logging.error(f"Error in metadata update: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
