# neo4j_api/urls.py
from django.urls import path
from . import api_views

urlpatterns = [
    # Movie endpoints
    path('movies/<int:movie_id>/', api_views.get_movie_short_by_id, name='movie_short'),
    path('movies/<int:movie_id>/full/', api_views.get_movie_full_by_id, name='movie_full'),
    path('movies/<int:movie_id>/links/', api_views.get_movie_links, name='movie_links'),
    path('movies/<int:movie_id>/keywords/', api_views.get_movie_keywords, name='movie_keywords'),
    path('movies/<int:movie_id>/credits/', api_views.get_movie_credits, name='movie_credits'),
    path('movies/<int:movie_id>/similar/', api_views.get_similar_movies, name='similar_movies'),
    
    # Rating endpoints
    path('ratings/<int:movie_id>/user/<int:user_id>/', api_views.get_user_rating, name='user_rating'),
    path('ratings/<int:movie_id>/user/<int:user_id>/add/', api_views.add_user_rating, name='add_rating'),

    # Search and discovery
    path('movies/search/', api_views.search_movies, name='search_movies'),
    path('movies/popular/', api_views.get_popular_movies, name='popular_movies'),
    path('movies/top-rated/', api_views.get_top_rated_movies, name='top_rated_movies'),
]