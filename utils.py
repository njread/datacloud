import requests
import logging

def get_preview_count(file_id, token):
    response = requests.get(
        url=f"https://api.box.com/2.0/file_access_stats/{file_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200 and response.content:
        response_data = response.json()
        return response_data.get('preview_count', 0)
    else:
        logging.error(f"Error fetching preview count: {response.text}")
        return 0

def fetch_metadata_suggestions(file_id, token):
    response = requests.get(
        url=f"https://api.box.com/2.0/metadata_instances/suggestions?item=file_{file_id}&scope=enterprise_964447513&template_key=contractAi&confidence=experimental",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response

def update_salesforce(data, endpoint, access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    response = requests.post(endpoint, json=data, headers=headers)
    return response

def apply_metadata_to_file(file_id, metadata, template_key, token):
    url = f"https://api.box.com/2.0/files/{file_id}/metadata/enterprise_27335/{template_key}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    logging.info(f"Applying metadata to file {file_id} with template {template_key}: {metadata}")
    response = requests.post(url, json=metadata, headers=headers)
    if response.status_code == 201:
        logging.info(f"Metadata applied successfully to file {file_id}")
    else:
        logging.error(f"Error applying metadata to file {file_id}: {response.text}")
        logging.debug(f"Response status code: {response.status_code}")
        logging.debug(f"Request payload: {metadata}")

# Template-specific extraction functions
def extract_contract_ai_attributes(suggestions):
    return {
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

def extract_project_management_ai_attributes(suggestions):
    return {
        "Project Manager": suggestions.get('projectManager'),
        "Project Status": suggestions.get('projectStatus'),
        "Start Date": suggestions.get('startDate'),
        "End Date": suggestions.get('endDate'),
        "Budget": suggestions.get('budget'),
        "Resources": suggestions.get('resources'),
        "Milestones": suggestions.get('milestones'),
        "Risks": suggestions.get('risks')
    }

# Mapping of template keys to extraction functions
template_extractors = {
    "contractAi": extract_contract_ai_attributes,
    "projectManagementAi": extract_project_management_ai_attributes,
    # Add more mappings for other templates
}
