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
        return response.json()
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
    
    # Ensure metadata values are properly escaped and handle special characters
    escaped_metadata = {k: v.replace("\n", "\\n").replace("u00b7", "\u2022") if isinstance(v, str) else v for k, v in metadata.items()}
    
    logging.info(f"Applying metadata to file {file_id} with template {template_key}: {escaped_metadata}")
    if 'policyNumber' in metadata:
        metadata['policyNumber'] = int(metadata['policyNumber'])
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

    # Generate JSON Patch operations
    patch_operations = []
    for key, value in new_metadata.items():
        if value is not None:  # Only include non-None values
            patch_operations.append({"op": "test", "path": f"/{key}", "value": value})
            patch_operations.append({"op": "replace", "path": f"/{key}", "value": value})
        else:
            patch_operations.append({"op": "remove", "path": f"/{key}"})  # Remove the key if the value is None

    logging.info(f"Updating metadata for file {file_id} with template {template_key}: {patch_operations}")
    try:
        response = requests.put(url, json=patch_operations, headers=headers)
        response.raise_for_status()
        logging.info(f"Metadata updated successfully for file {file_id}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error updating metadata for file {file_id}: {e}")

# Template-specific extraction functions

def extract_order_form_ai_attributes(suggestions, schema):
    logging.info(f"Extracting order form AI attributes: suggestions={suggestions}, schema={schema}")
    try:
        # Normalize the suggestion keys
        normalized_suggestions = {
            k.strip().replace(' ', '').replace('-', '').lower(): v
            for k, v in suggestions.items()
        }
        logging.info(f"Normalized suggestions: {normalized_suggestions}")

        # Normalize the schema keys
        normalized_schema = {
            k.strip().replace(' ', '').replace('-', '').lower(): v
            for k, v in schema.items()
        }
        logging.info(f"Normalized schema: {normalized_schema}")

        # Use normalized keys to extract attributes
        extracted_attributes = {}
        for key in ['ordernumber', 'invoicenumber', 'address', 'invoicedate', 'total']:
            if key in normalized_schema:
                schema_key = normalized_schema[key]
                suggestion_value = normalized_suggestions.get(key)
                if suggestion_value is not None:
                    extracted_attributes[schema_key] = suggestion_value

        logging.info(f"Extracted order form AI attributes: {extracted_attributes}")
        return extracted_attributes
    except Exception as e:
        logging.error(f"Error during attribute extraction: {e}")
        return {}

def extract_contract_ai_attributes(suggestions, schema):
    logging.info(f"Extracting contract AI attributes: suggestions={suggestions}, schema={schema}")
    try:
        # Normalize the suggestion keys
        normalized_suggestions = {
            k.strip().replace(' ', '').replace('-', '').lower(): v
            for k, v in suggestions.items()
        }
        logging.info(f"Normalized suggestions: {normalized_suggestions}")

        # Normalize the schema keys
        normalized_schema = {
            k.strip().replace(' ', '').replace('-', '').lower(): v
            for k, v in schema.items()
        }
        logging.info(f"Normalized schema: {normalized_schema}")

        # Use normalized keys to extract attributes
        extracted_attributes = {}
        keys_to_extract = [
            'contracttype', 'contracteffectivedate', 'contractmasterserviceagreement',
            'client', 'projectname', 'assessmentandplanning', 'configurationandsetup',
            'deliverables', 'clientspecificdependencies', 'projectpersonnel',
            'totalestimatedservicefees', 'milestoneordeliverables'
        ]
        for key in keys_to_extract:
            if key in normalized_schema:
                schema_key = normalized_schema[key]
                suggestion_value = normalized_suggestions.get(key)
                if suggestion_value is not None:
                    extracted_attributes[schema_key] = suggestion_value

        logging.info(f"Extracted contract AI attributes: {extracted_attributes}")
        return extracted_attributes
    except Exception as e:
        logging.error(f"Error during attribute extraction: {e}")
        return {}

def classificationtest_ai_attributes(suggestions, schema):
    logging.info(f"Extracting classification test AI attributes: suggestions={suggestions}, schema={schema}")
    try:
        # Normalize the suggestion keys
        normalized_suggestions = {
            k.strip().replace(' ', '').replace('-', '').lower(): v
            for k, v in suggestions.items()
        }
        logging.info(f"Normalized suggestions: {normalized_suggestions}")

        # Normalize the schema keys
        normalized_schema = {
            k.strip().replace(' ', '').replace('-', '').lower(): v
            for k, v in schema.items()
        }
        logging.info(f"Normalized schema: {normalized_schema}")

        # Use normalized keys to extract attributes dynamically
        extracted_attributes = {}
        for norm_key, schema_key in normalized_schema.items():
            suggestion_value = normalized_suggestions.get(norm_key)
            if suggestion_value is not None:
                extracted_attributes[schema_key] = suggestion_value

        logging.info(f"Extracted classification test AI attributes: {extracted_attributes}")
        return extracted_attributes
    except Exception as e:
        logging.error(f"Error during attribute extraction: {e}")
        return {}
    
def auto_policy(suggestions, schema):
    logging.info(f"Extracting classification test AI attributes: suggestions={suggestions}, schema={schema}")
    try:
        # Normalize the suggestion keys
        normalized_suggestions = {
            k.strip().replace(' ', '').replace('-', '').lower(): v
            for k, v in suggestions.items()
        }
        logging.info(f"Normalized suggestions: {normalized_suggestions}")

        # Normalize the schema keys
        normalized_schema = {
            k.strip().replace(' ', '').replace('-', '').lower(): v
            for k, v in schema.items()
        }
        logging.info(f"Normalized schema: {normalized_schema}")

        # Use normalized keys to extract attributes dynamically
        extracted_attributes = {}
        for norm_key, schema_key in normalized_schema.items():
            suggestion_value = normalized_suggestions.get(norm_key)
            if suggestion_value is not None:
                extracted_attributes[schema_key] = suggestion_value

        logging.info(f"Extracted classification test AI attributes: {extracted_attributes}")
        return extracted_attributes
    except Exception as e:
        logging.error(f"Error during attribute extraction: {e}")
        return {}
template_extractors = {
    # Add more mappings for other templates
    #"contractAi": extract_contract_ai_attributes,
    "classificationtest": classificationtest_ai_attributes,
    #"aitest": extract_order_form_ai_attributes,
    #"uberaiextract": extract_uber_ai_attributes,
    #"nikeplayercontrat": extract_nike_contract_ai_attributes,
    #"nikeallsportsagreement": extract_nike_all_sports_agreement_attributes,
    "autoPolicy": auto_policy
    
}

