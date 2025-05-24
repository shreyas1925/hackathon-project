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