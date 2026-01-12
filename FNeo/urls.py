# your_project/urls.py (in your project folder, same level as settings.py)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
import neo4j_api.api_views as api_views
import film_app.views as views
from neo4j_api.api_views import *
from film_app.views import HomeView, MoviesListView, MovieDetailView
from film_app.admin_views import (
    admin_dashboard,
    manage_users,
    user_details,
    toggle_user_status,
    make_admin,
    remove_admin
)
from film_app.auth_views import register_view, login_view, logout_view, profile_view, update_profile_view




urlpatterns = [
    path('api/', include('neo4j_api.urls')),  # API endpoints



    # Authentication URLs
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('profile/', profile_view, name='profile'),
    path('profile/update/', update_profile_view, name='update_profile'),
    
    # Admin URLs
    path('admin/dashboard/', admin_dashboard, name='admin_dashboard'),
    path('admin/users/', manage_users, name='manage_users'),
    path('admin/users/<str:user_id>/', user_details, name='user_details'),
    path('admin/users/<str:user_id>/toggle/', toggle_user_status, name='toggle_user_status'),
    path('admin/users/<str:user_id>/make-admin/', make_admin, name='make_admin'),
    path('admin/users/<str:user_id>/remove-admin/', remove_admin, name='remove_admin'),

     # ==================== PAGES PUBLIQUES ====================
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    
   
    # ==================== FAVORIS (pour tous les utilisateurs) ====================
    path('favorites/', views.favorites_page, name='favorites'),
    path('api/favorites/toggle/', views.toggle_favorite, name='toggle_favorite'),
    path('api/favorites/', views.get_favorites, name='get_favorites'),
    path('api/watchlist/toggle/', views.toggle_watchlist, name='toggle_watchlist'),
    path('api/watchlist/', views.watchlist_page, name='watchlist'),
    # ==================== DASHBOARD UTILISATEUR ====================
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    
   
    
    # ==================== PAGES FILMS ====================
    path('movies/', MoviesListView.as_view(), name='movies_list'),  # Add this line
    path('movie/<int:movie_id>/', MovieDetailView.as_view(), name='movie_detail'),
    
      
    # ==================== API ENDPOINTS ====================
    path('api/check-favorite/<str:movie_id>/', views.check_favorite, name='check_favorite'),
    path('api/user-stats/', views.get_user_stats, name='get_user_stats'),

    path('neo4j/', include('neo4j_api.urls')),
    

 # HTML views
    path('', HomeView.as_view(), name='home'),
    path('movie/<int:movie_id>/', MovieDetailView.as_view(), name='movie_detail'),
    

 
    
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

