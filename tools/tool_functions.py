import json
import requests
from utils.mongo_loader import connect_mongo
from utils.helpers import list_bams, list_endpoints, summarize_projection, extract_null_monitoring_endpoints
from utils.monitoring_payload_utils import format_monitoring_payload, format_get_assets_payload
from dotenv import load_dotenv
import os
from copy import deepcopy
from langsmith import traceable


load_dotenv()
more_api_key = os.getenv("MORE_API_KEY")

@traceable(name="Create Monitor")
def create_monitor(endpoint_sysId, testType, configurations, monitoringCriticality):
    payload = format_monitoring_payload(
        endpoint_sysId=endpoint_sysId,
        monitoringCriticality=monitoringCriticality,
        configurations=configurations,
        testType=testType
    )
    response = requests.post("https://more-api-dev.cisco.com/api/v1/monitoringRequest", headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + more_api_key,
    }, json=payload)

    requestId = response.json().get("requestId")
    if response.status_code == 201:
        return f"Monitoring created for `{endpoint_sysId}` with test type `{testType}. Please track you application status using tracking Id : {requestId}`. Please check after some time to see the status of your request"
    else:
        error_description = response.json().get("errorDescription", [])
        if isinstance(error_description, list) and error_description:
            error_message = error_description[0]
        else:
            error_message = str(error_description)

        return f"Failed to create {testType} test to monitor {endpoint_sysId}. Error: {error_message}"

@traceable(name="Update Monitor")   
def update_monitor(endpoint_sysId, testType, configurations, openai_client, app_key, user_input):
    db = connect_mongo()
    collection = db["assetsMonitoringConfiguration"]
    existingEndpointData = collection.find_one({"data.cmdbId": endpoint_sysId})

    if not existingEndpointData:
        return f"❌ No existing monitoring configuration found for endpoint `{endpoint_sysId}`. Please create a new monitor instead."

    monitoringCriticality = existingEndpointData.get("data", {}).get("monitoringCriticality", "5")
    existingEndpointConfiguration = existingEndpointData.get("data", {}).get("thousandEyesConfiguration", {})
 
    if not existingEndpointConfiguration:
        return f"❌ No existing monitoring configuration found for endpoint `{endpoint_sysId}`. Please create a new monitor instead."
    
    # update the configurations with existing ones
    configurations = {**existingEndpointConfiguration, **configurations}
    payload = {
        "assets": [
            {
                "sysIds": [endpoint_sysId],
                "monitoringCriticality": monitoringCriticality,
                "monitoringPlatform": "ThousandEyes",
                "monitoringConfiguration": [configurations]
            }
        ]
    }

    response = requests.put("https://more-api-dev.cisco.com/api/v1/monitoringRequest/updateMonitoring", headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + more_api_key,
    }, json=payload)

    requestId = response.json().get("requestId")
    if response.status_code == 201:
        return f"Monitoring updated for `{endpoint_sysId}` with test type `{testType}. Please track you application status using tracking Id : {requestId}`. Please check after some time to see the status of your request"
    else:
        error_description = response.json().get("errorDescription", [])
        if isinstance(error_description, list) and error_description:
            error_message = error_description[0]
        else:
            error_message = str(error_description)

        return f"Failed to update {testType} test to monitor {endpoint_sysId}. Error: {error_message}"

@traceable(name="Delete Monitor")
def delete_monitor(endpoint_sysId, openai_client, app_key, user_input):
    response = requests.delete(f"https://more-api-dev.cisco.com/api/v1/monitoringRequest/ci/{endpoint_sysId}?monitoringPlatform=ThousandEyes", headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + more_api_key,
    })

    if response.status_code == 202 or response.status_code == 204:
        return f"Monitoring deleted for {endpoint_sysId}"
    else:
        error_description = response.json().get("errorDescription", [])
        if isinstance(error_description, list) and error_description:
            error_message = error_description[0]
        else:
            error_message = str(error_description)

        return f"Failed to delete test which was monitoring {endpoint_sysId}. Error: {error_message}"

@traceable(name="Fetch BA Level Information")
def fetch_ba_level_information(baName: str, user_input: str, openai_client, app_key):
    db = connect_mongo()
    collection = db["brownfield-ba-data"]
    ba_data = collection.find_one({"baName": baName})

    if not ba_data:
        return f"❌ No data found for Business Application `{baName}`."
    
    # Let LLM decide the intent and target
    intent_response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", 
             "content": 
                """You are a tool router for a monitoring assistant. The user will ask questions about business applications (BAs), business application modules (BAMs), and endpoints (systems monitored in ThousandEyes). 
                - If the user asks for a list of modules, return {"tool": "list_bams"}.
                - If the user asks for a list of endpoints or monitored systems, return {"tool": "list_endpoints"}.
                - If the user asks for a summary or count of endpoints, return {"tool": "summarize"}.
                - If the intent is unclear or unsupported, return {"tool": "unknown"}.

                BAs are business applications, BAMs are modules within a BA, and endpoints are systems where monitoring is set up in ThousandEyes.

                Always return a JSON object with the key "tool"."""
            },
            {"role": "user", "content": user_input}
        ],
        user=json.dumps({"appkey": app_key})
    )
    tool = json.loads(intent_response.choices[0].message.content).get("tool")
    
    if tool == "list_bams":
        return "\n".join(list_bams(ba_data))
    elif tool == "list_endpoints":
        return list_endpoints(ba_data)
    elif tool == "summarize":
        return summarize_projection(ba_data)
    else:
        return "Sorry, at this point of time I do not support this request"

@traceable(name="Get Matched Endpoint")
def get_matched_endpoint(db, endpoint_sysId):
    collection = db["brownfield-ba-data"]

    doc = collection.find_one({
        "$or": [
            {"endpoints.endpointSysId": endpoint_sysId},
            {"bams.endpoints.endpointSysId": endpoint_sysId}
        ]
    })

    if not doc:
        return f"❌ No data found for endpoint in MoRE `{endpoint_sysId}`."
    # Extract the matching endpoint
    matched_endpoint = None
    source = ""

    # Check top-level endpoints
    for ep in doc.get("endpoints", []):
        if ep.get("endpointSysId") == endpoint_sysId:
            matched_endpoint = deepcopy(ep)
            source = "BA"
            break

    # Check inside BAMS if not found
    if not matched_endpoint:
        for bam in doc.get("bams", []):
            for ep in bam.get("endpoints", []):
                if ep.get("endpointSysId") == endpoint_sysId:
                    matched_endpoint = deepcopy(ep)
                    matched_endpoint["bamName"] = bam.get("bamName")
                    matched_endpoint["bamSysId"] = bam.get("bamSysId")
                    source = "BAM"
                    break
            if matched_endpoint:
                break

    if not matched_endpoint:
        return f"❌ Endpoint `{endpoint_sysId}` not found in any known BA/BAM structure."

    #add context metadata from the parent document
    matched_endpoint["baName"] = doc.get("baName")
    matched_endpoint["baSysId"] = doc.get("baSysId")
    matched_endpoint["source"] = source 
    return matched_endpoint

@traceable(name="Fetch Endpoint Information")
def fetch_endpoint_information(endpoint_sysId: str, user_input: str, openai_client, app_key):
    db = connect_mongo()
    matched_endpoint = get_matched_endpoint(db, endpoint_sysId)

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system",
                "content": (
                    "You are a helpful assistant. "
                    "You will be given endpoint data in JSON format and a user question. "
                    "Answer the user's question using only the provided data. "
                    "If the answer is not present, say you don't have enough information."
                )
            },
            {"role": "user", "content": f"Endpoint data: {json.dumps(matched_endpoint)}\n\nQuestion: {user_input}"}
        ],
        user=json.dumps({"appkey": app_key})
    )
    return response.choices[0].message.content

@traceable(name="Compare Endpoint Charges")
def compare_endpoint_charges(endpoint_sysId1: str, endpoint_sysId2: str, openai_client, app_key, user_input):
    db = connect_mongo()
    matched_endpoint1 = get_matched_endpoint(db, endpoint_sysId1)
    matched_endpoint2 = get_matched_endpoint(db, endpoint_sysId2)

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system",
                "content": (
                    "You are a helpful assistant who will compare config of 2 test and explain why there is charge difference. "
                    "You will be given endpoints data where it will have test information of both endpoints in JSON format"
                    "Configuration strictly responsible for consumption or charges are interval, timeLimit and number of agents assigned to the endpoint"
                    "Do not consider any other configuration for charge comparison"
                    "So you have to answer back user in natural language why their one test is consuming more than the other"
                    "If you don't have answer, say you don't have enough information."
                )
            },
            {"role": "user", "content": f"Endpoint data1: {json.dumps(matched_endpoint1)}\nEndpoint data2: {json.dumps(matched_endpoint2)}"}],
        user=json.dumps({"appkey": app_key})
    )
    return response.choices[0].message.content

@traceable(name="Fetch Agent Information")
def fetch_agent_information(agentName: str, openai_client, app_key, user_input):

    agentMapping = {
        "Cisco: San Jose, CA" :  251041,
        "Cisco: Allen/Richardson, TX" : 251146,
        "Cisco: Raleigh, NC" : 251226,
        "Cisco: Almere, Netherlands" : 251306,
        "Cisco: Bangalore, India" : 251386,
        "Cisco: Tokyo, Japan" : 251471,
        "Cisco: St. Leonards, Australia" : 251556
    }

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system",
                "content": (
                    "You are a assistant who is expert in analyzing mapping data and user input to return correct data."
                    "You will get an agentMapping and also an user input which will have user input"
                    "You have to only return the agentId based on the user input which maps to the correct agentName present in agentmapping"
                    "If you don't have answer, say you don't have enough information."
                )
            },
            {"role": "user", "content": f"Endpoint data1: {json.dumps(agentMapping)}\nUser input: {agentName}"}],
        user=json.dumps({"appkey": app_key})
    )
    agentId = response.choices[0].message.content
    db = connect_mongo()
    collection = db["brownfield-ba-data"]

    pipeline = [
        { "$unwind": "$endpoints" },
        { "$match": { "endpoints.testConfiguration.agents": agentId } },
        { 
            "$project": { 
                "_id": 0, 
                "testName": "$endpoints.testName",
                "endpointSysId": "$endpoints.endpointSysId"
            } 
        }
    ]   

    results = list(collection.aggregate(pipeline))
    # return results
    formatted_results = [
        f'testName: "{result["testName"]}", endpointSysId: "{result["endpointSysId"]}"\n'
        for result in results
    ]

    return "\n".join(formatted_results)

@traceable(name="Fetch Request Status")
def fetch_request_status(requestId: str, openai_client, app_key, user_input):
    print(requestId)
    print("Fetching request status...")
    response = requests.get(f"https://more-api-dev.cisco.com/api/v1/monitoringRequests/{requestId}/status", headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + more_api_key,
    })
    testInformation = response.json()
    print(testInformation)
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system",
                "content": (
                    "You are an assistant who analyzes JSON data to answer user questions based only on the fields in the input JSON called 'testInformation'.\n"
                    "You must not output the entire JSON or mention 'testInformation' explicitly in your answers.\n"
                    "Answer only what is asked, based on relevant fields in the input.\n"
                    "For example:\n"
                    "- If user asks 'What is the request status f363f15a...', find the 'status' field.\n"
                    "- If user asks about the URL, find it under assets -> monitoringConfiguration -> url.\n"
                    "- If asks about errors, find it under assetsStatusInThousandEyes -> errors.\n. If no errors then say 'No errors found in your request'\n"
                    "If the question cannot be answered with available fields, say 'I don't have enough information to answer that.'"
                )
            },
            {"role": "user", "content": f"Required information : {json.dumps(testInformation)}\n"}],
        user=json.dumps({"appkey": app_key})
    )
    return response.choices[0].message.content

@traceable(name="Fetch Unmonitored Endpoints")
def fetch_unmonitored_endpoints(baSysId, openai_client, app_key, user_input):
    print(f"Fetching unmonitored endpoints for BA SysId: {baSysId}")
    response = requests.post(f"https://more-api-dev.cisco.com/api/v1/onboarding/assetsDetails/{baSysId}", headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + more_api_key,
    })
    endpoints = extract_null_monitoring_endpoints(response.json())
    formatted_results = [
        f'endpointName: "{result["endpointName"]}", endpointSysId: "{result["endpointSysId"]}"\n'
            for result in endpoints
    ]

    output = "\n".join(formatted_results) 
    return output
    
 # Update or insert the userID in the MongoDB collection 'clientIdToUserMapping' for the record with clientId="monoh-dev-integration".

@traceable(name="Set User ID in MongoDB")
def set_user_id_in_mongo(userId):
    try:
        db = connect_mongo()
        collection = db["clientIdToUserMapping"]
        result = collection.update_one(
            {"clientId": "monoh-dev-integration"},
            {"$set": {"userId": userId}},
            upsert=True
        )
        
        if result.matched_count > 0:
            return {"status": "success", "message": "User ID updated successfully in MongoDB."}
        elif result.upserted_id:
            return {"status": "success", "message": "User ID inserted successfully in MongoDB."}
        else:
            return {"status": "warning", "message": "No changes made to MongoDB."}
    except Exception as e:
        return {"status": "error", "message": f"An error occurred: {str(e)}"}

# create a new tool to get the user assets list by calling the more api
@traceable(name="Fetch User Assets")
def fetch_user_assets(userId: str, openai_client, app_key, user_input: str):
    print("Fetching user assets...")
    print(f"User ID: {userId}")
    if not userId:
        return "❌ User CEC ID is required to fetch assets."

    set_user_id_response = set_user_id_in_mongo(userId)
    if set_user_id_response["status"] != "success":
        return f"❌ Failed to set user ID in MongoDB: {set_user_id_response['message']}"
    print(f"User ID set in MongoDB: {set_user_id_response['message']}")

    # Prepare the payload for the more API
    payload = format_get_assets_payload(
        monitoring_goal_ids=["MonOH_AA", "MonOH_AN"],
        enabled=True
    )
    print(f"Payload: {json.dumps(payload, indent=2)}")
    # Set the user in the headers as auth-user
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + more_api_key,
        "auth-user": userId
    }
    # Make a post request to the more API
    response = requests.post("https://more-api-dev.cisco.com/api/v1/onboarding/assetsList/thousandEyes", headers=headers, json=payload)

    # Handle response
    if response.status_code == 200:
        assets = response.json().get("data", [])
        if not assets:
            return f"ℹ️ No assets found for the user ID `{userId}`."

        # Format asset data as a list of strings
        asset_list = "\n".join(
            [f"- BA Name: {asset.get('ciName', 'N/A')}, SysId: {asset.get('sysId', 'N/A')}" for asset in assets]
        )

        return f"✅ Assets associated with user `{userId}`:\n\n{asset_list}"

    else:
        error_description = response.json().get("errorDescription", [])
        if isinstance(error_description, list) and error_description:
            error_message = error_description[0]
        else:
            error_message = str(error_description)

        return f"❌ Failed to fetch assets for user `{userId}`. Error: {error_message}"