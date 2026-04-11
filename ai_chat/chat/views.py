import uuid
import requests
import traceback
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .models import Conversation

def get_ai_reply(messages):
    response = requests.post(
        f"{settings.OLLAMA_HOST}/api/chat",
        json={
            "model":    settings.OLLAMA_MODEL,
            "messages": messages,
            "stream":   False
        },
        timeout=180
    )
    response.raise_for_status()
    return response.json()["message"]["content"]

def get_or_create_session(request):
    if "session_id" not in request.session:
        request.session["session_id"] = str(uuid.uuid4())
    return request.session["session_id"]

def build_messages(session_id, new_user_message):
    # Get history BEFORE the new message
    history = list(
        Conversation.objects.filter(session_id=session_id)
        .order_by("created_at")
        .values("role", "content")
    )

    # System prompt + history + new message
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

@require_http_methods(["GET", "POST"])
def chat_view(request):
    session_id = get_or_create_session(request)
    error = ""

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "chat":
            user_message = request.POST.get("message", "").strip()
            if user_message:
                try:
                    # Step 1 — build message list from history
                    # BEFORE saving the new message
                    messages = build_messages(session_id, user_message)

                    # Step 2 — save user message to DB
                    Conversation.objects.create(
                        session_id=session_id,
                        role="user",
                        content=user_message
                    )

                    # Step 3 — call Ollama with full context
                    reply = get_ai_reply(messages)

                    # Step 4 — save AI reply to DB
                    Conversation.objects.create(
                        session_id=session_id,
                        role="assistant",
                        content=reply
                    )

                except Exception as e:
                    error = traceback.format_exc()

        elif action == "clear":
            Conversation.objects.filter(session_id=session_id).delete()

        if error:
            history = Conversation.objects.filter(
                session_id=session_id
            ).order_by("created_at")[:40]
            return render(request, "chat/chat.html", {
                "history": history,
                "error":   error
            })

        return redirect("chat")

    history = Conversation.objects.filter(
        session_id=session_id
    ).order_by("created_at")[:40]

    return render(request, "chat/chat.html", {
        "history": history,
        "error":   error,
    })