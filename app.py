import os
import sys
import logging
from flask import Flask, request, jsonify
import requests
from threading import Thread

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

@app.route('/', methods=['POST'])
def index():
    print('POST request received')
    return 'Hello, Heroku App Is UP!'

@app.route('/box-webhook', methods=['POST'])
def box_webhook():
    event = request.json
    thread = Thread(target=process_webhook, args=(event,))
    thread.start()
    return jsonify({'status': 'Webhook received'}), 202

def process_webhook(event):
    if event.get('trigger') == 'FILE.PREVIEWED':
        item_id = event['source']['id']
        user_id = event['created_by']['id']
        user_email = event['created_by']['login']
        file_name = event['source']['name']
        file_id = event['source']['id']
        uploaded_at = event['created_at']
        folder_id = event['source']['parent']['id']
        folder_name = event['source']['parent']['name']

        Preview_response = requests.get(url=f"https://api.box.com/2.0/file_access_stats/{file_id}",
                                        headers={"Authorization": "Bearer UXHuLxV8dUR51d7PIuMW7YSzFuvG5yJp"})
        Preview_response_data = Preview_response.json()
        print(f"Preview response data: {Preview_response_data}")

        Preview_count = Preview_response_data['preview_count']

        print(f"User {user_id} previewed file {file_name} file id {file_id} with a preview count of {Preview_count}")

        AIresponse = requests.get(url=f"https://api.box.com/2.0/metadata_instances/suggestions?item=file_{file_id}&scope=enterprise_964447513&template_key=contractAi&confidence=experimental",
                                  headers={"Authorization": "Bearer UXHuLxV8dUR51d7PIuMW7YSzFuvG5yJp"})
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
                    "itemID": item_id,
                    "BoxMetadatatemplate": MetadtaDataTemplate,
                    "BoxMetadataAttribute": f"Client: {client}, Project Name: {project_name}, Assessment and Planning: {a_and_p}, Configuration and Setup: {config_and_setup}, Deliverables: {deliverables}, Client Specific Dependencies: {client_dependencies}, Project Personnel: {project_presonnel}, Total Estimated Service Fees: {totalestimatedfees}, Milestone or Deliverables: {total_deliverables}",
                    "BoxFolderID": folder_id,
                    "BoxFoldername": folder_name,
                    "Boxuser": user_email,
                    "BoxCountOfPreviews": Preview_count
                }]
            }

            headers = {
                'Authorization': f'Bearer {SALESFORCE_DATA_CLOUD_ACCESS_TOKEN}',
                'Content-Type': 'application/json'
            }

            response = requests.post(SALESFORCE_DATA_CLOUD_ENDPOINT, json=data, headers=headers)
        elif AIresponse.status_code == 503:
            data = {
                "data": [{
                    "Boxuserid": user_id,
                    "BoxFilename": file_name,
                    "BoxFileID": file_id,
                    "itemID": item_id,
                    "BoxMetadatatemplate": "ContractAI",
                    "BoxMetadataAttribute": f"Client:, Project Name:, Assessment and Planning:, Configuration and Setup:, Deliverables:, Client Specific Dependencies: , Project Personnel: , Total Estimated Service Fees: , Milestone or Deliverables: ",
                    "BoxFolderID": folder_id,
                    "BoxFoldername": folder_name,
                    "Boxuser": user_email,
                    "BoxCountOfPreviews": Preview_count
                }]
            }

            headers = {
                'Authorization': f'Bearer {SALESFORCE_DATA_CLOUD_ACCESS_TOKEN}',
                'Content-Type': 'application/json'
            }

            response = requests.post(SALESFORCE_DATA_CLOUD_ENDPOINT, json=data, headers=headers)
            
            if response.status_code == 202:
                print("Salesforce data cloud update success")
            else:
                print(f"Salesforce data cloud update error: {response.text}")

    if event.get('trigger') == 'FILE.UPLOADED':
        print("File uploaded event received")
        user_id = event['created_by']['id']
        item_id = event['source']['id']
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
                "itemID": item_id,
                "BoxFilename": file_name,
                "BoxFileID": file_id,
                "Boxenterpriseid": 1164695563,
                "BoxCountOfPreviews": 0,
            }]
        }

        headers = {
            'Authorization': f'Bearer {SALESFORCE_DATA_CLOUD_ACCESS_TOKEN}',
            'Content-Type': 'application/json'
        }

        response = requests.post(SALESFORCE_DATA_CLOUD_ENDPOINT, json=data, headers=headers)

        if response.status_code == 202:
            print('Salesforce data cloud update success')
        else:
            print(f'Salesforce data cloud update error: {response.text}')

        try:
            AIresponse = requests.get(url=f"https://api.box.com/2.0/metadata_instances/suggestions?item=file_{file_id}&scope=enterprise_964447513&template_key=contractAi&confidence=experimental",
                                      headers={"Authorization": "Bearer UXHuLxV8dUR51d7PIuMW7YSzFuvG5yJp"})
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
                        "itemID": item_id,
                        "BoxMetadatatemplate": MetadtaDataTemplate,
                        "BoxMetadataAttribute": f"Client: {client}, Project Name: {project_name}, Assessment and Planning: {a_and_p}, Configuration and Setup: {config_and_setup}, Deliverables: {deliverables}, Client Specific Dependencies: {client_dependencies}, Project Personnel: {project_presonnel}, Total Estimated Service Fees: {totalestimatedfees}, Milestone or Deliverables: {total_deliverables}",
                        "BoxFolderID": folder_id,
                        "BoxFoldername": folder_name,
                        "Boxuser": user_email,
                        "BoxCountOfPreviews": "0",
                    }]
                }

                headers = {
                    'Authorization': f'Bearer {SALESFORCE_DATA_CLOUD_ACCESS_TOKEN}',
                    'Content-Type': 'application/json'
                }

                response = requests.post(SALESFORCE_DATA_CLOUD_ENDPOINT, json=data, headers=headers)

            else:
                print(f"Metadata update failed: {AIresponse.text}")

        except Exception as e:
            print(f"Error in metadata update: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
