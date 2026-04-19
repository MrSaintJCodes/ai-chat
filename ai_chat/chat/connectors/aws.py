import boto3
from .base import BaseConnector


class AWSConnector(BaseConnector):
    provider = "aws"

    def __init__(self, access_key_id: str, secret_access_key: str, region: str):
        self.session = boto3.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region or "us-east-1",
        )
        self.ec2 = self.session.client("ec2")
        self.cloudwatch = self.session.client("cloudwatch")
        self.s3 = self.session.client("s3")

    def test_connection(self):
        return self.ec2.describe_regions()

    def list_instances(self):
        response = self.ec2.describe_instances()
        instances = []

        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                instances.append({
                    "instance_id": instance.get("InstanceId"),
                    "instance_type": instance.get("InstanceType"),
                    "state": instance.get("State", {}).get("Name"),
                    "private_ip": instance.get("PrivateIpAddress"),
                })

        return instances