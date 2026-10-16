from django.shortcuts import render

# Create your views here.


import secrets
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.http import HttpResponse,HttpResponseBadRequest
from django.shortcuts import redirect
from django.utils.html import escape




GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"




def home(request):
    user = request.session.get("user")
    if user:
        display_name = escape(user["name"] or user["login"])
        avatar = escape(user["avatar_url"] or "")
        return HttpResponse(
            f"<img src='{avatar}' width='60'><br>"
            f"Hello {display_name}! <a href='/logout/'>Logout</a>"
        )
    return HttpResponse("<a href='/login/'>Login with GitHub</a>")

def logout_view(request):
    request.session.flush()
    return redirect("/")

def login_view(request):
    # 1. Create a random, unguessable value
    state = secrets.token_urlsafe(16)

    # 2. Remember it in the user's session
    request.session["oauth_state"] = state
    print("OAuth state")
    print(request.session["oauth_state"])

    # 3. Build the GitHub URL with all the parameters
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_REDIRECT_URI,
        "scope": "read:user",  # <-- this defines WHAT we're asking authorization for
        "state": state,
    }
    url = f"{GITHUB_AUTH_URL}?{urlencode(params)}"

    # 4. Send the browser there
    return redirect(url)


def callback_view(request):
    # 0. Did the user click "Cancel" on GitHub?
    if request.GET.get("error"):
        return HttpResponseBadRequest(f"GitHub error: {request.GET['error']}")

    # 1. Verify the state
    expected_state = request.session.pop("oauth_state", None)
    received_state = request.GET.get("state")
    if not expected_state or received_state != expected_state:
        return HttpResponseBadRequest("Invalid state")

    # 2. Get the temporary code
    code = request.GET.get("code")
    if not code:
        return HttpResponseBadRequest("Missing code")

    # 3. Exchange the code for an access token (server to server)
    response = requests.post(
        GITHUB_TOKEN_URL,
        data={
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": settings.GITHUB_REDIRECT_URI,
        },
        headers={"Accept": "application/json"},
        timeout=10,
    )
    data = response.json()
    access_token = data.get("access_token")
    print('access_token')
    print(access_token)

    if not access_token:
        return HttpResponseBadRequest(f"Token exchange failed: {data}")

        # 4. Use the token to fetch the user's profile
    user_response = requests.get(
        GITHUB_USER_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
        timeout=10,
    )
    if user_response.status_code != 200:
        return HttpResponseBadRequest("Could not fetch GitHub profile")
    profile = user_response.json()
    print(profile)
    # 5. "Log in" by saving minimal info in our own session
    request.session["user"] = {
        "login": profile["login"],
        "name": profile.get("name"),
        "avatar_url": profile.get("avatar_url"),
    }
    return redirect("/")