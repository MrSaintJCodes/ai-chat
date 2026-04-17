from django.urls import path
from . import views

urlpatterns = [
    path("", views.home_redirect, name="chat_home"),
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.EmailLoginView.as_view(), name="login"),
    path("logout/", views.EmailLogoutView.as_view(), name="logout"),
    path("new/", views.new_chat, name="new_chat"),
    path("chat/<uuid:session_id>/", views.chat_view, name="chat"),
    path("chat/<uuid:session_id>/delete/", views.delete_chat, name="delete_chat"),
]