def list_bams(ba_data):
    return [bam['bamName'] for bam in ba_data.get("bams", [])]

def list_endpoints(ba_data):
    eps = ba_data.get("endpoints", []) + [
        ep for bam in ba_data.get("bams", []) for ep in bam.get("endpoints", [])
    ]
    endpoint_list = [
        f'endpointName: "{ep.get("endpointName", "")}", endpointSysId: "{ep.get("endpointSysId", "")}"'
        for ep in eps
    ]
   
    content = "\n\n".join(endpoint_list)
    
    return f"""Here are the list of monitored endpoints:\n\n{content}"""

def summarize_projection(ba_data):
    total_eps = len(list_endpoints(ba_data))
    return f"Total monitored endpoints under BA '{ba_data['baName']}': {total_eps}"

def getAgentIdFromAgentName(agentName):
    agentMapping = {
        "Cisco: San Jose, CA" :  251041,
        "Cisco: Allen/Richardson, TX" : 251146,
        "Cisco: Raleigh, NC" : 251226,
        "Cisco: Almere, Netherlands" : 251306,
        "Cisco: Bangalore, India" : 251386,
        "Cisco: Tokyo, Japan" : 251471,
        "Cisco: St. Leonards, Australia" : 251556
    }
    return agentMapping.get(agentName, None)

def extract_null_monitoring_endpoints(api_response):
    """
    Extracts endpoints with monitoringConfigurationType: null from API response
    
    Args:
        api_response (dict): The API response object containing assetDetails
        
    Returns:
        list: List of endpoints with format [{"endpointName": "", "endpointSysId": ""}]
    """
    endpoints = []
    
    if not api_response or 'assetDetails' not in api_response:
        return endpoints
    
    asset_details = api_response['assetDetails']
    
    # Extract endpoints from BAM -> App Instances -> Endpoints
    if 'bam' in asset_details and isinstance(asset_details['bam'], list):
        for bam in asset_details['bam']:
            if 'appInstances' in bam and isinstance(bam['appInstances'], list):
                for app_instance in bam['appInstances']:
                    if 'appEndpoints' in app_instance and isinstance(app_instance['appEndpoints'], list):
                        for endpoint in app_instance['appEndpoints']:
                            if endpoint.get('monitoringConfigurationType') is None:
                                endpoints.append({
                                    'endpointName': endpoint.get('ciName', ''),
                                    'endpointSysId': endpoint.get('sysId', '')
                                })
    
    # Extract endpoints from direct App Instances under BA
    if 'appInstances' in asset_details and isinstance(asset_details['appInstances'], list):
        for app_instance in asset_details['appInstances']:
            if 'appEndpoints' in app_instance and isinstance(app_instance['appEndpoints'], list):
                for endpoint in app_instance['appEndpoints']:
                    if endpoint.get('monitoringConfigurationType') is None:
                        endpoints.append({
                            'endpointName': endpoint.get('ciName', ''),
                            'endpointSysId': endpoint.get('sysId', '')
                        })
    
    return endpoints