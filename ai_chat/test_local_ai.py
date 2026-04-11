import uuid
import requests
import traceback

def get_ai_reply(messages):
    response = requests.post(
      	"http://localhost:11434/api/chat",
        json={
            "model":    "llama3.2:1b",
            "messages": messages,
            "stream":   False
        },
        timeout=180
    )
    response.raise_for_status()
    return response.json()["message"]["content"]

reply = get_ai_reply([
    {"role": "user", "content": "Test"}
])
print(reply)
