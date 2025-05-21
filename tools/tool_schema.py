functions = [
    {
        "name": "create_monitor",
        "description": "Creates a thousandeyes test for my application, ask for all the parameters before creating a test",
        "parameters": {
            "type": "object",
            "properties": {
                "endpoint_sysId": {
                    "type": "string",
                    "description": "ID of a application in which is to be monitored"
                },
                "testType": {
                    "type": "string",
                    "description": "Type of test to create. Must be one of: HTTP, WebTransaction, Network, DNS, FTTP."
                },
                "monitoringCriticality":{
                    "type": "string",
                    "description": "Criticality from 1 (low) to 5 (high)"
                },
                "configurations": {
                  "type": "object",
                  "description": "Ask for the configurations before creating a test to monitor the application",
                  "properties": {
                    "interval": { "type": "integer", "description": "Polling interval in seconds" },
                    "httpTimeLimit": { "type": "integer", "description": "Time limit for HTTP" },
                    "timeLimit": { "type": "integer", "description": "Time limit for WebTransaction" },
                    "fttpTimeLimit": { "type": "integer", "description": "Time limit for FTTP" },
                    "url": { "type": "string", "description": "URL to monitor, do not ask while creating DNS Test but always ask for other tests" },
                    "dnsServers": {
                        "type": "array",
                        "items": { "type": "string", "format": "ipv4" },
                        "description": "DNS servers to use (only for DNS tests).Always considers each one as a array of strings separated by commas"
                    },
                    "domain": { "type": "string", "description": "Domain to monitor (only for DNS tests)" }
                  },
                  "required": ["interval"]
                }
            },
            "required": ["endpoint_sysId", "testType", "monitoringCriticality", "configurations"]
        }
    },
    {
        "name": "fetch_ba_level_information",
        "description": "You should return configurations or information when asked by user regarding tests, endpoints, bams, consumptions",
        "parameters": {
            "type": "object",
            "properties": {
                "baName": {
                    "type": "string",
                    "description": "Name of the business application which you want to view"
                }
            },
            "required": ["baName"]
        }
    },
    {
        "name": "fetch_endpoint_information",
        "description": "You should return endpoint related configurations or other information when asked by user (e.g., endpoint name, test Name, testConfiguration, consumption)",
        "parameters": {
            "type": "object",
            "properties": {
                "endpoint_sysId": {
                    "type": "string",
                    "description": "Application Id of the monitored application"
                }
            },
            "required": ["endpoint_sysId"]
        }
    },
    {
        "name": "compare_endpoint_charges",
        "description": "When user asks regarding charges or wants to know why one of my test is charged more than other test",
        "parameters": {
            "type": "object",
            "properties": {
                "endpoint_sysId1": {
                    "type": "string",
                    "description": "Application Id of the first monitored application"
                },
                "endpoint_sysId2": {
                    "type": "string",
                    "description": "Application Id of the second monitored application to compare"
                }
            },
            "required": ["endpoint_sysId1","endpoint_sysId2"]
        }
    },
    {
        "name": "fetch_agent_information",
        "description": "When user asks queries based on agent name or agent id to know the endpoints/tests associated with the specific agent",
        "parameters": {
            "type": "object",
            "properties": {
                "agentName": {
                    "type": "string",
                    "description": "Agent Name of the agent in which application is monitored"
                }
            },
            "required": ["agentName"]
        }
    }
]
