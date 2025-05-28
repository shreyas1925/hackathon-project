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
        "name": "update_monitor",
        "description": "Updates a thousandeyes test configuration for application/update monitored endpoint's configurations. Requires endpoint_sysId and testType, and optionally allows updating configurations. You should ask user what configuration you wants to update and then proceed",
        "parameters": {
            "type": "object",
            "properties": {
                "endpoint_sysId": {
                    "type": "string",
                    "description": "ID of the application to be monitored"
                },
                "testType": {
                    "type": "string",
                    "description": "Type of test to update. Must be one of: HTTP, WebTransaction, Network, DNS, FTTP."
                },
                "configurations": {
                    "type": "object",
                    "description": "Optional configurations to update for the test",
                    "properties": {
                        "interval": { "type": "integer", "description": "Polling interval in seconds" },
                        "httpTimeLimit": { "type": "integer", "description": "Time limit for HTTP" },
                        "timeLimit": { "type": "integer", "description": "Time limit for WebTransaction" },
                        "fttpTimeLimit": { "type": "integer", "description": "Time limit for FTTP" },
                        "url": { "type": "string", "description": "URL to monitor, do not ask while updating DNS Test but always ask for other tests" },
                        "dnsServers": {
                            "type": "array",
                            "items": { "type": "string", "format": "ipv4" },
                            "description": "DNS servers to use (only for DNS tests). Always considers each one as an array of strings separated by commas"
                        },
                        "domain": { "type": "string", "description": "Domain to monitor (only for DNS tests)" }
                    }
                }
            },
            "required": ["endpoint_sysId", "testType"]
        }
    },
    {
        "name": "delete_monitor",
        "description": "Deletes a thousandeyes test configuration for the specified application. Requires endpoint_sysId to identify the test to delete.",
        "parameters": {
            "type": "object",
            "properties": {
                "endpoint_sysId": {
                    "type": "string",
                    "description": "ID of the application whose test configuration is to be deleted"
                }
            },
            "required": ["endpoint_sysId"]
        }
    },
    {
        "name": "fetch_ba_level_information",
        "description": "You should return configurations or information when asked by user regarding tests, endpoints, bams, consumptions. You should always be get called when users asks for monitored endpoints under BA/Business Application",
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
        "description": "When user asks regarding charges or wants to know why one of my test is charged more than other test. Always ask user to provide two endpoint sysId do not consider anything which you know",
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
    },
    {
        "name": "fetch_request_status",
        "description": "When user asks for the information regarding test status or test information which he has onboarded to monitor the application, you should return the only the information what user has asked based on the provided requestId or trackingId",
        "parameters": {
            "type": "object",
            "properties": {
                "requestId": {
                    "type": "string",
                    "description": "Tracking Id of the request which you want to get the information"
                }
            },
            "required": ["requestId"]
        }
    },
    {
        "name": "fetch_unmonitored_endpoints",
        "description": "When user asks for the unmonitored endpoints for on BA, you should return the unmonitored endpoints.Stritctly this function should be called only when user asks for unmonitored endpoints",
        "parameters": {
            "type": "object",
            "properties": {
                "baSysId": {
                    "type": "string",
                    "description": "SysId of the business application to fetch unmonitored endpoints"
                }
            },
            "required": ["baSysId"]
        }
    },
    {
        "name": "fetch_user_assets",
        "description": "Fetches all the assets of the user which includes business applications",
        "parameters": {
            "type": "object",
            "properties": {
                "userId": {
                    "type": "string",
                    "description": "User CEC ID of the user whose assets are to be fetched"
                }
            },
            "required": ["userId"]
        }
    },
]
