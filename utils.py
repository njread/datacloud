import requests
import logging

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

def fetch_metadata_suggestions(file_id, token):
    try:
        response = requests.get(
            url=f"https://api.box.com/2.0/metadata_instances/suggestions?item=file_{file_id}&scope=enterprise_964447513&template_key=contractAi&confidence=experimental",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching metadata suggestions: {e}")
        return requests.Response()

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
            schema["Assessment and Planning"]: suggestions.get('assessmentAndPlanning'),
            schema["Configuration and Setup"]: suggestions.get('configurationAndSetup'),
            schema["Deliverables"]: suggestions.get('deliverables'),
            schema["Client Specific Dependencies"]: suggestions.get('clientspecificDependencies'),
            schema["Project Personnel"]: suggestions.get('projectPersonnel'),
            schema["Total Estimated Service Fees"]: suggestions.get('totalEstimatedServiceFees'),
            schema["Milestone or Deliverables"]: suggestions.get('milestoneOrDeliverables')
        }
    except KeyError as e:
        logging.error(f"KeyError: {e} - Schema: {schema}")
        return {}

def extract_project_management_ai_attributes(suggestions, schema):
    try:
        return {
            schema["Project Manager"]: suggestions.get('projectManager'),
            schema["Project Status"]: suggestions.get('projectStatus'),
            schema["Start Date"]: suggestions.get('startDate'),
            schema["End Date"]: suggestions.get('endDate'),
            schema["Budget"]: suggestions.get('budget'),
            schema["Resources"]: suggestions.get('resources'),
            schema["Milestones"]: suggestions.get('milestones'),
            schema["Risks"]: suggestions.get('risks')
        }
    except KeyError as e:
        logging.error(f"KeyError: {e} - Schema: {schema}")
        return {}

# Mapping of template keys to extraction functions
template_extractors = {
    "contractAi": extract_contract_ai_attributes,
    "projectManagementAi": extract_project_management_ai_attributes,
    # Add more mappings for other templates
}
