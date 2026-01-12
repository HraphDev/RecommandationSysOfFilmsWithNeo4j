# film_app/views/auth.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import User

# Registration View
def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        
        # Validation
        errors = []
        
        # Username validation
        if not username:
            errors.append("Le nom d'utilisateur est requis")
        elif len(username) < 3:
            errors.append("Le nom d'utilisateur doit contenir au moins 3 caractères")
        elif User.objects.filter(username=username).exists():
             errors.append("Ce nom d'utilisateur est déjà pris")
        
        # Email validation
        if not email:
            errors.append("L'email est requis")
        elif '@' not in email:
            errors.append("Email invalide")
        elif User.objects.filter(email=email).exists():
            errors.append("Cet email est déjà utilisé")
        
        # Password validation
        if not password:
            errors.append("Le mot de passe est requis")
        elif len(password) < 6:
            errors.append("Le mot de passe doit contenir au moins 6 caractères")
        elif password != confirm_password:
            errors.append("Les mots de passe ne correspondent pas")
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'auth/register.html', {
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
            })
        
        # Create user
        try:
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_active=True
            )
            user.set_password(password)
            user.save()
            
            # Auto-login after registration
            auth_login(request, user, backend='film_app.backends.Neo4jAuthBackend')
            
            messages.success(request, f"Bienvenue {user.get_full_name()}! Votre compte a été créé avec succès.")
            return redirect('home')
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la création du compte: {str(e)}")
            return render(request, 'auth/register.html', {
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
            })
    
    return render(request, 'auth/register.html')

# Login View
def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username_or_email = request.POST.get('username_or_email', '').strip()
        password = request.POST.get('password', '').strip()
        remember_me = request.POST.get('remember_me') == 'on'
        
        if not username_or_email or not password:
            messages.error(request, "Veuillez remplir tous les champs")
            return render(request, 'auth/login.html')
        
        # Authenticate user (support email or username)
        user = None
        if '@' in username_or_email:
            # Try to find by email
            try:
                user_obj = User.objects.get(email=username_or_email)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None
        else:
            # Use as username
            user = authenticate(request, username=username_or_email, password=password)
        
        if user is not None:
            if not user.is_active:
                messages.error(request, "Votre compte est désactivé. Contactez l'administrateur.")
                return render(request, 'auth/login.html')
            
            auth_login(request, user)
            user.last_login = timezone.now()
            user.save()
            
            if not remember_me:
                request.session.set_expiry(0)
            
            messages.success(request, f"Bon retour, {user.get_full_name()}!")
            
            if user.is_admin:
                return redirect('admin_dashboard')
            else:
                return redirect('home')
        else:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect")
    
    return render(request, 'auth/login.html')

# Logout View
def logout_view(request):
    auth_logout(request)
    messages.success(request, "Vous avez été déconnecté avec succès.")
    return redirect('home')

# Profile View
@login_required
def profile_view(request):
    user = request.user
    context = {
        'user': user,
        'favorites_count': user.get_favorites_count(),
        'watchlist_count': len(user.watchlist),
        'watched_count': len(user.watched_movies),
    }
    return render(request, 'auth/profile.html', context)

# Update Profile View
@login_required
def update_profile_view(request):
    user = request.user
    
    if request.method == 'POST':
        # Update basic info
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        
        # Update email if changed
        new_email = request.POST.get('email', '').strip()
        if new_email and new_email != user.email:
            if User.nodes.filter(email=new_email):
                messages.error(request, "Cet email est déjà utilisé")
            else:
                user.email = new_email
        
        # Update password if provided
        current_password = request.POST.get('current_password', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        
        if current_password and new_password:
            if user.check_password(current_password):
                if new_password == confirm_password:
                    if len(new_password) >= 6:
                        user.set_password(new_password)
                        messages.success(request, "Mot de passe mis à jour")
                    else:
                        messages.error(request, "Le mot de passe doit contenir au moins 6 caractères")
                else:
                    messages.error(request, "Les nouveaux mots de passe ne correspondent pas")
            else:
                messages.error(request, "Mot de passe actuel incorrect")
        
        # Save changes
        user.save()
        messages.success(request, "Profil mis à jour avec succès")
        return redirect('profile')
    
    return render(request, 'auth/update_profile.html', {'user': user})