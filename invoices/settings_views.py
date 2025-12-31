from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserDetailsForm, UserProfileForm, NotificationPreferencesForm, PasswordChangeForm
from .models import UserProfile, UserSession

@login_required
def settings_dashboard(request):
    return redirect('invoices:settings_profile')

@login_required
def settings_profile(request):
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        user_form = UserDetailsForm(request.POST, instance=user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('invoices:settings_profile')
    else:
        user_form = UserDetailsForm(instance=user)
        profile_form = UserProfileForm(instance=profile)
        
    return render(request, 'settings/settings_profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'active_tab': 'profile'
    })

@login_required
def settings_business(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Business settings updated.")
            return redirect('invoices:settings_business')
    else:
        form = UserProfileForm(instance=profile)
    return render(request, 'settings/settings_business.html', {'form': form, 'active_tab': 'business'})

@login_required
def settings_notifications(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = NotificationPreferencesForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Notification preferences updated.")
            return redirect('invoices:settings_notifications')
    else:
        form = NotificationPreferencesForm(instance=profile)
    return render(request, 'settings/settings_notifications.html', {'form': form, 'active_tab': 'notifications'})

@login_required
def settings_security(request):
    if request.method == 'POST':
        if 'revoke_session' in request.POST:
            session_id = request.POST.get('revoke_session')
            UserSession.objects.filter(user=request.user, id=session_id).update(is_revoked=True)
            messages.success(request, "Session revoked successfully.")
            return redirect('invoices:settings_security')
        
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            user = request.user
            if user.check_password(form.cleaned_data['current_password']):
                user.set_password(form.cleaned_data['new_password'])
                user.save()
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully.")
                return redirect('invoices:settings_security')
            else:
                form.add_error('current_password', "Incorrect current password.")
    else:
        form = PasswordChangeForm()
    
    sessions = UserSession.objects.filter(user=request.user, is_revoked=False)
    return render(request, 'settings/settings_security.html', {
        'form': form, 
        'sessions': sessions,
        'active_tab': 'security'
    })
