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

@app.route('/')
def index():
    print('POST request received')
    return 'Hello, this is the home page of your Flask app running on Heroku!'

@app.route('/box-webhook', methods=['POST'])
def box_webhook():
   
    event = request.json
    
    # Corrected key check to 'trigger'
    if event.get('trigger') == 'FILE.PREVIEWED':
        user_id = event['created_by']['id']
        user_email = event['created_by']['login']
        file_name = event['source']['name']
        file_id = event['source']['id']
        uploaded_at = event['created_at']
        folder_id = event['source']['parent']['id']
        folder_name = event['source']['parent']['name']

        Preview_response = requests.get(url=f"https://api.box.com/2.0/file_access_stats/{file_id}"
                        , headers={"Authorization": "Bearer WxpuPUuf0PuyDGLjmMHmqIqzIghkp3ww"})
        Preview_response_data = Preview_response.json()
        print(f"Preview response data: {Preview_response_data}")
        Preview_count = Preview_response_data['preview_count']
        
        print(f"User {user_id} previewed file {file_name} file id {file_id} with a preview count of {Preview_count}")
        
        AIresponse = requests.get(url=f"https://api.box.com/2.0/metadata_instances/suggestions?item=file_{file_id}&scope=enterprise_964447513&template_key=aitest&confidence=experimental"
                        , headers={"Authorization": "Bearer WxpuPUuf0PuyDGLjmMHmqIqzIghkp3ww"})
        print(AIresponse.text)
            
        if AIresponse.status_code == 200:
            print(f"Metadata update successful: {AIresponse.text}")
                #Make a DataCloud Entry of Metadata
            AIresponsedata = AIresponse.json()
            MetadtaDataTemplate = AIresponsedata['$templateKey']
            order_number = AIresponsedata['suggestions']['orderNumber']
            invoice_number = AIresponsedata['suggestions']['invoiceNumber']
            invoice_date = AIresponsedata['suggestions']['invoiceDate']
            total_amount = AIresponsedata['suggestions']['total']
            
            data = {
                    "data": [{
                    "Boxuserid": user_id,
                    "BoxFilename": file_name,
                    "BoxFileID": file_id,
                    "BoxMetadatatemplate" : MetadtaDataTemplate,
                    "BoxMetadataAttribute": f"Order Number:{order_number}, Invoice Number: {invoice_number}, Invoice Date: {invoice_date}, Total Amount: {total_amount}",
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

            AIresponse = requests.get(url=f"https://api.box.com/2.0/metadata_instances/suggestions?item=file_{file_id}&scope=enterprise_964447513&template_key=aitest&confidence=experimental"
                        , headers={"Authorization": "Bearer WxpuPUuf0PuyDGLjmMHmqIqzIghkp3ww"})
            print(AIresponse.text)
            
            if AIresponse.status_code == 200:
                print(f"Metadata update successful: {AIresponse.text}")
                #Make a DataCloud Entry of Metadata
                AIresponsedata = AIresponse.json()
                MetadtaDataTemplate = AIresponsedata['$templateKey']
                order_number = AIresponsedata['suggestions']['orderNumber']
                invoice_number = AIresponsedata['suggestions']['invoiceNumber']
                invoice_date = AIresponsedata['suggestions']['invoiceDate']
                total_amount = AIresponsedata['suggestions']['total']



                data = {
                        "data": [{
                        "Boxuserid": user_id,
                        "BoxFilename": file_name,
                        "BoxFileID": file_id,
                        "BoxMetadatatemplate" : MetadtaDataTemplate,
                        "BoxMetadataAttribute": f"Order Number:{order_number}, Invoice Number: {invoice_number}, Invoice Date: {invoice_date}, Total Amount: {total_amount}",
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
                print(f"Metadata update failed:  {response.text}")

        except Exception as e:
            logging.error(f"Error in metadata update: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
        
        return jsonify({'status': 'success'}), 202

    return jsonify({'status': 'ignored'}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
