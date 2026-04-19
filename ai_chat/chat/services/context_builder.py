from chat.connectors.manager import ConnectorManager


def build_cloud_context(user, prompt: str):
    manager = ConnectorManager(user)
    lowered = prompt.lower()

    context_parts = []

    # AWS
    if "aws" in lowered:
        connector = manager.get_connector("aws")
        if connector:
            try:
                instances = connector.list_instances()
                context_parts.append(f"AWS instances: {instances}")
            except Exception as e:
                context_parts.append(f"AWS error: {str(e)}")

    # Azure
    if "azure" in lowered:
        connector = manager.get_connector("azure")
        if connector:
            try:
                vms = connector.list_vms()
                context_parts.append(f"Azure VMs: {vms}")
            except Exception as e:
                context_parts.append(f"Azure error: {str(e)}")

    # GCP
    if "gcp" in lowered:
        connector = manager.get_connector("gcp")
        if connector:
            try:
                instances = connector.list_instances()
                context_parts.append(f"GCP instances: {instances}")
            except Exception as e:
                context_parts.append(f"GCP error: {str(e)}")

    return "\n".join(context_parts)