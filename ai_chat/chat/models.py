import uuid
from django.db import models
from django.contrib.auth.models import User

class UserPreference(models.Model):
    THEME_CHOICES = [
        ("light", "Light"),
        ("dark", "Dark"),
        ("system", "System"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="preferences")
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, default="system")
    smooth_animations = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} preferences"


class CloudProviderSetting(models.Model):
    PROVIDER_CHOICES = [
        ("aws", "AWS"),
        ("azure", "Azure"),
        ("gcp", "GCP"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cloud_settings")
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    enabled = models.BooleanField(default=False)
    display_name = models.CharField(max_length=120, blank=True, default="")

    # AWS
    aws_access_key_id = models.TextField(blank=True, default="")
    aws_secret_access_key = models.TextField(blank=True, default="")
    aws_region = models.CharField(max_length=64, blank=True, default="")

    # Azure
    azure_tenant_id = models.CharField(max_length=128, blank=True, default="")
    azure_client_id = models.CharField(max_length=128, blank=True, default="")
    azure_client_secret = models.TextField(blank=True, default="")
    azure_subscription_id = models.CharField(max_length=128, blank=True, default="")

    # GCP
    gcp_project_id = models.CharField(max_length=128, blank=True, default="")
    gcp_service_account_json = models.TextField(blank=True, default="")

    # Optional flexible config for future use
    config_json = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "provider")

    def __str__(self):
        return f"{self.user.username} - {self.provider}"

class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_sessions")
    title = models.CharField(max_length=120, default="New Chat")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.title}"

class Conversation(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=16)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.session.id} — {self.role}"
    