from django.urls import path
from . import views

urlpatterns = [
    path("", views.home_redirect, name="chat_home"),
    path("new/", views.new_chat, name="new_chat"),
    path("chat/<uuid:session_id>/", views.chat_view, name="chat"),
    path("chat/<uuid:session_id>/delete/", views.delete_chat, name="delete_chat"),
]