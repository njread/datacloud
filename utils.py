import requests
import logging

def get_available_templates(token):
    url = "https://api.box.com/2.0/metadata_templates/enterprise_964447513"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        templates = response.json()
        return [template['templateKey'] for template in templates['entries']]
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching metadata templates: {e}")
        return []

def get_preview_count(file_id, token):
    try:
        response = requests.get(
            url=f"https://api.box.com/2.0/file_access_stats/{file_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        response_data = response.json()
        return response_data.get('preview_count', 0)
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching preview count: {e}")
        return 0

def fetch_metadata_suggestions(file_id, token, templates):
    for template_key in templates:
        try:
            response = requests.get(
                url=f"https://api.box.com/2.0/metadata_instances/suggestions?item=file_{file_id}&scope=enterprise_964447513&template_key={template_key}&confidence=experimental",
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            if response.json().get('suggestions'):
                logging.info(f"Metadata suggestions fetched for template {template_key}: {response.json()}")
                return response, template_key
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching metadata suggestions for template {template_key}: {e}")
    return None, None

def update_salesforce(data, endpoint, access_token):
    try:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        response = requests.post(endpoint, json=data, headers=headers)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f"Error updating Salesforce: {e}")
        return requests.Response()

def apply_metadata_to_file(file_id, metadata, template_key, token):
    url = f"https://api.box.com/2.0/files/{file_id}/metadata/enterprise_964447513/{template_key}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    logging.info(f"Applying metadata to file {file_id} with template {template_key}: {metadata}")
    try:
        response = requests.post(url, json=metadata, headers=headers)
        response.raise_for_status()
        logging.info(f"Metadata applied successfully to file {file_id}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error applying metadata to file {file_id}: {e}")

def list_metadata_templates(token):
    url = "https://api.box.com/2.0/metadata_templates/schema"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        templates = response.json()
        logging.info(f"Available templates: {templates}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error listing metadata templates: {e}")

def get_template_schema(template_key, token):
    url = f"https://api.box.com/2.0/metadata_templates/enterprise_964447513/{template_key}/schema"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        schema = response.json()
        attribute_mapping = {field['displayName']: field['key'] for field in schema['fields']}
        logging.info(f"Fetched template schema for {template_key}: {attribute_mapping}")
        return attribute_mapping
    else:
        logging.error(f"Error fetching metadata template schema: {response.text}")
        return {}

# Template-specific extraction functions
def extract_contract_ai_attributes(suggestions, schema):
    try:
        return {
            schema["Client"]: suggestions.get('client'),
            schema["Project Name"]: suggestions.get('projectName'),
            schema["Assessment And Planning"]: suggestions.get('assessmentAndPlanning'),
            schema["Configuration and Setup"]: suggestions.get('configurationAndSetup'),
            schema["Deliverables"]: suggestions.get('deliverables'),
            schema["Client-Specific Dependencies"]: suggestions.get('clientspecificDependencies'),
            schema["Project Personnel"]: suggestions.get('projectPersonnel'),
            schema["Total Estimated Service Fees"]: suggestions.get('totalEstimatedServiceFees'),
            schema["Milestone Or Deliverables"]: suggestions.get('milestoneOrDeliverables')
        }
    except KeyError as e:
        logging.error(f"KeyError: {e} - Schema: {schema}")
        return {}

def extract_sales_order_ai_attributes(suggestions, schema):
    try:
        return {
            schema["Order Number"]: suggestions.get('orderNumber'),
            schema["Invoice Number"]: suggestions.get('invoiceNumber'),
            schema["Address"]: suggestions.get('address'),
            schema["INVOICE DATE"]: suggestions.get('invoiceDate'),
            schema["Total"]: suggestions.get('total'),
        }
    except KeyError as e:
        logging.error(f"KeyError: {e} - Schema: {schema}")
        return {}

# Mapping of template keys to extraction functions
template_extractors = {
    "contractAi": extract_contract_ai_attributes,
    "salesOrderAi": extract_sales_order_ai_attributes,
    # Add more mappings for other templates
}
