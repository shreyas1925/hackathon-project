from utils.mongo_loader import connect_mongo

REQUIRED_CONFIG_FIELDS = {
    "HTTP": ["url", "interval", "httpTimeLimit"],
    "WebTransaction": ["url", "interval", "timeLimit"],
    "FTTP": ["url", "interval", "fttpTimeLimit"],
    "DNS": ["interval", "dnsServers", "domain"],
    "Network": ["url", "interval"]
}

def review_monitor_arguments(state):
    args = state.get("monitor_args", {})
    test_type = args.get("testType")
    config = args.get("configurations", {}) or {}
    endpoint_sysId = args.get("endpoint_sysId")
    operation_type = state.get("operation_type")
    print(operation_type)
    if not test_type:
        return {"result": "❌ `testType` is required to review monitor arguments."}

    required_fields = REQUIRED_CONFIG_FIELDS.get(test_type, [])
    merged_config = config

    # For update, fetch existing config and merge
    if operation_type == "update_monitor" and endpoint_sysId:
        print("Fetching existing configuration for update operation...")
        db = connect_mongo()
        collection = db["assetsMonitoringConfiguration"]
        existing = collection.find_one({"data.cmdbId": endpoint_sysId})
        if not existing:
            return {
                "result": f"❌ No existing monitoring configuration found for endpoint `{endpoint_sysId}`. Please create a new monitor instead."
            }

        existing_config = existing.get("data", {}).get("thousandEyesConfiguration", {})
        merged_config = {**existing_config, **config}

    # Check for missing required fields
    missing = [field for field in required_fields if field not in merged_config]

    if missing:
        return {
            "result": (
                f"❌ Missing required fields for `{test_type}` test: {', '.join(missing)}.\n"
                f"Please provide them before proceeding."
            )
        }

    return {
        "result": f"✅ Monitoring request is end-to-end validated and all required fields for `{test_type}` test are present."
    }
