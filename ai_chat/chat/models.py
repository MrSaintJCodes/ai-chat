from django.db import models
import uuid

# Create your models here.
class Conversation(models.Model):
    session_id = models.CharField(max_length=64, db_index=True)
    role       = models.CharField(max_length=16)
    content    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.session_id} — {self.role}"