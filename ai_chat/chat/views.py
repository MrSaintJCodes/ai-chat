import requests
import traceback
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from .forms import SignUpForm, EmailAuthenticationForm
from .models import Conversation, ChatSession


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
    history = list(
        session.messages.all()
        .order_by("created_at")[:5]
        .values("role", "content")
    )

    return [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant running on a "
                "production-grade AWS infrastructure built with "
                "Terraform and Ansible. The stack includes: 3-tier VPC, "
                "ALB, Auto Scaling Group, EFS, RDS PostgreSQL, WAF, "
                "CloudWatch, AWS Backup, Secrets Manager, and IAM "
                "least privilege. Be concise and helpful."
            )
        }
    ] + [
        {"role": m["role"], "content": m["content"]}
        for m in history
    ] + [
        {"role": "user", "content": new_user_message}
    ]


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

    return render(request, "chat/empty.html")


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

                    reply = get_ai_reply(messages)

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