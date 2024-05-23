import os
import sys
import logging
from flask import Flask, request, jsonify
import requests
from boxsdk import JWTAuth
from boxsdk import *

app = Flask(__name__)

# Configure logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
try:
    SALESFORCE_DATA_CLOUD_ENDPOINT = os.getenv('SALESFORCE_DATA_CLOUD_ENDPOINT')
    SALESFORCE_DATA_CLOUD_ACCESS_TOKEN = os.getenv('SALESFORCE_ACCESS_TOKEN')
    BOX_CONFIG_FILE = os.getenv('BOX_CONFIG_FILE')
    if not SALESFORCE_DATA_CLOUD_ENDPOINT or not SALESFORCE_DATA_CLOUD_ACCESS_TOKEN or not BOX_CONFIG_FILE:
        raise ValueError("Missing necessary environment variables.")
except Exception as e:
    logging.error(f"Error loading environment variables: {e}")
    sys.exit(1)

#basic rout hello
@app.route('/')
def index():
    return 'Hello, this is the home page of your Flask app running on Heroku!'
#rout for file preview
@app.route('/box-webhook', methods=['POST'])
def box_webhook():
    event = request.json
    
    if event.get('trigger') == 'FILE.PREVIEWED':
        user_id = event['created_by']['id']
        file_name = event['source']['name']
        file_id = event['source']['id']
        previewed_at = event['created_at']
        
        print(f"User {user_id} previewed file {file_name} file id {file_id} at {previewed_at}")
        
        data = {
            "data": [{
                "Boxuser": user_id,
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
            return jsonify({'status': 'success'}), 202
        else:
            return jsonify({'status': 'error', 'message': response.text}), response.status_code

    return jsonify({'status': 'ignored'}), 200
#rout for file upload 
@app.route('/upload', methods=['POST'])
def upload_file():
    event = request.json
    
    if event.get('trigger') == 'FILE.UPLOADED':
        user_id = event['created_by']['id']
        file_name = event['source']['name']
        file_id = event['source']['id']
        uploaded_at = event['created_at']
        
        print(f"User {user_id} uploaded file {file_name} file id {file_id} at {uploaded_at}")
        
        data = {
            "data": [{
                "Boxuser": user_id,
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
            logging.info('Salesforce data cloud update success')
        else:
            logging.error('Salesforce data cloud update error: ' + response.text)
            return jsonify({'status': 'error', 'message': response.text}), response.status_code

        # Metadata update and script execution
        try:
            # Update metadata with AI insights
            configFile = "AI_DemoCreds.json"
            auth = JWTAuth.from_settings_file(configFile)
            auth.authenticate_instance()
            client = LoggingClient(auth)
            BoxAI_metadata_url = f"https://api.box.com/2.0/metadata_instances/suggestions?item=file_{file_id}&scope=enterprise_1164695563&template_key=aitest&confidence=experimental"
            BOX_AI_response = requests.get(BoxAI_metadata_url, headers={"Authorization": f"Bearer {client}"})
            
            if BOX_AI_response.status_code == 200:
                print(f"Metadata update successful: {BOX_AI_response.text}")
                #Make a DataCloud Entry of Metadata
                if event.get('trigger') == 'METADATA.UPDATE':
                    MetadataAttribute = event['created_by']['id']
                    file_name = event['source']['name']
                    file_id = event['source']['id']
                    MetadataValue = event['created_at']
        
                    print(f"Metadata Attributes {MetadataAttribute} of file {file_name} file id {file_id} were updated {MetadataValue}")
        
                    data = {
                        "data": [{
                        "Boxuser": user_id,
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
                
            else:
                print("Metadata update failed: ", response.text)

        except Exception as e:
            logging.error(f"Error in metadata update: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
        
        return jsonify({'status': 'success'}), 202
    
    return jsonify({'status': 'ignored'}), 200
#rout for metadata update
@app.route('/metadata_Update', methods=['UPDATE'])
def update_metadata():
    event = request.json
    if event.get('trigger') == 'Metadata.UPDATED':
        user_id = event['created_by']['id']
        file_name = event['source']['name']
        file_id = event['source']['id']
        Metadata_Attribute = event['created_at']
        Metadata_Value = event['value']

        print(f"User {user_id} updated file {file_name} file id {file_id} 's Metadata Attribute: {Metadata_Attribute} With {Metadata_Value}")
       
        data = {
            "data": [{
                "Boxuser": user_id,
                "BoxFilename": file_name,
                "BoxFileID": file_id,
                "BoxMetadataAttribute": Metadata_Attribute,
                "BoxMetadateValues": Metadata_Value,
                "Boxenterpriseid": 1164695563,
            }]
        }
        headers = {
            'Authorization': f'Bearer {SALESFORCE_DATA_CLOUD_ACCESS_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(SALESFORCE_DATA_CLOUD_ENDPOINT, json=data, headers=headers)
        if response.status_code == 202:
            return jsonify({'status': 'success'}), 202
        else:
            return jsonify({'status': 'error', 'message': response.text}), response.status_code

    return jsonify({'status': 'ignored'}), 200

@app.rout('/box_shared_externally', methods = ['POST'])
def shared_externally():
    event = request.json()
    if event.get('trigger') == 'External.collaboration':
        user_id = event['created_by']['id']
        file_id = event['source']['id']

        data = {
            "data": [{
                "Boxuser": user_id,
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
            return jsonify({'status': 'success'}), 202
        else:
            return jsonify({'status': 'error', 'message': response.text}), response.status_code
    return jsonify({'status': 'ignored'}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
