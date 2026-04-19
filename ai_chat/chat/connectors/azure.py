from azure.identity import ClientSecretCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
from .base import BaseConnector


class AzureConnector(BaseConnector):
    provider = "azure"

    def __init__(self, tenant_id: str, client_id: str, client_secret: str, subscription_id: str):
        self.credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )
        self.subscription_id = subscription_id
        self.resource_client = ResourceManagementClient(self.credential, subscription_id)
        self.compute_client = ComputeManagementClient(self.credential, subscription_id)

    def test_connection(self):
        groups = list(self.resource_client.resource_groups.list())
        return {"resource_group_count": len(groups)}

    def list_vms(self):
        vms = []
        for vm in self.compute_client.virtual_machines.list_all():
            vms.append({
                "name": vm.name,
                "location": vm.location,
                "vm_size": vm.hardware_profile.vm_size if vm.hardware_profile else None,
            })
        return vms