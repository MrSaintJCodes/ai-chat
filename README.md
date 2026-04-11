# Lab Chatbot — Django AI Chat Application

A production-ready AI chatbot built with Django, powered by Ollama (llama3.2:1b), and backed by PostgreSQL. Conversation history is persisted per session and served via Apache mod_wsgi.

---

## Table of contents

- [Overview](#overview)
- [Project structure](#project-structure)
- [Requirements](#requirements)
- [Local development](#local-development)
- [Environment variables](#environment-variables)
- [Running with Ollama](#running-with-ollama)
- [Database](#database)
- [Deployment](#deployment)
- [How it works](#how-it-works)

---

## Overview

This Django application provides a web-based chat interface that:

- Accepts user messages via a POST form
- Maintains per-session conversation history in PostgreSQL
- Sends the full conversation context to a local Ollama instance (llama3.2:1b)
- Saves both the user message and AI reply to the database
- Displays the full conversation history on page load

The app uses SQLite locally for development and PostgreSQL in production.

---

## Project structure

```
django/
├── manage.py
├── requirements.txt
├── ai_chat/                  # Django project
│   ├── settings.py           # environment-driven config
│   ├── urls.py               # root URL config
│   └── wsgi.py               # WSGI entrypoint for Apache
└── chat/                     # Django app
    ├── models.py             # Conversation model
    ├── views.py              # chat_view, get_ai_reply
    ├── urls.py               # app URL config
    └── templates/
        └── chat/
            ├── base.html     # base layout
            └── chat.html     # chat interface
```

---

## Requirements

- Python 3.8+
- pip
- Ollama running locally or on a remote host
- PostgreSQL (production) or SQLite (local dev)

Install Python dependencies:

```bash
pip install -r requirements.txt
```

`requirements.txt`:
```
django>=4.2
psycopg2-binary
requests
```

---

## Local development

### 1. Clone the repo

```bash
git clone https://github.com/<your-username>/aws-sysadmin-lab.git
cd aws-sysadmin-lab/django
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Set environment variables

```bash
export DJANGO_SECRET_KEY="local-dev-secret-key"
export DEBUG="True"
export OLLAMA_HOST="http://localhost:11434"
export OLLAMA_MODEL="llama3.2:1b"
```

Leave `DB_HOST` unset to use SQLite automatically.

### 4. Run migrations

```bash
python3 manage.py migrate
```

### 5. Start the development server

```bash
python3 manage.py runserver
```

Visit `http://localhost:8000` to open the chat interface.

---

## Environment variables

| Variable | Description | Default |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django secret key | `local-dev-secret-key` |
| `DEBUG` | Enable debug mode | `True` |
| `DB_HOST` | PostgreSQL host (unset = SQLite) | unset |
| `DB_NAME` | PostgreSQL database name | `labdb` |
| `DB_USER` | PostgreSQL username | `labadmin` |
| `DB_PASS` | PostgreSQL password | — |
| `OLLAMA_HOST` | Ollama API base URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama model name | `llama3.2:1b` |

---

## Running with Ollama

Ollama must be running before starting Django.

### Install Ollama

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh
```

### Pull the model

```bash
ollama pull llama3.2:1b
```

### Start Ollama

```bash
ollama serve
```

Verify it is working:

```bash
curl http://localhost:11434/api/tags
```

### Test the AI reply directly

```python
import requests

response = requests.post(
    "http://localhost:11434/api/chat",
    json={
        "model": "llama3.2:1b",
        "messages": [{"role": "user", "content": "Say hello"}],
        "stream": False
    },
    timeout=180
)
print(response.json()["message"]["content"])
```

---

## Database

### Model

The `Conversation` model stores every message exchanged in a session:

```python
class Conversation(models.Model):
    session_id = models.CharField(max_length=64, db_index=True)
    role       = models.CharField(max_length=16)   # "user" or "assistant"
    content    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
```

### Message flow

Each user message triggers the following sequence:

```
1. Fetch conversation history from DB   (all prior messages for this session)
2. Build message list                   (system prompt + history + new message)
3. Save user message to DB
4. Call Ollama API with full context
5. Save AI reply to DB
6. Redirect to GET — render updated history
```

This ensures Ollama only generates one reply per user message and the database always contains the full conversation history in order.

### Inspect the database locally

```bash
python3 manage.py shell -c "
from chat.models import Conversation
for m in Conversation.objects.all().order_by('created_at'):
    print(m.role, '|', m.content[:80])
"
```

### Clear all conversations

```bash
python3 manage.py shell -c "
from chat.models import Conversation
Conversation.objects.all().delete()
print('Cleared')
"
```

---

## Deployment

### Production environment variables

Set these via Apache `SetEnv` directives in the mod_wsgi config:

```apache
SetEnv DJANGO_SETTINGS_MODULE labchat.settings
SetEnv DJANGO_SECRET_KEY      <your-secret-key>
SetEnv DEBUG                  False
SetEnv DB_HOST                <rds-endpoint>
SetEnv DB_NAME                labdb
SetEnv DB_USER                labadmin
SetEnv DB_PASS                <password>
SetEnv OLLAMA_HOST            http://<ollama-alb-dns>:11434
SetEnv OLLAMA_MODEL           llama3.2:1b
```

### Generate a Django secret key

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

### Run migrations in production

```bash
cd /var/www/labchat/django
python3 manage.py migrate --noinput
python3 manage.py collectstatic --noinput
```

### Restart Apache

```bash
sudo systemctl restart httpd
```

### Check logs

```bash
# Apache error log
sudo tail -50 /var/log/httpd/labchat-error.log

# Apache access log
sudo tail -50 /var/log/httpd/labchat-access.log

# User data bootstrap log
sudo tail -50 /var/log/user-data.log
```

---

## How it works

```
Browser
  |
  | POST /  (user message)
  v
Apache (mod_wsgi)
  |
  v
Django — chat_view()
  |
  |-- 1. Fetch session history from PostgreSQL
  |-- 2. Build message list (system + history + new message)
  |-- 3. Save user message to PostgreSQL
  |-- 4. POST to Ollama /api/chat
  |-- 5. Save AI reply to PostgreSQL
  |
  | redirect to GET /
  v
Django — render chat.html
  |
  v
Browser (updated conversation)
```

Sessions are managed by Django's session framework backed by the database. Each browser gets a unique `session_id` so conversations are isolated per user. Since both EC2 instances share the same RDS PostgreSQL database, conversations are consistent regardless of which instance the ALB routes to.
