import requests
import logging

def get_preview_count(file_id):
    response = requests.get(
        url=f"https://api.box.com/2.0/file_access_stats/{file_id}",
        headers={"Authorization": "Bearer HHCPsFvvtufkKqH9Vb7EnjyAIB7AH2Nu"}
    )
    if response.status_code == 200 and response.content:
        response_data = response.json()
        return response_data.get('preview_count', 0)
    else:
        logging.error(f"Error fetching preview count: {response.text}")
        return 0

def fetch_metadata_suggestions(file_id):
    response = requests.get(
        url=f"https://api.box.com/2.0/metadata_instances/suggestions?item=file_{file_id}&scope=enterprise_964447513&template_key=contractAi&confidence=experimental",
        headers={"Authorization": "Bearer HHCPsFvvtufkKqH9Vb7EnjyAIB7AH2Nu"}
    )
    return response

def update_salesforce(data, endpoint, access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    response = requests.post(endpoint, json=data, headers=headers)
    return response

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
