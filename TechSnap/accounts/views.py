from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .forms import  SignUpForm, LoginForm, ProfileUpdateForm
from organizations.models import Membership, Invite


def home_view(request):
    return render(request, 'accounts/home.html')


def signup_view(request):
    """Handles user signup and automatic joining of organizations via invite."""
    if request.user.is_authenticated:
        return redirect('accounts:choose_action')
    
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # ✅ Check for any pending invites using the same email
            invites = Invite.objects.filter(
                email=user.email,
                accepted=False,
                expires_at__gt=timezone.now()
            )
            for invite in invites:
                try:
                    invite.accept(user)  # Automatically creates Membership
                    messages.success(request, f"You’ve been added to {invite.org.name}.")
                except Exception as e:
                    print("Invite accept error:", e)

            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('accounts:choose_action')
    else:
        form = SignUpForm()
    
    return render(request, 'accounts/signup.html', {'form': form})


def login_view(request):
    """Handles user login and automatic linking with pending invites."""
    if request.user.is_authenticated:
        return redirect('accounts:choose_action')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)

                # ✅ Auto-join pending invites
                invites = Invite.objects.filter(
                    email=user.email,
                    accepted=False,
                    expires_at__gt=timezone.now()
                )
                for invite in invites:
                    try:
                        invite.accept(user)
                        messages.success(request, f"You’ve been added to {invite.org.name}.")
                    except Exception as e:
                        print("Invite accept error:", e)

                messages.success(request, f'Welcome back, {user.first_name}!')
                return redirect('accounts:choose_action')
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('accounts:login')


@login_required
def choose_action(request):
    """Shows all organizations the user belongs to."""
    memberships = Membership.objects.filter(
        user=request.user,
        is_active=True
    ).select_related("org")

    has_organizations = memberships.exists()

    context = {
        "memberships": memberships,
        "has_organizations": has_organizations,
    }
    return render(request, "accounts/choose_action.html", context)

@login_required
def profile_settings(request):
    user = request.user
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("accounts:profile_settings")
    else:
        form = ProfileUpdateForm(instance=user)
    return render(request, "accounts/profile_settings.html", {"form": form})
