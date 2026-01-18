"""
GitHub OAuth views for InvoiceFlow.
Implements GitHub OAuth 2.0 authentication flow using oauthlib.
"""

import json
import os
import secrets

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.shortcuts import redirect
from django.utils import timezone
from django.urls import reverse
from oauthlib.oauth2 import WebApplicationClient

from .models import SocialAccount, UserProfile, UserSession

User = get_user_model()

GITHUB_CLIENT_ID = os.environ.get("GITHUB_OAUTH_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_OAUTH_CLIENT_SECRET", "")
GITHUB_AUTHORIZATION_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_API_URL = "https://api.github.com/user"
GITHUB_EMAILS_API_URL = "https://api.github.com/user/emails"


def get_github_redirect_uri(request):
    """Build the OAuth callback redirect URI for GitHub."""
    if os.environ.get("REPLIT_DEV_DOMAIN"):
        return f'https://{os.environ["REPLIT_DEV_DOMAIN"]}/oauth/github/callback/'
    
    scheme = "https" if request.is_secure() else "http"
    host = request.get_host()
    if "localhost" not in host and "127.0.0.1" not in host:
        scheme = "https"
    
    return f"{scheme}://{host}/oauth/github/callback/"


def github_login(request):
    """Initiate GitHub OAuth login flow."""
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        messages.error(
            request,
            "GitHub login is not configured. Please contact support."
        )
        return redirect("invoices:login")
    
    try:
        client = WebApplicationClient(GITHUB_CLIENT_ID)
        
        redirect_uri = get_github_redirect_uri(request)
        
        state = secrets.token_urlsafe(32)
        request.session["github_oauth_state"] = state
        
        request_uri = client.prepare_request_uri(
            GITHUB_AUTHORIZATION_URL,
            redirect_uri=redirect_uri,
            scope=["user:email", "read:user"],
            state=state,
        )
        
        return redirect(request_uri)
    
    except Exception:
        messages.error(
            request,
            "An error occurred. Please try again."
        )
        return redirect("invoices:login")


def github_callback(request):
    """Handle GitHub OAuth callback and create/login user."""
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        messages.error(request, "GitHub login is not configured.")
        return redirect("invoices:login")
    
    code = request.GET.get("code")
    state = request.GET.get("state")
    error = request.GET.get("error")
    
    if error:
        messages.error(request, "GitHub login was cancelled or failed.")
        return redirect("invoices:login")
    
    if not code:
        messages.error(request, "Invalid response from GitHub.")
        return redirect("invoices:login")
    
    stored_state = request.session.pop("github_oauth_state", None)
    if not stored_state or stored_state != state:
        messages.error(request, "Invalid security token. Please try again.")
        return redirect("invoices:login")
    
    try:
        token_response = requests.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": get_github_redirect_uri(request),
            },
            headers={"Accept": "application/json"},
            timeout=10,
        )
        
        if token_response.status_code != 200:
            messages.error(request, "Failed to verify with GitHub. Please try again.")
            return redirect("invoices:login")
        
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            messages.error(request, "Failed to get access token from GitHub.")
            return redirect("invoices:login")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        user_response = requests.get(GITHUB_USER_API_URL, headers=headers, timeout=10)
        
        if user_response.status_code != 200:
            messages.error(request, "Failed to get user info from GitHub.")
            return redirect("invoices:login")
        
        userinfo = user_response.json()
        
        github_id = str(userinfo.get("id"))
        email = userinfo.get("email")
        name = userinfo.get("name") or userinfo.get("login", "")
        login_username = userinfo.get("login", "")
        
        if not email:
            emails_response = requests.get(GITHUB_EMAILS_API_URL, headers=headers, timeout=10)
            if emails_response.status_code == 200:
                emails = emails_response.json()
                for email_obj in emails:
                    if email_obj.get("primary") and email_obj.get("verified"):
                        email = email_obj.get("email")
                        break
                if not email and emails:
                    for email_obj in emails:
                        if email_obj.get("verified"):
                            email = email_obj.get("email")
                            break
        
        if not github_id or not email:
            messages.error(request, "Could not retrieve your information from GitHub. Please ensure your email is public or verified.")
            return redirect("invoices:login")
        
        social_account = SocialAccount.objects.filter(
            provider="github",
            provider_id=github_id,
        ).first()
        
        if social_account:
            user = social_account.user
            social_account.access_token = access_token or social_account.access_token
            social_account.token_scopes = token_data.get("scope", "")
            social_account.avatar_url = userinfo.get("avatar_url", "")
            social_account.last_synced = timezone.now()
            social_account.save()
        else:
            user = User.objects.filter(email=email).first()
            
            if user:
                if not user.is_active:
                    messages.error(request, "This account is inactive. Please verify your email.")
                    return redirect("invoices:login")
                profile, _ = UserProfile.objects.get_or_create(user=user)
                if not profile.email_verified:
                    profile.email_verified = True
                    profile.save(update_fields=["email_verified"])
                SocialAccount.objects.create(
                    user=user,
                    provider="github",
                    provider_id=github_id,
                    access_token=access_token or "",
                    token_scopes=token_data.get("scope", ""),
                    avatar_url=userinfo.get("avatar_url", ""),
                    last_synced=timezone.now(),
                )
            else:
                base_username = login_username or email.split("@")[0]
                username = base_username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1
                
                first_name = ""
                last_name = ""
                if name:
                    name_parts = name.split()
                    first_name = name_parts[0] if name_parts else ""
                    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                )
                user.is_active = True
                user.save()

                profile, _ = UserProfile.objects.get_or_create(user=user)
                if not profile.email_verified:
                    profile.email_verified = True
                    profile.save(update_fields=["email_verified"])
                
                SocialAccount.objects.create(
                    user=user,
                    provider="github",
                    provider_id=github_id,
                    access_token=access_token or "",
                    token_scopes=token_data.get("scope", ""),
                    avatar_url=userinfo.get("avatar_url", ""),
                    last_synced=timezone.now(),
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
        return redirect("invoices:dashboard")
    
    except requests.RequestException:
        messages.error(request, "Could not connect to GitHub. Please try again later.")
        return redirect("invoices:login")
    except Exception:
        messages.error(request, "An error occurred during login. Please try again.")
        return redirect("invoices:login")
