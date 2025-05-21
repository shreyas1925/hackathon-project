def get_default_config(test_type):
    defaults = {
        "HTTP": {
            "type": "ThousandEyesHTTPConfiguration",
            "alertRules": [
                "HTTP Server Availability 0%",
                "HTTP Server Availability Below 50%",
                "HTTP Server Availability Below 75%",
                "HTTP Server Availability Below 99%",
                "Latency above 2x stddev",
                "Latency above 450ms",
                "Packet Loss: >= 25%",
                "SSL Certificate Expiry: 1 day",
                "SSL Certificate Expiry: 30 days",
                "SSL Certificate Expiry: 7 days",
                "Transport Layer Availability 0%",
                "Transport Layer Availability Below 50%",
                "Transport Layer Availability Below 75%",
                "Transport Layer Availability Below 99%"
            ],
            "agents": ["251041"],
            "agentSelect": "Static",
            "alertsEnabled": True,
            "enabled": True,
            "bandwidthMeasurements": False,
            "contentRegex": "SUCCESS",
            "followRedirects": True
        },
        "WebTransaction": {
            "type": "ThousandEyesWebTransactionConfiguration",
            "alertRules": [
                "HTTP Server Availability 0%",
                "HTTP Server Availability Below 50%",
                "HTTP Server Availability Below 75%",
                "HTTP Server Availability Below 99%",
                "Latency above 2x stddev",
                "Latency above 450ms",
                "Packet Loss: >= 25%",
                "SSL Certificate Expiry: 1 day",
                "SSL Certificate Expiry: 30 days",
                "SSL Certificate Expiry: 7 days",
                "Transport Layer Availability 0%",
                "Transport Layer Availability Below 50%",
                "Transport Layer Availability Below 75%",
                "Transport Layer Availability Below 99%"
            ],
            "agents": ["251041"],
            "agentSelect": "Static",
            "alertsEnabled": True,
            "enabled": True
        },
        "Network": {
            "type": "ThousandEyesNetworkConfiguration",
            "alertRules": [
                "HTTP Server Availability 0%",
                "HTTP Server Availability Below 50%",
                "HTTP Server Availability Below 75%",
                "HTTP Server Availability Below 99%",
                "Latency above 2x stddev",
                "Latency above 450ms",
                "Packet Loss: >= 25%",
                "SSL Certificate Expiry: 1 day",
                "SSL Certificate Expiry: 30 days",
                "SSL Certificate Expiry: 7 days",
                "Transport Layer Availability 0%",
                "Transport Layer Availability Below 50%",
                "Transport Layer Availability Below 75%",
                "Transport Layer Availability Below 99%"
            ],
            "agents": ["251041"],
            "agentSelect": "Static",
            "alertsEnabled": True,
            "enabled": True
        },
        "DNS": {
            "type": "ThousandEyesDNSConfiguration",
            "alertRules": [
                "HTTP Server Availability 0%",
                "HTTP Server Availability Below 50%",
                "HTTP Server Availability Below 75%",
                "HTTP Server Availability Below 99%",
                "Latency above 2x stddev",
                "Latency above 450ms",
                "Packet Loss: >= 25%",
                "SSL Certificate Expiry: 1 day",
                "SSL Certificate Expiry: 30 days",
                "SSL Certificate Expiry: 7 days",
                "Transport Layer Availability 0%",
                "Transport Layer Availability Below 50%",
                "Transport Layer Availability Below 75%",
                "Transport Layer Availability Below 99%"
            ],
            "agents": ["251041"],
            "agentSelect": "Static",
            "alertsEnabled": True,
            "enabled": True
        },
        "FTTP": {
            "type": "ThousandEyesFTTPConfiguration",
            "alertRules": [
                "HTTP Server Availability 0%",
                "HTTP Server Availability Below 50%",
                "HTTP Server Availability Below 75%",
                "HTTP Server Availability Below 99%",
                "Latency above 2x stddev",
                "Latency above 450ms",
                "Packet Loss: >= 25%",
                "SSL Certificate Expiry: 1 day",
                "SSL Certificate Expiry: 30 days",
                "SSL Certificate Expiry: 7 days",
                "Transport Layer Availability 0%",
                "Transport Layer Availability Below 50%",
                "Transport Layer Availability Below 75%",
                "Transport Layer Availability Below 99%"
            ],
            "agents": ["251041"],
            "agentSelect": "Static",
            "alertsEnabled": True,
            "enabled": True
        }
    }
    return defaults.get(test_type, {})

REQUIRED_CONFIG_FIELDS = {
    "HTTP": ["url", "interval", "httpTimeLimit"],
    "WebTransaction": ["url", "interval", "timeLimit"],
    "FTTP": ["url", "interval", "fttpTimeLimit"],
    "DNS": ["interval", "dnsServers", "domain"],
    "Network": ["url", "interval"]
}

def validate_configuration(config, testType):
    required_keys = REQUIRED_CONFIG_FIELDS.get(testType, [])
    missing_keys = [key for key in required_keys if key not in config]

    if missing_keys:
        # Build a helpful message
        examples = {
            "httpTimeLimit": "`httpTimeLimit`: 10",
            "timeLimit": "`timeLimit`: 10",
            "fttpTimeLimit": "`fttpTimeLimit`: 10",
            "dnsServers": "`dnsServers`: ['8.8.8.8']",
            "interval": "`interval`: 60",
            "url": "`url`: 'https://example.com'",
            "domain": "`domain`: 'example.com'"
        }

        example_lines = [f"- {examples[key]}" for key in missing_keys if key in examples]
        example_text = "\n".join(example_lines)

        raise ValueError(
            f"To create a `{testType}` test, please provide the following missing field(s): "
            f"{', '.join(missing_keys)}.\nExample:\n{example_text}"
        )

def format_monitoring_payload(endpoint_sysId, monitoringCriticality, configurations, testType):
    validate_configuration(configurations, testType)
    default_config = get_default_config(testType)
    filtered_config = configurations.copy()

    # Only keep the correct time limit field
    if testType == "HTTP":
        filtered_config = {
            k: v for k, v in configurations.items() if k in ["interval", "url", "httpTimeLimit"]
        }
    elif testType == "WebTransaction":
        filtered_config = {
            k: v for k, v in configurations.items() if k in ["interval", "url", "timeLimit"]
        }
    elif testType == "FTTP":
        filtered_config = {
            k: v for k, v in configurations.items() if k in ["interval", "url", "fttpTimeLimit"]
        }
    elif testType == "DNS":
        filtered_config = {
            k: v for k, v in configurations.items() if k in ["interval", "dnsServers", "domain"]
        }
    elif testType == "Network":
        filtered_config = {
            k: v for k, v in configurations.items() if k in ["interval", "url"]
        }

    merged_config = {**default_config, **filtered_config}

    return {
        "assets": [
            {
                "sysIds": [endpoint_sysId],
                "monitoringCriticality": monitoringCriticality,
                "monitoringPlatform": "ThousandEyes",
                "monitoringConfiguration": [merged_config]
            }
        ]
    }
