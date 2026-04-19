import requests
import traceback
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from chat.services.context_builder import build_cloud_context
import markdown

from .forms import SignUpForm, EmailAuthenticationForm, UserPreferenceForm, AWSConnectorForm, AzureConnectorForm, GCPConnectorForm
from .models import Conversation, ChatSession, CloudProviderSetting, UserPreference
from .utils.crypto import encrypt_value, decrypt_value

def generate_chat_title(user_message):
    try:
        response = requests.post(
            f"{settings.OLLAMA_HOST}/api/chat",
            json={
                "model": settings.OLLAMA_TITLE_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Generate a very short title for a chat conversation. "
                            "Use 2 to 6 words maximum. "
                            "Do not use quotes. "
                            "Do not add punctuation unless necessary. "
                            "Only return the title."
                        )
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ],
                "stream": False
            },
            timeout=60
        )
        response.raise_for_status()
        title = response.json()["message"]["content"].strip()
        return title[:60] or "New Chat"
    except Exception:
        return user_message[:40] or "New Chat"


def get_ai_reply(messages):
    response = requests.post(
        f"{settings.OLLAMA_HOST}/api/chat",
        json={
            "model": settings.OLLAMA_MODEL,
            "messages": messages,
            "stream": False
        },
        timeout=180
    )
    response.raise_for_status()
    return response.json()["message"]["content"]

def build_messages(session, new_user_message):
    history = session.messages.all().order_by("created_at")[:5]

    # 👇 NEW: inject cloud context
    cloud_context = build_cloud_context(session.user, new_user_message)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a cloud operations assistant. "
                "You help analyze AWS, Azure, and GCP environments. "
                "Use provided infrastructure data when available."
            )
        }
    ]

    # 👇 ONLY add cloud context if relevant
    if cloud_context:
        messages.append({
            "role": "system",
            "content": f"REAL CLOUD DATA:\n{cloud_context}"
        })

    # history
    messages += [
        {"role": m.role, "content": m.content}
        for m in history
    ]

    # new message
    messages.append({
        "role": "user",
        "content": new_user_message
    })

    return messages


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("chat_home")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data["email"]
            user.username = form.cleaned_data["email"]
            user.set_password(form.cleaned_data["password1"])
            user.save()
            UserPreference.objects.get_or_create(user=user)
            login(request, user)
            return redirect("chat_home")
    else:
        form = SignUpForm()

    return render(request, "chat/signup.html", {"form": form})


class EmailLoginView(LoginView):
    template_name = "chat/login.html"
    authentication_form = EmailAuthenticationForm


class EmailLogoutView(LogoutView):
    pass


@login_required
def home_redirect(request):
    latest_session = ChatSession.objects.filter(user=request.user).order_by("-created_at").first()

    if latest_session:
        return redirect("chat", session_id=latest_session.id)

    return render(request, "chat/empty.html", {
        "sessions": [],
    })


@login_required
def new_chat(request):
    session = ChatSession.objects.create(user=request.user, title="New Chat")
    return redirect("chat", session_id=session.id)


@login_required
@require_http_methods(["POST"])
def delete_chat(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    session.delete()

    next_session = ChatSession.objects.filter(user=request.user).order_by("-created_at").first()

    if next_session:
        return redirect("chat", session_id=next_session.id)

    return redirect("chat_home")


@login_required
@require_http_methods(["GET", "POST"])
def chat_view(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    error = ""
    new_title = None

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "chat":
            user_message = request.POST.get("message", "").strip()

            if user_message:
                try:
                    messages = build_messages(session, user_message)

                    Conversation.objects.create(
                        session=session,
                        role="user",
                        content=user_message
                    )

                    if session.title == "New Chat" and session.messages.filter(role="user").count() == 1:
                        new_title = generate_chat_title(user_message)
                        session.title = new_title
                        session.save()

                    raw_reply = get_ai_reply(messages)

                    html_reply = markdown.markdown(
                        raw_reply,
                        extensions=["fenced_code", "codehilite"]
                    )

                    reply = html_reply

                    Conversation.objects.create(
                        session=session,
                        role="assistant",
                        content=reply
                    )

                    if request.headers.get("x-requested-with") == "XMLHttpRequest":
                        return JsonResponse({
                            "success": True,
                            "reply": reply,
                            "title": new_title,
                            "session_id": str(session.id),
                        })

                except Exception:
                    error = traceback.format_exc()

                    if request.headers.get("x-requested-with") == "XMLHttpRequest":
                        return JsonResponse({
                            "success": False,
                            "error": error
                        }, status=500)

        elif action == "clear":
            session.messages.all().delete()

        return redirect("chat", session_id=session.id)

    history = session.messages.all().order_by("created_at")[:40]
    sessions = ChatSession.objects.filter(user=request.user).order_by("-created_at")

    return render(request, "chat/chat.html", {
        "history": history,
        "error": error,
        "sessions": sessions,
        "current_session": session,
    })

@login_required
def settings_view(request):
    preference, _ = UserPreference.objects.get_or_create(user=request.user)

    aws_config, _ = CloudProviderSetting.objects.get_or_create(
        user=request.user,
        provider="aws",
        defaults={"display_name": "AWS Connector"}
    )
    azure_config, _ = CloudProviderSetting.objects.get_or_create(
        user=request.user,
        provider="azure",
        defaults={"display_name": "Azure Connector"}
    )
    gcp_config, _ = CloudProviderSetting.objects.get_or_create(
        user=request.user,
        provider="gcp",
        defaults={"display_name": "GCP Connector"}
    )

    # decrypt for display
    aws_initial = {
        "enabled": aws_config.enabled,
        "display_name": aws_config.display_name,
        "aws_access_key_id": decrypt_value(aws_config.aws_access_key_id) if aws_config.aws_access_key_id else "",
        "aws_secret_access_key": decrypt_value(aws_config.aws_secret_access_key) if aws_config.aws_secret_access_key else "",
        "aws_region": aws_config.aws_region,
    }

    azure_initial = {
        "enabled": azure_config.enabled,
        "display_name": azure_config.display_name,
        "azure_tenant_id": azure_config.azure_tenant_id,
        "azure_client_id": azure_config.azure_client_id,
        "azure_client_secret": decrypt_value(azure_config.azure_client_secret) if azure_config.azure_client_secret else "",
        "azure_subscription_id": azure_config.azure_subscription_id,
    }

    gcp_initial = {
        "enabled": gcp_config.enabled,
        "display_name": gcp_config.display_name,
        "gcp_project_id": gcp_config.gcp_project_id,
        "gcp_service_account_json": decrypt_value(gcp_config.gcp_service_account_json) if gcp_config.gcp_service_account_json else "",
    }

    if request.method == "POST":
        preference_form = UserPreferenceForm(request.POST, instance=preference)
        aws_form = AWSConnectorForm(request.POST, instance=aws_config, prefix="aws")
        azure_form = AzureConnectorForm(request.POST, instance=azure_config, prefix="azure")
        gcp_form = GCPConnectorForm(request.POST, instance=gcp_config, prefix="gcp")

        if all([preference_form.is_valid(), aws_form.is_valid(), azure_form.is_valid(), gcp_form.is_valid()]):
            preference_form.save()

            aws_obj = aws_form.save(commit=False)
            aws_obj.aws_access_key_id = encrypt_value(aws_form.cleaned_data.get("aws_access_key_id", ""))
            aws_obj.aws_secret_access_key = encrypt_value(aws_form.cleaned_data.get("aws_secret_access_key", ""))
            aws_obj.save()

            azure_obj = azure_form.save(commit=False)
            azure_obj.azure_client_secret = encrypt_value(azure_form.cleaned_data.get("azure_client_secret", ""))
            azure_obj.save()

            gcp_obj = gcp_form.save(commit=False)
            gcp_obj.gcp_service_account_json = encrypt_value(gcp_form.cleaned_data.get("gcp_service_account_json", ""))
            gcp_obj.save()

            messages.success(request, "Preferences and cloud connector settings saved.")
            return redirect("settings")
    else:
        preference_form = UserPreferenceForm(instance=preference)
        aws_form = AWSConnectorForm(instance=aws_config, prefix="aws", initial=aws_initial)
        azure_form = AzureConnectorForm(instance=azure_config, prefix="azure", initial=azure_initial)
        gcp_form = GCPConnectorForm(instance=gcp_config, prefix="gcp", initial=gcp_initial)

    return render(request, "chat/settings.html", {
        "preference_form": preference_form,
        "aws_form": aws_form,
        "azure_form": azure_form,
        "gcp_form": gcp_form,
    })
    
class CustomPasswordChangeView(SuccessMessageMixin, PasswordChangeView):
    template_name = "chat/password_change.html"
    success_url = reverse_lazy("settings")
    success_message = "Your password was updated successfully."
    
def landing_view(request):
    return render(request, "chat/landing.html")
