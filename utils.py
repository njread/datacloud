import requests
import logging
import json

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
        logging.info(f"Available templates: {templates}")
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

def fetch_metadata_suggestions_via_ai(token, file_id, prompt):
    url = "https://api.box.com/2.0/ai/extract"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "prompt": json.dumps(prompt),
        "items": [
            {
                "type": "file",
                "id": file_id
            }
        ]
    }

    try:
        logging.info(f"Sending AI metadata extraction request with payload: {data}")
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        extraction_result = response.json()
        logging.info(f"AI extraction result: {extraction_result}")
        return extraction_result
    except requests.exceptions.RequestException as e:
        logging.error(f"Error extracting AI metadata: {e}")
        logging.error(f"Request payload: {data}")
        return None

def generate_prompt_from_template(template_key, token):
    schema = get_template_schema(template_key, token)
    fields = []
    for display_name, key in schema.items():
        description = f"The {display_name.lower()} in the document"
        fields.append({
            "type": "string",
            "key": key,
            "displayName": display_name,
            "description": description,
            "prompt": f"{display_name} is in the document"
        })
    logging.info(f"Generated prompt for template {template_key}: {fields}")
    return {"fields": fields}

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
    
    escaped_metadata = {k: v.replace("\n", "\\n").replace("u00b7", "\u2022") if isinstance(v, str) else v for k, v in metadata.items()}
    
    logging.info(f"Applying metadata to file {file_id} with template {template_key}: {escaped_metadata}")
    
    try:
        response = requests.post(url, json=escaped_metadata, headers=headers)
        response.raise_for_status()
        logging.info(f"Metadata applied successfully to file {file_id}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error applying metadata to file {file_id}: {e}")
        logging.error(f"Response: {e.response.text}")
        logging.error(f"Payload: {escaped_metadata}")

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

def calculate_filled_percentage(suggestions, schema):
    total_fields = len(schema)
    filled_fields = sum(1 for key in schema.values() if suggestions.get(key) is not None)
    return filled_fields / total_fields if total_fields > 0 else 0

def fetch_all_metadata_suggestions(file_id, token, templates):
    all_suggestions = []
    for template_key in templates:
        if template_key not in template_extractors:
            logging.info(f"Skipping template {template_key} as it is not defined in template_extractors.")
            continue
        try:
            response = requests.get(
                url=f"https://api.box.com/2.0/metadata_instances/suggestions?item=file_{file_id}&scope=enterprise_964447513&template_key={template_key}&confidence=experimental",
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            if response.json().get('suggestions'):
                logging.info(f"Metadata suggestions fetched for template {template_key}: {response.json()}")
                all_suggestions.append((template_key, response.json().get('suggestions')))
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching metadata suggestions for template {template_key}: {e}")
    return all_suggestions

def get_template_schema(template_key, token):
    url = f"https://api.box.com/2.0/metadata_templates/enterprise_964447513/{template_key}/schema"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        schema = response.json()
        attribute_mapping = {field['displayName'].strip(): field['key'] for field in schema['fields']}
        logging.info(f"Fetched template schema for {template_key}: {attribute_mapping}")
        return attribute_mapping
    else:
        logging.error(f"Error fetching metadata template schema: {response.text}")
        return {}

def is_metadata_template_applied(file_id, template_key, token):
    url = f"https://api.box.com/2.0/files/{file_id}/metadata/enterprise_964447513/{template_key}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return True, response.json()
    elif response.status_code == 404:
        return False, None
    else:
        logging.error(f"Error checking metadata template: {response.text}")
        return False, None

def update_metadata(file_id, new_metadata, template_key, token):
    url = f"https://api.box.com/2.0/files/{file_id}/metadata/enterprise_964447513/{template_key}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json-patch+json"
    }

    patch_operations = []
    for key, value in new_metadata.items():
        if value is not None:
            patch_operations.append({"op": "test", "path": f"/{key}", "value": value})
            patch_operations.append({"op": "replace", "path": f"/{key}", "value": value})
        else:
            patch_operations.append({"op": "remove", "path": f"/{key}"})

    logging.info(f"Updating metadata for file {file_id} with template {template_key}: {patch_operations}")
    try:
        response = requests.put(url, json=patch_operations, headers=headers)
        response.raise_for_status()
        logging.info(f"Metadata updated successfully for file {file_id}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error updating metadata for file {file_id}: {e}")

def extract_attributes(suggestions, schema):
    logging.info(f"Extracting attributes: suggestions={suggestions}, schema={schema}")
    try:
        extracted_attributes = {schema[key]: suggestions[key] for key in schema if key in suggestions}
        extracted_attributes = {k: v for k, v in extracted_attributes.items() if v is not None}
        logging.info(f"Extracted attributes: {extracted_attributes}")
        return extracted_attributes
    except KeyError as e:
        logging.error(f"KeyError: {e} - Schema: {schema}")
        return {}

template_extractors = {
    "contractAi": extract_attributes,
    "aitest": extract_attributes,
    "uberaiextract": extract_attributes,
    "nikeplayercontrat": extract_attributes,
    "nikeallsportsagreement": extract_attributes,
}
