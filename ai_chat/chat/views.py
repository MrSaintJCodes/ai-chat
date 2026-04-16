import uuid
import requests
import traceback
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .models import Conversation, ChatSession
from django.http import JsonResponse

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

def generate_chat_title(user_message):
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

    # keep it tidy
    if len(title) > 60:
        title = title[:60].strip()

    return title or "New Chat"

def build_messages(session, new_user_message):
    history = session.messages.all().order_by("created_at")[:10]

    return [
        {
            "role": "system",
            "content": "You are a helpful assistant."
        }
    ] + [
        {"role": m.role, "content": m.content}
        for m in history
    ] + [
        {"role": "user", "content": new_user_message}
    ]

def home_redirect(request):
    latest_session = ChatSession.objects.order_by("-created_at").first()

    if latest_session:
        return redirect("chat", session_id=latest_session.id)

    return render(request, "chat/empty.html")

@require_http_methods(["GET", "POST"])
def chat_view(request, session_id):
    session = ChatSession.objects.get(id=session_id)
    error = ""
    new_title = None

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "chat":
            user_message = request.POST.get("message", "").strip()

            if user_message:
                try:
                    messages = build_messages(session, user_message)

                    # Save user message
                    Conversation.objects.create(
                        session=session,
                        role="user",
                        content=user_message
                    )
                
                    if session.title == "New Chat" and session.messages.filter(role="user").count() == 1:
                        try:
                            session.title = generate_chat_title(user_message)
                            session.save()
                            new_title = session.title
                        except Exception:
                            session.title = user_message[:40]
                            session.save()
                            new_title = session.title

                    # Call Ollama
                    reply = get_ai_reply(messages)

                    # Save reply
                    Conversation.objects.create(
                        session=session,
                        role="assistant",
                        content=reply
                    )

                    # ✅ RETURN JSON (for fetch)
                    if request.headers.get("x-requested-with") == "XMLHttpRequest":
                        return JsonResponse({
                            "success": True,
                            "reply": reply,
                            "title": new_title,
                            "session_id": str(session.id),
                        })
                except Exception as e:
                    error = traceback.format_exc()

                    if request.headers.get("x-requested-with") == "XMLHttpRequest":
                        return JsonResponse({
                            "success": False,
                            "error": error
                        }, status=500)

        elif action == "clear":
            Conversation.objects.filter(session_id=session_id).delete()

        # ✅ fallback (non-AJAX form submit)
        return redirect("chat")

    # GET request
    history = Conversation.objects.filter(
        session_id=session_id
    ).order_by("created_at")[:40]

    sessions = ChatSession.objects.all().order_by("-created_at")

    return render(request, "chat/chat.html", {
        "history": session.messages.all().order_by("created_at"),
        "sessions": sessions,
        "current_session": session,
        "error": error,
    })

def new_chat(request):
    session = ChatSession.objects.create()
    return redirect("chat", session_id=session.id)

@require_http_methods(["POST"])
def delete_chat(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id)
    session.delete()

    current_session_id = request.session.get("session_id")
    if current_session_id == str(session_id):
        request.session.pop("session_id", None)

    next_session = ChatSession.objects.order_by("-created_at").first()

    if next_session:
        request.session["session_id"] = str(next_session.id)
        return redirect("chat", session_id=next_session.id)

    return redirect("chat_home")