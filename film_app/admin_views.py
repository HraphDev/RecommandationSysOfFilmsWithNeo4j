# film_app/views/admin.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from .models import User
from .neo4j_driver import get_session

# Admin check decorator
def admin_required(view_func):
    decorated_view_func = login_required(
        user_passes_test(
            lambda u: u.is_admin,
            login_url='/',
            redirect_field_name=None
        )(view_func)
    )
    return decorated_view_func

# Admin Dashboard
@admin_required
def admin_dashboard(request):
    # Get statistics
    total_users = len(User.nodes.all())
    active_users = len(User.nodes.filter(is_active=True))
    admin_users = len(User.nodes.filter(is_admin=True))
    
    # Get recent users
    recent_users = User.nodes.order_by('-date_joined')[:10]
    
    # Get movie statistics from existing database
    query = """
    MATCH (m:Movie)
    RETURN 
        count(m) as total_movies,
        avg(toFloat(m.vote_average)) as avg_rating,
        sum(toInteger(m.vote_count)) as total_votes
    """
    
    with get_session() as session:
        result = session.run(query)
        stats = result.single()
    
    context = {
        'total_users': total_users,
        'active_users': active_users,
        'admin_users': admin_users,
        'recent_users': recent_users,
        'total_movies': stats['total_movies'] if stats else 0,
        'avg_rating': round(stats['avg_rating'], 2) if stats and stats['avg_rating'] else 0,
        'total_votes': stats['total_votes'] if stats else 0,
    }
    
    return render(request, 'admin/dashboard.html', context)

# Manage Users
@admin_required
def manage_users(request):
    users = User.nodes.all()
    return render(request, 'admin/manage_users.html', {'users': users})

# User Details
@admin_required
def user_details(request, user_id):
    try:
        user = User.nodes.get(uid=user_id)
        
        # Get user's favorite movies details
        favorites = []
        if user.favorite_movies:
            query = """
            MATCH (m:Movie)
            WHERE m.id IN $movie_ids
            RETURN m.id AS id, m.original_title AS title, m.vote_average AS rating
            LIMIT 10
            """
            
            with get_session() as session:
                result = session.run(query, movie_ids=[int(mid) for mid in user.favorite_movies[:10]])
                favorites = [dict(record) for record in result]
        
        context = {
            'user': user,
            'favorites': favorites,
            'favorites_count': len(user.favorite_movies),
            'watchlist_count': len(user.watchlist),
            'watched_count': len(user.watched_movies),
        }
        
        return render(request, 'admin/user_details.html', context)
        
    except User.DoesNotExist:
        messages.error(request, "Utilisateur non trouvé")
        return redirect('manage_users')

# Toggle User Status
@admin_required
def toggle_user_status(request, user_id):
    try:
        user = User.nodes.get(uid=user_id)
        
        # Prevent deactivating self
        if user.uid == request.user.uid:
            messages.error(request, "Vous ne pouvez pas désactiver votre propre compte")
        else:
            user.is_active = not user.is_active
            user.save()
            
            status = "activé" if user.is_active else "désactivé"
            messages.success(request, f"Utilisateur {user.username} {status}")
    
    except User.DoesNotExist:
        messages.error(request, "Utilisateur non trouvé")
    
    return redirect('manage_users')

# Make Admin
@admin_required
def make_admin(request, user_id):
    try:
        user = User.nodes.get(uid=user_id)
        user.is_admin = True
        user.save()
        messages.success(request, f"{user.username} est maintenant administrateur")
    except User.DoesNotExist:
        messages.error(request, "Utilisateur non trouvé")
    
    return redirect('manage_users')

# Remove Admin
@admin_required
def remove_admin(request, user_id):
    try:
        user = User.nodes.get(uid=user_id)
        
        # Prevent removing last admin
        admins = User.nodes.filter(is_admin=True)
        if len(admins) <= 1:
            messages.error(request, "Impossible de retirer le dernier administrateur")
        else:
            user.is_admin = False
            user.save()
            messages.success(request, f"{user.username} n'est plus administrateur")
    except User.DoesNotExist:
        messages.error(request, "Utilisateur non trouvé")
    
    return redirect('manage_users')