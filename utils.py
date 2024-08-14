#git rebase
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
    
    url = "https://api.box.com/2.0/ai/extract_structured"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    for template_key in templates:
        if template_key not in template_extractors:
            continue

        # Prepare the payload for the extract_structured endpoint
        data = {
            "metadata_template": {
                "type": "metadata_template",
                "scope": "enterprise_964447513",
                "template_key": template_key
            },
            "items": [
                {
                    "type": "file",
                    "id": file_id
                }
            ]
        }

        try:
            logging.info(f"Sending AI metadata extraction request for template {template_key} with payload: {data}")
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            # Extract request ID from the response headers
            request_id = response.headers.get('Box-Request-Id', 'N/A')
            logging.info(f"Box Request ID: {request_id}")

            suggestions = response.json().get('suggestions', [])
            if suggestions:
                logging.info(f"Metadata suggestions fetched for template {template_key}: {suggestions}")
                all_suggestions.append((template_key, suggestions))
            else:
                logging.info(f"No suggestions found for template {template_key}. Box Request ID: {request_id}")
        
        except requests.exceptions.RequestException as e:
            try:
                error_response = e.response.json()
                request_id = error_response.get('request_id', 'N/A')
                logging.error(f"Error extracting AI metadata for template {template_key}. Box Request ID: {request_id}")
                logging.error(f"Error message: {error_response.get('message', 'No error message')}")
            except (ValueError, AttributeError):  # Handles case when response is not JSON or has no request_id
                request_id = response.headers.get('X-Box-Request-Id', 'N/A') if response else 'N/A'
                logging.error(f"Error extracting AI metadata for template {template_key}. Box Request ID: {request_id}")
                logging.error(f"Request payload: {data}")
    
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
        # Normalize the suggestion keys to lowercase without spaces
        normalized_suggestions = {k.strip().lower().replace(' ', ''): v for k, v in suggestions.items()}
        logging.info(f"Normalized suggestions: {normalized_suggestions}")

        # Normalize the schema keys to lowercase without spaces
        normalized_schema = {k.strip().lower().replace(' ', ''): v for k, v in schema.items()}
        logging.info(f"Normalized schema: {normalized_schema}")

        # Extract attributes using normalized keys
        extracted_attributes = {
            normalized_schema["ordernumber"]: normalized_suggestions.get('ordernumber'),
            normalized_schema["invoicenumber"]: normalized_suggestions.get('invoicenumber'),
            normalized_schema["address"]: normalized_suggestions.get('address'),
            normalized_schema["invoicedate"]: normalized_suggestions.get('invoicedate'),
            normalized_schema["total"]: normalized_suggestions.get('total'),
        }
        logging.info(f"Extracted order form AI attributes: {extracted_attributes}")
        return extracted_attributes
    except KeyError as e:
        logging.error(f"KeyError: {e} - Schema: {normalized_schema}")
        return {}

def extract_contract_ai_attributes(suggestions, schema):
    logging.info(f"Extracting contract AI attributes: suggestions={suggestions}, schema={schema}")
    try:
        # Normalize the suggestion keys to lowercase without spaces or hyphens
        normalized_suggestions = {k.strip().replace(' ', '').replace('-', '').lower(): v for k, v in suggestions.items()}
        logging.info(f"Normalized suggestions: {normalized_suggestions}")

        # Normalize the schema keys to lowercase without spaces or hyphens
        normalized_schema = {k.strip().replace(' ', '').replace('-', '').lower(): v for k, v in schema.items()}
        logging.info(f"Normalized schema: {normalized_schema}")

        # Extract attributes using normalized keys and filter out None values
        extracted_attributes = {
            normalized_schema["contracttype"]: normalized_suggestions.get('contracttype'),
            normalized_schema["contracteffectivedate"]: normalized_suggestions.get('contracteffectivedate'),
            normalized_schema["contractmasterserviceagreement"]: normalized_suggestions.get('contractmasterserviceagreement'),
            normalized_schema["client"]: normalized_suggestions.get('client'),
            normalized_schema["projectname"]: normalized_suggestions.get('projectname'),
            normalized_schema["assessmentandplanning"]: normalized_suggestions.get('assessmentandplanning'),
            normalized_schema["configurationandsetup"]: normalized_suggestions.get('configurationandsetup'),
            normalized_schema["deliverables"]: normalized_suggestions.get('deliverables'),
            normalized_schema["clientspecificdependencies"]: normalized_suggestions.get('clientspecificdependencies'),
            normalized_schema["projectpersonnel"]: normalized_suggestions.get('projectpersonnel'),
            normalized_schema["totalestimatedservicefees"]: normalized_suggestions.get('totalestimatedservicefees'),
            normalized_schema["milestoneordeliverables"]: normalized_suggestions.get('milestoneordeliverables')
        }

        # Remove keys with None values
        extracted_attributes = {k: v for k, v in extracted_attributes.items() if v is not None}

        logging.info(f"Extracted contract AI attributes: {extracted_attributes}")
        return extracted_attributes
    except KeyError as e:
        logging.error(f"KeyError: {e} - Schema: {normalized_schema}")
        return {}
def extract_nike_all_sports_agreement_attributes(suggestions, schema):
    logging.info(f"Extracting Nike All Sports Agreement attributes: suggestions={suggestions}, schema={schema}")
    try:
        # Normalize the suggestion keys to lowercase without spaces or hyphens
        normalized_suggestions = {k.strip().replace(' ', '').replace('-', '').lower(): v for k, v in suggestions.items()}
        logging.info(f"Normalized suggestions: {normalized_suggestions}")

        # Normalize the schema keys to lowercase without spaces or hyphens
        normalized_schema = {k.strip().replace(' ', '').replace('-', '').lower(): v for k, v in schema.items()}
        logging.info(f"Normalized schema: {normalized_schema}")

        # Extract attributes using normalized keys and filter out None values
        extracted_attributes = {
            normalized_schema["title"]: normalized_suggestions.get('title'),
            normalized_schema["university"]: normalized_suggestions.get('university'),
            normalized_schema["effectivedate"]: normalized_suggestions.get('effectivedate'),
            normalized_schema["expirationdate"]: normalized_suggestions.get('expirationdate'),
            normalized_schema["renewaldate"]: normalized_suggestions.get('renewaldate'),
            normalized_schema["termlength"]: normalized_suggestions.get('termlength'),
            normalized_schema["terminationclauses"]: normalized_suggestions.get('terminationclauses'),
            normalized_schema["totalcontractvalue"]: normalized_suggestions.get('totalcontractvalue'),
            normalized_schema["paymentterms"]: normalized_suggestions.get('paymentterms'),
            normalized_schema["bonusesincentives"]: normalized_suggestions.get('bonusesincentives'),
            normalized_schema["deliverables"]: normalized_suggestions.get('deliverables'),
            normalized_schema["milestones"]: normalized_suggestions.get('milestones'),
            normalized_schema["responsibilities"]: normalized_suggestions.get('responsibilities'),
            normalized_schema["jurisdiction"]: normalized_suggestions.get('jurisdiction'),
            normalized_schema["signatories"]: normalized_suggestions.get('signatories'),
            normalized_schema["confidentialityclause"]: normalized_suggestions.get('confidentialityclause'),
            normalized_schema["attachmentsandexhibits"]: normalized_suggestions.get('attachmentsandexhibits'),
            normalized_schema["preexistingcontracts"]: normalized_suggestions.get('preexistingcontracts')
        }

        # Remove keys with None values
        extracted_attributes = {k: v for k, v in extracted_attributes.items() if v is not None}

        logging.info(f"Extracted Nike All Sports Agreement attributes: {extracted_attributes}")
        return extracted_attributes
    except KeyError as e:
        logging.error(f"KeyError: {e} - Schema: {normalized_schema}")
        return {}

def extract_uber_ai_attributes(suggestions, schema):
    logging.info(f"Extracting Uber AI attributes: suggestions={suggestions}, schema={schema}")
    try:
        # Normalize the suggestion keys to lowercase without spaces or hyphens
        normalized_suggestions = {k.strip().replace(' ', '').replace('-', '').lower(): v for k, v in suggestions.items()}
        logging.info(f"Normalized suggestions: {normalized_suggestions}")

        # Normalize the schema keys to lowercase without spaces or hyphens
        normalized_schema = {k.strip().replace(' ', '').replace('-', '').lower(): v for k, v in schema.items()}
        logging.info(f"Normalized schema: {normalized_schema}")

        # Extract attributes using normalized keys and filter out None values
        extracted_attributes = {
            normalized_schema["restaurantname"]: normalized_suggestions.get('restaurantname'),
            normalized_schema["commissionfee"]: normalized_suggestions.get('commissionfee'),
            normalized_schema["termandtermination"]: normalized_suggestions.get('termandtermination'),
            normalized_schema["intellectualproperty"]: normalized_suggestions.get('intellectualproperty'),
            normalized_schema["confidentiality"]: normalized_suggestions.get('confidentiality'),
            normalized_schema["indemnification"]: normalized_suggestions.get('indemnification'),
            normalized_schema["governinglaw"]: normalized_suggestions.get('governinglaw'),
            normalized_schema["entireagreement"]: normalized_suggestions.get('entireagreement')
        }

        # Remove keys with None values
        extracted_attributes = {k: v for k, v in extracted_attributes.items() if v is not None}

        logging.info(f"Extracted Uber AI attributes: {extracted_attributes}")
        return extracted_attributes
    except KeyError as e:
        logging.error(f"KeyError: {e} - Schema: {normalized_schema}")
        return {}

# Update the extract_nike_contract_ai_attributes function similarly
def extract_nike_contract_ai_attributes(suggestions, schema):
    logging.info(f"Extracting contract AI attributes: suggestions={suggestions}, schema={schema}")
    try:
        # Normalize the suggestion keys to lowercase without spaces or hyphens
        normalized_suggestions = {k.strip().replace(' ', '').replace('-', '').lower(): v for k, v in suggestions.items()}
        logging.info(f"Normalized suggestions: {normalized_suggestions}")

        # Normalize the schema keys to lowercase without spaces or hyphens
        normalized_schema = {k.strip().replace(' ', '').replace('-', '').lower(): v for k, v in schema.items()}
        logging.info(f"Normalized schema: {normalized_schema}")

        # Extract attributes using normalized keys and filter out None values
        extracted_attributes = {
            normalized_schema["contractdate"]: normalized_suggestions.get('contractdate'),
            normalized_schema["contractrecipiant"]: normalized_suggestions.get('athletename'),
            normalized_schema["agreementterms"]: normalized_suggestions.get('agreementterms'),
            normalized_schema["totalcontractvalue"]: normalized_suggestions.get('compensation'),
            normalized_schema["commissiononplayerssignatureproducts"]: normalized_suggestions.get('commissiononplayerssignatureproducts'),
            normalized_schema["canuseplayersnameandlikeness"]: normalized_suggestions.get('canuseplayersnameandlikeness'),
            normalized_schema["termination"]: normalized_suggestions.get('termination'),
            normalized_schema["paymentterms"]: normalized_suggestions.get('paymentterms'),
            normalized_schema["contractstartdate"]: normalized_suggestions.get('contractstartdate'),
            normalized_schema["contractenddate"]: normalized_suggestions.get('contractenddate'),
        }

        # Remove keys with None values
        extracted_attributes = {k: v for k, v in extracted_attributes.items() if v is not None}

        logging.info(f"Extracted contract AI attributes: {extracted_attributes}")
        return extracted_attributes
    except KeyError as e:
        logging.error(f"KeyError: {e} - Schema: {normalized_schema}")
        return {}


        # Remove keys with None values
        extracted_attributes = {k: v for k, v in extracted_attributes.items() if v is not None}

        logging.info(f"Extracted contract AI attributes: {extracted_attributes}")
        return extracted_attributes
    except KeyError as e:
        logging.error(f"KeyError: {e} - Schema: {normalized_schema}")
        return {}
def auto_policy(suggestions, schema):
    logging.info(f"Extracting Uber AI attributes: suggestions={suggestions}, schema={schema}")
    try:
        # Normalize the suggestion keys to lowercase without spaces or hyphens
        normalized_suggestions = {k.strip().replace(' ', '').replace('-', '').lower(): v for k, v in suggestions.items()}
        logging.info(f"Normalized suggestions: {normalized_suggestions}")

        # Normalize the schema keys to lowercase without spaces or hyphens
        normalized_schema = {k.strip().replace(' ', '').replace('-', '').lower(): v for k, v in schema.items()}
        logging.info(f"Normalized schema: {normalized_schema}")

        # Extract attributes using normalized keys and filter out None values
        extracted_attributes = {
            normalized_schema["policyNumber"]: normalized_suggestions.get('policyNumber'),
            normalized_schema["policyholdername"]: normalized_suggestions.get('policyholdername'),
            normalized_schema["policyeffectivestartdate"]: normalized_suggestions.get('policyeffectivestartdate'),
            normalized_schema["policyeffectiveenddate"]: normalized_suggestions.get('policyeffectiveenddate'),
            normalized_schema["agencyprovidingcoverage"]: normalized_suggestions.get('agencyprovidingcoverage'),
            normalized_schema["policytype"]: normalized_suggestions.get('policytype'),
            normalized_schema["coverageforstatepropertyandcasualtyinsuranceguaranty"]: normalized_suggestions.get('coverageforstatepropertyandcasualtyinsuranceguaranty'),
            normalized_schema["bodilyinjuryliability"]: normalized_suggestions.get('bodilyinjuryliability'),
            normalized_schema["areuninsuredmotoristscovered"]: normalized_suggestions.get('areuninsuredmotoristscovered'),
            normalized_schema["ishaildamagecovered"]: normalized_suggestions.get('ishaildamagecovered'),
            normalized_schema["lossofclothingpayment"]: normalized_suggestions.get('lossofclothingpayment'),
            normalized_schema["righttoappraisal"]: normalized_suggestions.get('righttoappraisal'),
            normalized_schema["whatisthisdocumentabout"]: normalized_suggestions.get('whatisthisdocumentabout'),
        }

        # Remove keys with None values
        extracted_attributes = {k: v for k, v in extracted_attributes.items() if v is not None}

        logging.info(f"Extracted Uber AI attributes: {extracted_attributes}")
        return extracted_attributes
    except KeyError as e:
        logging.error(f"KeyError: {e} - Schema: {normalized_schema}")
        return {}
# Mapping of template keys to extraction functions
template_extractors = {
    # Add more mappings for other templates
    # "contractAi": extract_contract_ai_attributes,
    # "aitest": extract_order_form_ai_attributes,
    # "uberaiextract": extract_uber_ai_attributes,
    #"nikeplayercontrat": extract_nike_contract_ai_attributes,
    # "nikeallsportsagreement": extract_nike_all_sports_agreement_attributes,
    "autoPolicy": auto_policy
    
}

