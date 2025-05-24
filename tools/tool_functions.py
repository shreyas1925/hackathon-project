import json
import requests
from utils.mongo_loader import connect_mongo
from utils.helpers import list_bams, list_endpoints, summarize_projection, getAgentIdFromAgentName
from utils.monitoring_payload_utils import format_monitoring_payload
from dotenv import load_dotenv
import os
from copy import deepcopy

load_dotenv()
more_api_key = os.getenv("MORE_API_KEY")

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

def fetch_ba_level_information(baName: str, user_input: str, openai_client, app_key):
    db = connect_mongo()
    collection = db["brownfield-ba-data"]
    ba_data = collection.find_one({"baName": baName})
    
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

def compare_endpoint_charges(endpoint_sysId1: str, endpoint_sysId2: str, openai_client, app_key):
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
    
def fetch_agent_information(agentName: str, openai_client, app_key):

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
    print(agentId)
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

def fetch_request_status(requestId: str, openai_client, app_key):
    print(requestId)
    print("Fetching request status...")
    response = requests.get(f"https://more-api-dev.cisco.com/api/v1/monitoringRequests/{requestId}/status", headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + more_api_key,
    })
    print(response)
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