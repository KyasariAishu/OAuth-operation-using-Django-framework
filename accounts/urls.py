from django.urls import path
from . import views

urlpatterns = [
    path("", views.home),
    path("login/", views.login_view),
    path("oauth/callback/", views.callback_view),
    path("logout/", views.logout_view),
]