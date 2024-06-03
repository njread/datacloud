import os
import sys
import logging
from flask import Flask, request, jsonify
import requests
import jwt
import time
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

app = Flask(__name__)

# Configure logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

def get_jwt_token():
    private_key = os.getenv('PRIVATE_KEY').replace('\\n', '\n').encode()
    private_key_passphrase = os.getenv('PRIVATE_KEY_PASSPHRASE').encode()
    
    private_key = serialization.load_pem_private_key(
        private_key,
        password=private_key_passphrase,
        backend=default_backend()
    )
    
    payload = {
        'iss': os.getenv('CLIENT_ID'),
        'sub': os.getenv('USER_ID'),
        'aud': os.getenv('AUTH_URL'),
        'exp': int(time.time()) + 60*3,
        'jti': os.urandom(16).hex()
    }

    token = jwt.encode(payload, private_key, algorithm='RS256')
    return token

def get_access_token():
    jwt_token = get_jwt_token()
    response = requests.post(
        os.getenv('AUTH_URL'),
        data={
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion': jwt_token
        },
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    if response.status_code != 200:
        logging.error(f"Failed to get access token: {response.text}")
        raise Exception("Failed to get access token")
    return response.json()['access_token']

try:
    SALESFORCE_DATA_CLOUD_ENDPOINT = os.getenv('SALESFORCE_DATA_CLOUD_ENDPOINT')
    if not SALESFORCE_DATA_CLOUD_ENDPOINT:
        raise ValueError("Missing necessary environment variables.")
except Exception as e:
    logging.error(f"Error loading environment variables: {e}")
    sys.exit(1)

@app.route('/')
def index():
    print('POST request received')
    return 'Hello, this is the home page of your Flask app running on Heroku!'

@app.route('/box-webhook', methods=['POST'])
def box_webhook():
    event = request.json
    if event.get('trigger') == 'FILE.PREVIEWED':
        user_id = event['created_by']['id']
        user_email = event['created_by']['login']
        file_name = event['source']['name']
        file_id = event['source']['id']
        uploaded_at = event['created_at']
        folder_id = event['source']['parent']['id']
        folder_name = event['source']['parent']['name']

        access_token = get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}

        Preview_response = requests.get(url=f"https://api.box.com/2.0/file_access_stats/{file_id}", headers=headers)
        Preview_response_data = Preview_response.json()
        print(f"Preview response data: {Preview_response_data}")
        Preview_count = Preview_response_data['preview_count']
        
        print(f"User {user_id} previewed file {file_name} file id {file_id} with a preview count of {Preview_count}")
        
        AIresponse = requests.get(url=f"https://api.box.com/2.0/metadata_instances/suggestions?item=file_{file_id}&scope=enterprise_964447513&template_key=contractAi&confidence=experimental", headers=headers)
        print(AIresponse.text)
            
        if AIresponse.status_code == 200:
            print(f"Metadata update successful: {AIresponse.text}")
            AIresponsedata = AIresponse.json()
            MetadtaDataTemplate = AIresponsedata['$templateKey']
            client = AIresponsedata['suggestions']['client']
            project_name = AIresponsedata['suggestions']['projectName']
            a_and_p = AIresponsedata['suggestions']['assessmentAndPlanning']
            config_and_setup = AIresponsedata['suggestions']['configurationAndSetup']
            deliverables = AIresponsedata['suggestions']['deliverables']
            client_dependencies = AIresponsedata['suggestions']['clientspecificDependencies']
            project_presonnel = AIresponsedata['suggestions']['projectPersonnel']
            totalestimatedfees = AIresponsedata['suggestions']['totalEstimatedServiceFees']
            total_deliverables = AIresponsedata['suggestions']['milestoneOrDeliverables']

            data = {
                "data": [{
                    "Boxuserid": user_id,
                    "BoxFilename": file_name,
                    "BoxFileID": file_id,
                    "BoxMetadatatemplate": MetadtaDataTemplate,
                    "BoxMetadataAttribute": f"Client: {client}, Project Name: {project_name}, Assessment and Planning: {a_and_p}, Configuration and Setup: {config_and_setup}, Deliverables: {deliverables}, Client Specific Dependencies: {client_dependencies}, Project Personnel: {project_presonnel}, Total Estimated Service Fees: {totalestimatedfees}, Milestone or Deliverables: {total_deliverables}",
                    "BoxFolderID": folder_id,
                    "BoxFoldername": folder_name, 
                    "Boxuser": user_email,
                    "BoxCountOfPreviews": Preview_count,
                }]
            }

            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            response = requests.post(SALESFORCE_DATA_CLOUD_ENDPOINT, json=data, headers=headers)
            
            if response.status_code == 202:
                return jsonify({'status': 'success'}), 202
            else:
                return jsonify({'status': 'error', 'message': response.text}), response.status_code
        
    if event.get('trigger') == 'FILE.UPLOADED':
        print("File uploaded event received")
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
                "BoxCountOfPreviews": 0,
            }]
        }

        access_token = get_access_token()
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(SALESFORCE_DATA_CLOUD_ENDPOINT, json=data, headers=headers)
        
        if response.status_code == 202:
            logging.info('Salesforce data cloud update success')
        else:
            logging.error('Salesforce data cloud update error: ' + response.text)
            return jsonify({'status': 'error', 'message': response.text}), response.status_code

        try:
            AIresponse = requests.get(url=f"https://api.box.com/2.0/metadata_instances/suggestions?item=file_{file_id}&scope=enterprise_964447513&template_key=contractAi&confidence=experimental", headers=headers)
            print(AIresponse.text)
            
            if AIresponse.status_code == 200:
                print(f"Metadata update successful: {AIresponse.text}")
                AIresponsedata = AIresponse.json()
                MetadtaDataTemplate = AIresponsedata['$templateKey']
                client = AIresponsedata['suggestions']['client']
                project_name = AIresponsedata['suggestions']['projectName']
                a_and_p = AIresponsedata['suggestions']['assessmentAndPlanning']
                config_and_setup = AIresponsedata['suggestions']['configurationAndSetup']
                deliverables = AIresponsedata['suggestions']['deliverables']
                client_dependencies = AIresponsedata['suggestions']['clientspecificDependencies']
                project_presonnel = AIresponsedata['suggestions']['projectPersonnel']
                totalestimatedfees = AIresponsedata['suggestions']['totalEstimatedServiceFees']
                total_deliverables = AIresponsedata['suggestions']['milestoneOrDeliverables']

                data = {
                    "data": [{
                        "Boxuserid": user_id,
                        "BoxFilename": file_name,
                        "BoxFileID": file_id,
                        "BoxMetadatatemplate": MetadtaDataTemplate,
                        "BoxMetadataAttribute": f"Client: {client}, Project Name: {project_name}, Assessment and Planning: {a_and_p}, Configuration and Setup: {config_and_setup}, Deliverables: {deliverables}, Client Specific Dependencies: {client_dependencies}, Project Personnel: {project_presonnel}, Total Estimated Service Fees: {totalestimatedfees}, Milestone or Deliverables: {total_deliverables}",
                        "BoxFolderID": folder_id,
                        "BoxFoldername": folder_name, 
                        "Boxuser": user_email,
                        "BoxCountOfPreviews": 0,
                    }]
                }

                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }
        
                response = requests.post(SALESFORCE_DATA_CLOUD_ENDPOINT, json=data, headers=headers)
                
            else:
                print(f"Metadata update failed: {AIresponse.text}")

        except Exception as e:
            logging.error(f"Error in metadata update: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
        
        return jsonify({'status': 'success'}), 202

    return jsonify({'status': 'ignored'}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
