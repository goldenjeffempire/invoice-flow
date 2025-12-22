"""
Google OAuth views for InvoiceFlow.
Implements Google OAuth 2.0 authentication flow using oauthlib.
Based on blueprint:flask_google_oauth integration.
"""

import json
import os
import secrets

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.shortcuts import redirect
from django.urls import reverse
from oauthlib.oauth2 import WebApplicationClient

from .models import SocialAccount, UserProfile, UserSession

User = get_user_model()

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"


def get_redirect_uri(request):
    """Build the OAuth callback redirect URI."""
    if os.environ.get("REPLIT_DEV_DOMAIN"):
        return f'https://{os.environ["REPLIT_DEV_DOMAIN"]}/oauth/google/callback/'
    
    scheme = "https" if request.is_secure() else "http"
    host = request.get_host()
    if "localhost" not in host and "127.0.0.1" not in host:
        scheme = "https"
    
    return f"{scheme}://{host}/oauth/google/callback/"


def google_login(request):
    """Initiate Google OAuth login flow."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        messages.error(
            request,
            "Google login is not configured. Please contact support."
        )
        return redirect("login")
    
    try:
        client = WebApplicationClient(GOOGLE_CLIENT_ID)
        
        google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL, timeout=10).json()
        authorization_endpoint = google_provider_cfg["authorization_endpoint"]
        
        redirect_uri = get_redirect_uri(request)
        
        state = secrets.token_urlsafe(32)
        request.session["oauth_state"] = state
        
        request_uri = client.prepare_request_uri(
            authorization_endpoint,
            redirect_uri=redirect_uri,
            scope=["openid", "email", "profile"],
            state=state,
        )
        
        return redirect(request_uri)
    
    except requests.RequestException:
        messages.error(
            request,
            "Could not connect to Google. Please try again later."
        )
        return redirect("login")
    except Exception:
        messages.error(
            request,
            "An error occurred. Please try again."
        )
        return redirect("login")


def google_callback(request):
    """Handle Google OAuth callback and create/login user."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        messages.error(request, "Google login is not configured.")
        return redirect("login")
    
    code = request.GET.get("code")
    state = request.GET.get("state")
    error = request.GET.get("error")
    
    if error:
        messages.error(request, "Google login was cancelled or failed.")
        return redirect("login")
    
    if not code:
        messages.error(request, "Invalid response from Google.")
        return redirect("login")
    
    stored_state = request.session.pop("oauth_state", None)
    if not stored_state or stored_state != state:
        messages.error(request, "Invalid security token. Please try again.")
        return redirect("login")
    
    try:
        client = WebApplicationClient(GOOGLE_CLIENT_ID)
        
        google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL, timeout=10).json()
        token_endpoint = google_provider_cfg["token_endpoint"]
        
        redirect_uri = get_redirect_uri(request)
        
        current_url = request.build_absolute_uri()
        if current_url.startswith("http://") and "localhost" not in current_url:
            current_url = current_url.replace("http://", "https://", 1)
        
        token_url, headers, body = client.prepare_token_request(
            token_endpoint,
            authorization_response=current_url,
            redirect_url=redirect_uri,
            code=code,
        )
        
        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
            timeout=10,
        )
        
        if token_response.status_code != 200:
            messages.error(request, "Failed to verify with Google. Please try again.")
            return redirect("login")
        
        client.parse_request_body_response(json.dumps(token_response.json()))
        
        userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
        uri, headers, body = client.add_token(userinfo_endpoint)
        userinfo_response = requests.get(uri, headers=headers, data=body, timeout=10)
        
        if userinfo_response.status_code != 200:
            messages.error(request, "Failed to get user info from Google.")
            return redirect("login")
        
        userinfo = userinfo_response.json()
        
        if not userinfo.get("email_verified"):
            messages.error(
                request,
                "Your Google email is not verified. Please verify your email with Google first."
            )
            return redirect("login")
        
        google_id = userinfo.get("sub")
        email = userinfo.get("email")
        name = userinfo.get("name", "")
        given_name = userinfo.get("given_name", "")
        
        if not google_id or not email:
            messages.error(request, "Could not retrieve your information from Google.")
            return redirect("login")
        
        social_account = SocialAccount.objects.filter(
            provider="google",
            provider_id=google_id
        ).first()
        
        if social_account:
            user = social_account.user
            social_account.email = email
            social_account.name = name
            social_account.extra_data = userinfo
            social_account.save()
        else:
            user = User.objects.filter(email=email).first()
            
            if user:
                SocialAccount.objects.create(
                    user=user,
                    provider="google",
                    provider_id=google_id,
                    email=email,
                    name=name,
                    extra_data=userinfo,
                )
            else:
                base_username = email.split("@")[0]
                username = base_username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1
                
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=given_name or name.split()[0] if name else "",
                    last_name=" ".join(name.split()[1:]) if name and len(name.split()) > 1 else "",
                )
                user.is_active = True
                user.save()
                
                UserProfile.objects.get_or_create(user=user)
                
                SocialAccount.objects.create(
                    user=user,
                    provider="google",
                    provider_id=google_id,
                    email=email,
                    name=name,
                    extra_data=userinfo,
                )
        
        login(request, user)
        
        try:
            client_ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
            if not client_ip:
                client_ip = request.META.get("REMOTE_ADDR", "unknown")
            user_agent = request.META.get("HTTP_USER_AGENT", "")
            
            UserSession.create_session(
                user=user,
                session_key=request.session.session_key or "",
                ip_address=client_ip,
                user_agent=user_agent,
            )
        except Exception:
            pass
        
        messages.success(request, f"Welcome, {user.first_name or user.username}!")
        return redirect("dashboard")
    
    except requests.RequestException:
        messages.error(request, "Could not connect to Google. Please try again later.")
        return redirect("login")
    except Exception:
        messages.error(request, "An error occurred during login. Please try again.")
        return redirect("login")
