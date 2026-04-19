from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from .models import UserPreference, CloudProviderSetting


class UserPreferenceForm(forms.ModelForm):
    class Meta:
        model = UserPreference
        fields = ["theme", "smooth_animations"]


class CloudProviderSettingForm(forms.ModelForm):
    class Meta:
        model = CloudProviderSetting
        fields = ["enabled", "display_name"]


class SignUpForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["username", "email"]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")

        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email")

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()


class AWSConnectorForm(forms.ModelForm):
    aws_secret_access_key = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=True)
    )

    class Meta:
        model = CloudProviderSetting
        fields = [
            "enabled",
            "display_name",
            "aws_access_key_id",
            "aws_secret_access_key",
            "aws_region",
        ]


class AzureConnectorForm(forms.ModelForm):
    azure_client_secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=True)
    )

    class Meta:
        model = CloudProviderSetting
        fields = [
            "enabled",
            "display_name",
            "azure_tenant_id",
            "azure_client_id",
            "azure_client_secret",
            "azure_subscription_id",
        ]


class GCPConnectorForm(forms.ModelForm):
    gcp_service_account_json = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 8})
    )

    class Meta:
        model = CloudProviderSetting
        fields = [
            "enabled",
            "display_name",
            "gcp_project_id",
            "gcp_service_account_json",
        ]