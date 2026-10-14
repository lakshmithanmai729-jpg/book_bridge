from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from .forms import SignUpForm
from .models import UserProfile


def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.get_or_create(user=user, defaults={'name': user.username})
            return redirect('accounts:login')
    else:
        form = SignUpForm()
    return render(request, 'accounts/signup.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            UserProfile.objects.get_or_create(user=user, defaults={'name': user.username})
            return redirect('core:home')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


def user_logout(request):
    logout(request)
    return redirect('core:home')


@login_required
def profile(request):
    profile_obj, _ = UserProfile.objects.get_or_create(
        user=request.user, 
        defaults={'name': request.user.username}
    )
    return render(request, 'accounts/profile.html', {'profile': profile_obj})


@login_required
def profile_edit(request):
    profile_obj, _ = UserProfile.objects.get_or_create(
        user=request.user, 
        defaults={'name': request.user.username}
    )
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        email = request.POST.get('email', '').strip()
        location = request.POST.get('location', '').strip()
        privacy = request.POST.get('account_privacy', 'private')

        if name:
            profile_obj.name = name
        profile_obj.phone_number = phone_number
        profile_obj.location = location
        profile_obj.account_privacy = privacy
        profile_obj.save()

        if email:
            request.user.email = email
            request.user.save()

        return redirect('accounts:profile')

    return render(request, 'accounts/profile_edit.html', {'profile': profile_obj})


@login_required
def messages_view(request):
    return render(request, 'accounts/messages.html')