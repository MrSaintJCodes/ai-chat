from chat.models import CloudProviderSetting
from chat.utils.crypto import decrypt_value
from .aws import AWSConnector
from .azure import AzureConnector
from .gcp import GCPConnector


class ConnectorManager:
    def __init__(self, user):
        self.user = user

    def get_enabled_settings(self):
        return CloudProviderSetting.objects.filter(user=self.user, enabled=True)

    def get_connector(self, provider: str):
        setting = CloudProviderSetting.objects.filter(
            user=self.user,
            provider=provider,
            enabled=True
        ).first()

        if not setting:
            return None

        if provider == "aws":
            return AWSConnector(
                access_key_id=decrypt_value(setting.aws_access_key_id),
                secret_access_key=decrypt_value(setting.aws_secret_access_key),
                region=setting.aws_region,
            )

        if provider == "azure":
            return AzureConnector(
                tenant_id=setting.azure_tenant_id,
                client_id=setting.azure_client_id,
                client_secret=decrypt_value(setting.azure_client_secret),
                subscription_id=setting.azure_subscription_id,
            )

        if provider == "gcp":
            return GCPConnector(
                service_account_json=decrypt_value(setting.gcp_service_account_json),
                project_id=setting.gcp_project_id,
            )

        return None