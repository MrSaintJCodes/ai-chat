import json
from google.oauth2 import service_account
from google.cloud import compute_v1
from .base import BaseConnector


class GCPConnector(BaseConnector):
    provider = "gcp"

    def __init__(self, service_account_json: str, project_id: str):
        info = json.loads(service_account_json)
        self.credentials = service_account.Credentials.from_service_account_info(info)
        self.project_id = project_id or info.get("project_id")
        self.instances_client = compute_v1.InstancesClient(credentials=self.credentials)

    def test_connection(self):
        request = compute_v1.AggregatedListInstancesRequest(project=self.project_id)
        pager = self.instances_client.aggregated_list(request=request)
        # just prove access works
        count = 0
        for _, scoped_list in pager:
            count += len(scoped_list.instances or [])
        return {"instance_count": count}

    def list_instances(self):
        request = compute_v1.AggregatedListInstancesRequest(project=self.project_id)
        pager = self.instances_client.aggregated_list(request=request)

        instances = []
        for zone, scoped_list in pager:
            for instance in scoped_list.instances or []:
                instances.append({
                    "name": instance.name,
                    "zone": zone,
                    "machine_type": instance.machine_type.split("/")[-1] if instance.machine_type else None,
                    "status": instance.status,
                })

        return instances