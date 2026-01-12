from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages

def home(request):
    return render(request, "pages/home-light.html")

def login_view(request):
    # Minimal stub for clean baseline
    return render(request, "pages/home-light.html")

def signup(request):
    # Minimal stub for clean baseline
    return render(request, "pages/home-light.html")

@login_required
def dashboard(request):
    return render(request, "pages/home-light.html")

def logout_view(request):
    logout(request)
    return redirect("home")

def custom_404(request, exception):
    return render(request, "pages/home-light.html", status=404)

def custom_500(request):
    return render(request, "pages/home-light.html", status=500)
