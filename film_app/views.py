# film_app/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json
from .models import User
from .backends import Neo4jAuthBackend
from .neo4j_driver import get_session
from django.http import HttpResponse
from django.views.generic import TemplateView
import ast
import re

def parse_genres_string(genres_string):
    """Parse la chaîne JSON des genres et retourne une liste de noms de genres"""
    if not genres_string or genres_string == '[]' or genres_string == '':
        return []
    
    try:
        # Essayer de parser comme JSON (remplacer les simples quotes par doubles)
        cleaned = genres_string.replace("'", '"')
        genres_list = json.loads(cleaned)
        
        if isinstance(genres_list, list):
            return [g.get('name', str(g)) for g in genres_list if isinstance(g, dict) and 'name' in g]
        elif isinstance(genres_list, dict):
            return [genres_list.get('name', '')] if 'name' in genres_list else []
        return []
    except json.JSONDecodeError:
        # Essayer avec ast.literal_eval pour les strings Python-like
        try:
            genres_list = ast.literal_eval(genres_string)
            if isinstance(genres_list, list):
                return [g.get('name', str(g)) for g in genres_list if isinstance(g, dict) and 'name' in g]
            return []
        except:
            # Si tout échoue, essayer d'extraire avec regex
            pattern = r"'name':\s*'([^']+)'"
            matches = re.findall(pattern, genres_string)
            return matches if matches else []
    except Exception:
        return []

# ==================== TEMPLATE VIEWS FOR HTML PAGES ====================

class HomeView(TemplateView):
    template_name = 'home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Query to get popular movies
        query = """
        MATCH (m:Movie)
        WHERE m.poster_path IS NOT NULL AND m.poster_path <> ''
        RETURN m.id AS id, 
               m.original_title AS title,
               m.vote_average AS rating,
               m.vote_count AS vote_count,
               m.release_date AS release_date,
               m.poster_path AS poster_path,
               m.genres AS genres_string
        ORDER BY m.popularity DESC
        LIMIT 12
        """
        
        with get_session() as session:
            result = session.run(query)
            popular_movies = []
            for record in result:
                # Parse les genres
                genres = parse_genres_string(record.get("genres_string", ""))
                genre = "Movie" if not genres else genres[0]
                
                # Build the poster URL
                poster_url = f"https://image.tmdb.org/t/p/w500{record['poster_path']}" if record["poster_path"] else ""
                
                # Extract year from release_date
                year = ""
                if record["release_date"]:
                    try:
                        year = str(record["release_date"]).split("-")[0]
                    except:
                        pass
                
                popular_movies.append({
                    "id": record["id"],
                    "title": record["title"],
                    "rating": round(float(record["rating"] or 0), 1),
                    "vote_count": record["vote_count"],
                    "year": year,
                    "genre": genre,
                    "poster_url": poster_url,
                    "views": record["vote_count"] or 0
                })
        
        context['popular_movies'] = popular_movies
        return context
    
class MoviesListView(TemplateView):
    template_name = 'movies.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get optional query parameters
        search_query = self.request.GET.get('search', '')
        genre_filter = self.request.GET.get('genre', '')
        page = int(self.request.GET.get('page', 1))
        per_page = 20
        offset = (page - 1) * per_page
        
        # Build the WHERE conditions dynamically
        where_conditions = []
        query_params = {}
        
        if search_query:
            where_conditions.append("toLower(m.original_title) CONTAINS toLower($search_query)")
            query_params['search_query'] = search_query
            
        if genre_filter:
            # Pour filtrer par genre, on cherche la chaîne dans le JSON
            where_conditions.append("m.genres CONTAINS $genre_filter_name")
            query_params['genre_filter_name'] = f"'name': '{genre_filter}'"
        
        # Build WHERE clause
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # Get total count query
        count_query = f"""
        MATCH (m:Movie)
        {where_clause}
        RETURN count(m) AS total_count
        """
        
        # Get movies with pagination query
        movies_query = f"""
        MATCH (m:Movie)
        {where_clause}
        RETURN m.id AS id, 
               m.original_title AS title,
               m.vote_average AS rating,
               m.release_date AS release_date,
               m.poster_path AS poster_path,
               m.genres AS genres_string,
               m.overview AS overview
        ORDER BY m.popularity DESC
        SKIP $offset
        LIMIT $limit
        """
        
        query_params['offset'] = offset
        query_params['limit'] = per_page
        
        with get_session() as session:
            # Get total count
            try:
                total_result = session.run(count_query, query_params)
                total_count = total_result.single()["total_count"]
            except Exception as e:
                print(f"Error in count query: {e}")
                total_count = 0
            
            # Get movies
            movies = []
            if total_count > 0:
                try:
                    result = session.run(movies_query, query_params)
                    
                    for record in result:
                        # Parse les genres
                        genres = parse_genres_string(record.get("genres_string", ""))
                        
                        # Build the poster URL
                        poster_url = ""
                        if record["poster_path"]:
                            poster_url = f"https://image.tmdb.org/t/p/w500{record['poster_path']}"
                        
                        # Extract year from release_date
                        year = ""
                        if record["release_date"]:
                            try:
                                year = str(record["release_date"]).split("-")[0]
                            except:
                                pass
                        
                        movies.append({
                            "id": record["id"],
                            "title": record["title"],
                            "rating": round(float(record["rating"] or 0), 1),
                            "year": year,
                            "genres": genres,
                            "poster_url": poster_url,
                            "overview": record["overview"] or ""
                        })
                except Exception as e:
                    print(f"Error in movies query: {e}")
                    movies = []
        
        # Get all unique genres for filter dropdown
        genre_query = """
        MATCH (m:Movie)
        WHERE m.genres IS NOT NULL AND m.genres <> '[]'
        RETURN m.genres AS genres_string
        """
        
        with get_session() as session:
            try:
                genre_result = session.run(genre_query)
                all_genres_set = set()
                
                for record in genre_result:
                    genres = parse_genres_string(record.get("genres_string", ""))
                    for genre in genres:
                        if genre:
                            all_genres_set.add(genre)
                
                all_genres = sorted(list(all_genres_set))
            except Exception as e:
                print(f"Error in genre query: {e}")
                all_genres = []
        
        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
        
        # Create page range for pagination
        page_range = []
        start_page = max(1, page - 2)
        end_page = min(total_pages, page + 2)
        for i in range(start_page, end_page + 1):
            page_range.append(i)
        
        context.update({
            'movies': movies,
            'all_genres': all_genres,
            'current_page': page,
            'total_pages': total_pages,
            'search_query': search_query,
            'selected_genre': genre_filter,
            'has_previous': page > 1,
            'has_next': page < total_pages,
            'page_range': page_range,
            'total_count': total_count,
        })
        return context

class MovieDetailView(TemplateView):
    template_name = 'movie_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        movie_id = self.kwargs.get('movie_id')
        
        # Query pour les détails du film
        movie_query = """
        MATCH (m:Movie)
        WHERE toInteger(m.id) = $movie_id
        RETURN m.id AS id, 
               m.original_title AS title,
               m.vote_average AS rating,
               m.vote_count AS vote_count,
               m.release_date AS release_date,
               m.poster_path AS poster_path,
               m.genres AS genres_string,
               m.overview AS overview,
               m.runtime AS runtime,
               m.budget AS budget,
               m.revenue AS revenue,
               m.original_language AS original_language,
               m.popularity AS popularity,
               m.adult AS adult,
               m.imdb_id AS imdb_id,
               m.tagline AS tagline
        """
        
        # Query pour les films similaires (basé sur les genres)
        similar_query = """
        MATCH (m:Movie {id: $movie_id})
        WITH m, m.genres AS movie_genres
        MATCH (similar:Movie)
        WHERE similar.id <> $movie_id
          AND similar.poster_path IS NOT NULL 
          AND similar.poster_path <> ''
          AND similar.genres CONTAINS movie_genres
        RETURN similar.id AS id, 
               similar.original_title AS title,
               similar.vote_average AS rating,
               similar.poster_path AS poster_path,
               similar.release_date AS release_date
        ORDER BY similar.popularity DESC
        LIMIT 6
        """
        
        with get_session() as session:
            # Get movie details
            movie_result = session.run(movie_query, movie_id=movie_id).single()
            
            if not movie_result:
                context['movie'] = None
                return context
            
            # Process movie data
            movie_data = {
                'id': movie_result["id"],
                'title': movie_result["title"],
                'rating': round(float(movie_result["rating"] or 0), 1),
                'vote_count': movie_result["vote_count"] or 0,
                'release_date': movie_result["release_date"],
                'poster_path': movie_result["poster_path"],
                'overview': movie_result["overview"] or "Pas de description disponible.",
                'runtime': movie_result["runtime"] or 0,
                'budget': movie_result["budget"] or 0,
                'revenue': movie_result["revenue"] or 0,
                'original_language': movie_result["original_language"] or "en",
                'popularity': round(float(movie_result["popularity"] or 0), 2),
                'adult': movie_result["adult"] or False,
                'tagline': movie_result.get("tagline", "") or "",
                'imdb_id': movie_result.get("imdb_id", "")
            }
            
            # Parse genres
            movie_data['genres'] = parse_genres_string(movie_result.get("genres_string", ""))
            
            # Get poster URL
            if movie_result["poster_path"]:
                movie_data['poster_url'] = f"https://image.tmdb.org/t/p/w500{movie_result['poster_path']}"
            else:
                movie_data['poster_url'] = ""
            
            # Get year
            if movie_result["release_date"]:
                try:
                    movie_data['year'] = str(movie_result["release_date"]).split("-")[0]
                except:
                    movie_data['year'] = ''
            else:
                movie_data['year'] = ''
            
            # Create IMDB URL
            if movie_data['imdb_id']:
                # Nettoyer l'ID IMDB
                imdb_id_clean = str(movie_data['imdb_id']).replace('tt', '').zfill(7)
                movie_data['imdb_url'] = f"https://www.imdb.com/title/tt{imdb_id_clean}"
            else:
                movie_data['imdb_url'] = None
            
            # Get similar movies
            similar_result = session.run(similar_query, movie_id=movie_id)
            similar_movies = []
            for record in similar_result:
                poster_url = ""
                if record["poster_path"]:
                    poster_url = f"https://image.tmdb.org/t/p/w300{record['poster_path']}"
                
                year = ""
                if record["release_date"]:
                    try:
                        year = str(record["release_date"]).split("-")[0]
                    except:
                        pass
                
                similar_movies.append({
                    'id': record["id"],
                    'title': record["title"],
                    'rating': round(float(record["rating"] or 0), 1),
                    'poster_url': poster_url,
                    'year': year
                })
        
        # Si pas assez de films similaires, ajouter des films populaires
        if len(similar_movies) < 4:
            backup_query = """
            MATCH (m:Movie)
            WHERE m.id <> $movie_id 
              AND m.poster_path IS NOT NULL 
              AND m.poster_path <> ''
            RETURN m.id AS id, 
                   m.original_title AS title,
                   m.vote_average AS rating,
                   m.poster_path AS poster_path,
                   m.release_date AS release_date
            ORDER BY m.popularity DESC
            LIMIT 6
            """
            
            with get_session() as session:
                backup_result = session.run(backup_query, movie_id=movie_id)
                backup_movies = []
                for record in backup_result:
                    poster_url = ""
                    if record["poster_path"]:
                        poster_url = f"https://image.tmdb.org/t/p/w300{record['poster_path']}"
                    
                    year = ""
                    if record["release_date"]:
                        try:
                            year = str(record["release_date"]).split("-")[0]
                        except:
                            pass
                    
                    backup_movies.append({
                        'id': record["id"],
                        'title': record["title"],
                        'rating': round(float(record["rating"] or 0), 1),
                        'poster_url': poster_url,
                        'year': year
                    })
                
                # Combiner les films (sans doublons)
                existing_ids = {m['id'] for m in similar_movies}
                for movie in backup_movies:
                    if movie['id'] not in existing_ids and len(similar_movies) < 6:
                        similar_movies.append(movie)
        
        # Add everything to context
        context['movie'] = movie_data
        context['similar_movies'] = similar_movies[:6]
        
        # Pour le cast et crew, vous pouvez les laisser optionnels pour l'instant
        context['cast'] = []
        context['crew'] = {'directors': [], 'writers': []}
        context['keywords'] = []
        
        return context


def about_view(request):
    """Page À propos"""
    return render(request, 'about.html')


def contact_view(request):
    """Page Contact"""
    return render(request, 'contact.html')


# ==================== AUTHENTIFICATION ====================

def register_view(request):
    """Inscription d'un nouvel utilisateur"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        # FIXED: Utiliser first_name et last_name au lieu de nom et prenom
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        
        # Validation
        errors = []
        
        if not username:
            errors.append("Le nom d'utilisateur est requis")
        elif len(username) < 3:
            errors.append("Le nom d'utilisateur doit contenir au moins 3 caractères")
        
        if not email:
            errors.append("L'email est requis")
        elif '@' not in email:
            errors.append("Email invalide")
        
        if not password:
            errors.append("Le mot de passe est requis")
        elif len(password) < 6:
            errors.append("Le mot de passe doit contenir au moins 6 caractères")
        
        if password != confirm_password:
            errors.append("Les mots de passe ne correspondent pas")
        
        # Vérifier si l'utilisateur existe déjà
        try:
            if User.objects.filter(username=username).exists():
                errors.append("Ce nom d'utilisateur est déjà pris")
            if User.objects.filter(email=email).exists():
                errors.append("Cet email est déjà utilisé")
        except Exception as e:
            print(f"Erreur lors de la vérification: {e}")
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'auth/register.html', {
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
            })
        
        # Créer l'utilisateur
        try:
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            user.set_password(password)
            user.save()
            
            # Auto-login après inscription
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


def login_view(request):
    """Connexion d'un utilisateur"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username_or_email = request.POST.get('username_or_email', '').strip()
        password = request.POST.get('password', '').strip()
        remember_me = request.POST.get('remember_me') == 'on'
        
        if not username_or_email or not password:
            messages.error(request, "Veuillez remplir tous les champs")
            return render(request, 'auth/login.html')
        
        # Authentifier l'utilisateur
        backend = Neo4jAuthBackend()
        
        # Déterminer si c'est un email ou un username
        if '@' in username_or_email:
            user = backend.authenticate(request, email=username_or_email, password=password)
        else:
            user = backend.authenticate(request, username=username_or_email, password=password)
        
        if user is not None:
            if not user.is_active:
                messages.error(request, "Ce compte est désactivé")
                return render(request, 'auth/login.html')
            
            # Connecter l'utilisateur
            auth_login(request, user, backend='film_app.backends.Neo4jAuthBackend')
            
            # Mettre à jour last_login
            user.last_login = timezone.now()
            user.save()
            
            # Gérer "Remember me"
            if not remember_me:
                request.session.set_expiry(0)  # Session navigateur
            
            # Redirection basée sur le rôle
            messages.success(request, f"Bienvenue {user.get_full_name()}!")
            
            if user.is_admin:
                return redirect('admin_dashboard')
            else:
                return redirect('home')
        else:
            messages.error(request, "Nom d'utilisateur/email ou mot de passe incorrect")
    
    return render(request, 'auth/login.html')


def logout_view(request):
    """Déconnexion"""
    auth_logout(request)
    messages.success(request, "Vous avez été déconnecté avec succès.")
    return redirect('home')


# ==================== PROFIL UTILISATEUR ====================

@login_required
def profile_view(request):
    """Afficher le profil de l'utilisateur"""
    user = request.user
    return render(request, 'auth/profile.html', {'user': user})


@login_required
def update_profile(request):
    """Mettre à jour le profil utilisateur"""
    user = request.user
    
    if request.method == 'POST':
        # FIXED: Utiliser first_name et last_name au lieu de nom et prenom
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        new_email = request.POST.get('email', user.email).strip()
        
        # Vérifier si l'email a changé et s'il est disponible
        if new_email != user.email:
            try:
                if User.objects.filter(email=new_email).exclude(id=user.id).exists():
                    messages.error(request, "Cet email est déjà utilisé par un autre compte")
                    return redirect('profile')
                user.email = new_email
            except Exception as e:
                messages.error(request, f"Erreur lors de la vérification de l'email: {str(e)}")
                return redirect('profile')
        
        # Mettre à jour le mot de passe si fourni
        new_password = request.POST.get('new_password', '').strip()
        if new_password:
            confirm_password = request.POST.get('confirm_password', '').strip()
            if new_password == confirm_password:
                if len(new_password) >= 6:
                    user.set_password(new_password)
                    messages.success(request, "Mot de passe mis à jour avec succès")
                else:
                    messages.error(request, "Le mot de passe doit contenir au moins 6 caractères")
            else:
                messages.error(request, "Les mots de passe ne correspondent pas")
        
        # Mettre à jour la photo de profil si téléchargée
        if 'profile_picture' in request.FILES:
            # FIXED: Utiliser profile_picture au lieu de photo
            photo = request.FILES['profile_picture']
            user.profile_picture = f"/media/profile_pics/{photo.name}"
        
        user.save()
        messages.success(request, "Profil mis à jour avec succès")
        return redirect('profile')
    
    return render(request, 'auth/update_profile.html', {'user': user})


# ==================== FAVORIS ====================

@login_required
@csrf_exempt
def toggle_favorite(request):
    """API pour ajouter/retirer un film des favoris"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            film_id = data.get('film_id')
            
            if not film_id:
                return JsonResponse({'error': 'Film ID requis'}, status=400)
            
            user = request.user
            is_favorite = user.toggle_favorite(film_id)
            
            return JsonResponse({
                'success': True,
                'is_favorite': is_favorite,
                'favorites_count': user.get_favorites_count(),
                'message': 'Ajouté aux favoris' if is_favorite else 'Retiré des favoris'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Requête invalide'}, status=400)


@login_required
def get_favorites(request):
    """API pour récupérer les films favoris"""
    user = request.user
    return JsonResponse({
        'success': True,
        'favorites': user.favorite_movies,
        'count': user.get_favorites_count()
    })


@login_required
def favorites_page(request):
    """Page affichant les films favoris de l'utilisateur"""
    user = request.user
    favorite_movies = user.get_favorite_movies()  
    favorites_count = user.get_favorites_count()
    
    # Get recommendations - limit to 10 for display
    recommendations = user.get_recommendations(limit=10)
    
    # DEBUG logging
    print(f"DEBUG - User: {user.username}")
    print(f"DEBUG - Favorite IDs: {user.favorite_movies}")
    print(f"DEBUG - Favorite movies fetched: {len(favorite_movies)}")
    print(f"DEBUG - Recommendations count: {len(recommendations)}")
    
    if recommendations:
        for i, rec in enumerate(recommendations[:3]):
            print(f"DEBUG - Rec {i+1}: {rec['title']} - Genre: {rec.get('genre', 'N/A')}")
    
    return render(request, 'favorites/favorites.html', {
        'user': user,
        'favorite_movies': favorite_movies,
        'favorites_count': favorites_count,
        "recommendations": recommendations
    })

@login_required
def check_favorite(request, movie_id):
    """API pour vérifier si un film est dans les favoris"""
    user = request.user
    is_favorite = user.is_favorite(movie_id)
    
    return JsonResponse({
        'success': True,
        'is_favorite': is_favorite
    })


# ==================== WATCHLIST ====================

@login_required
@csrf_exempt
def toggle_watchlist(request):
    """API pour ajouter/retirer un film de la watchlist"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            movie_id = data.get('movie_id')
            if not movie_id:
                return JsonResponse({'error': 'Movie ID required'}, status=400)
            
            user = request.user
            is_in_watchlist = user.toggle_watchlist(movie_id)
            return JsonResponse({
                'success': True,
                'is_in_watchlist': is_in_watchlist,
                'watchlist_count': len(user.watchlist),
                'message': 'Ajouté à la watchlist' if is_in_watchlist else 'Retiré de la watchlist'
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def watchlist_page(request):
    """Page affichant la watchlist de l'utilisateur"""
    user = request.user
    watchlist_movies = user.get_watchlist_movies()  
    watchlist_count = len(user.watchlist)
    
    return render(request, 'watchlist/watchlist.html', {
        'user': user,
        'watchlist_movies': watchlist_movies,
        'watchlist_count': watchlist_count
    })


# ==================== DASHBOARD UTILISATEUR ====================

@login_required
def user_dashboard(request):
    """Dashboard pour utilisateur normal"""
    user = request.user
    
    # Statistiques de l'utilisateur
    stats = {
        'favorites_count': user.get_favorites_count(),
        'watchlist_count': user.get_watchlist_count(),
        'account_age': (timezone.now() - user.date_joined).days,
        'last_login': user.last_login if user.last_login else 'Jamais'
    }
    
    return render(request, 'dashboard/user.html', {
        'user': user,
        'stats': stats
    })


@login_required
def get_user_stats(request):
    """API pour obtenir les statistiques de l'utilisateur"""
    user = request.user
    
    return JsonResponse({
        'success': True,
        'stats': {
            'favorites_count': user.get_favorites_count(),
            'watchlist_count': user.get_watchlist_count(),
            'account_age_days': (timezone.now() - user.date_joined).days,
            'username': user.username,
            'full_name': user.get_full_name()
        }
    })