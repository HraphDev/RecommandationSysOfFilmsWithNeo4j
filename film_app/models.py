# film_app/models.py
import uuid
import json
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from .neo4j_driver import get_session


class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        if not username:
            raise ValueError("Username is required")

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_admin", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser):
    # ----------------- Core Fields -----------------
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128, default="")
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    profile_picture = models.CharField(max_length=255, default="default.jpg")

    # ----------------- Permissions -----------------
    is_admin = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # ----------------- Dates -----------------
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)

    # ----------------- User Data -----------------
    favorite_movies = models.JSONField(default=list)
    watchlist = models.JSONField(default=list)
    watched_movies = models.JSONField(default=list)

    # ----------------- Neo4j -----------------
    neo4j_id = models.CharField(max_length=100, blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return self.username

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}" if self.first_name and self.last_name else self.username

    def get_short_name(self):
        return self.first_name or self.username

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return self.is_admin

    @property
    def is_staff(self):
        return self.is_admin

    # ==================== NEO4J SYNC ====================
    def create_in_neo4j(self):
        query = """
        CREATE (u:User {
            id: $user_id,
            username: $username,
            email: $email,
            first_name: $first_name,
            last_name: $last_name,
            is_admin: $is_admin,
            is_active: $is_active,
            date_joined: $date_joined,
            favorite_movies: $favorite_movies,
            watchlist: $watchlist,
            watched_movies: $watched_movies
        })
        RETURN elementId(u) AS neo4j_id
        """
        try:
            with get_session() as session:
                result = session.run(
                    query,
                    user_id=str(self.id),
                    username=self.username,
                    email=self.email,
                    first_name=self.first_name or "",
                    last_name=self.last_name or "",
                    is_admin=self.is_admin,
                    is_active=self.is_active,
                    date_joined=self.date_joined.isoformat() if self.date_joined else "",
                    favorite_movies=json.dumps(self.favorite_movies or []),
                    watchlist=json.dumps(self.watchlist or []),
                    watched_movies=json.dumps(self.watched_movies or []),
                )
                record = result.single()
                if record:
                    self.neo4j_id = record["neo4j_id"]
                    self.save(update_fields=["neo4j_id"])
                    return True
        except Exception as e:
            print(f"Error creating user in Neo4j: {e}")
        return False

    def update_in_neo4j(self):
        if not self.neo4j_id:
            return False

        query = """
        MATCH (u:User)
        WHERE elementId(u) = $neo4j_id
        SET u.username = $username,
            u.email = $email,
            u.first_name = $first_name,
            u.last_name = $last_name,
            u.is_admin = $is_admin,
            u.is_active = $is_active,
            u.favorite_movies = $favorite_movies,
            u.watchlist = $watchlist,
            u.watched_movies = $watched_movies
        RETURN u
        """
        try:
            with get_session() as session:
                session.run(
                    query,
                    neo4j_id=self.neo4j_id,
                    username=self.username,
                    email=self.email,
                    first_name=self.first_name or "",
                    last_name=self.last_name or "",
                    is_admin=self.is_admin,
                    is_active=self.is_active,
                    favorite_movies=json.dumps(self.favorite_movies or []),
                    watchlist=json.dumps(self.watchlist or []),
                    watched_movies=json.dumps(self.watched_movies or []),
                )
                return True
        except Exception as e:
            print(f"Error updating user in Neo4j: {e}")
        return False

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            self.create_in_neo4j()
        else:
            self.update_in_neo4j()

    # ==================== FAVORITES ====================
    def add_favorite(self, movie_id):
        movie_id_str = str(movie_id)
        if movie_id_str not in self.favorite_movies:
            self.favorite_movies.append(movie_id_str)
            self.save()
            return True
        return False

    def remove_favorite(self, movie_id):
        movie_id_str = str(movie_id)
        if movie_id_str in self.favorite_movies:
            self.favorite_movies.remove(movie_id_str)
            self.save()
            return True
        return False

    def toggle_favorite(self, movie_id):
        return self.remove_favorite(movie_id) if self.is_favorite(movie_id) else self.add_favorite(movie_id)

    def is_favorite(self, movie_id):
        return str(movie_id) in self.favorite_movies

    def get_favorite_movies(self):
        if not self.favorite_movies:
            return []
        query = """
        MATCH (m:Movie)
        WHERE m.id IN $movie_ids
        RETURN m.id AS id, m.original_title AS title, m.vote_average AS rating, m.poster_path AS poster_path
        ORDER BY m.popularity DESC
        """
        try:
            movie_ids = [int(mid) for mid in self.favorite_movies if mid.isdigit()]
            with get_session() as session:
                result = session.run(query, movie_ids=movie_ids)
                return [
                    {
                        "id": record["id"],
                        "title": record["title"],
                        "rating": round(float(record["rating"] or 0), 1),
                        "poster_url": f"https://image.tmdb.org/t/p/w500{record['poster_path']}" if record["poster_path"] else "",
                    }
                    for record in result
                ]
        except Exception as e:
            print(f"Error getting favorite movies: {e}")
            return []

    def get_favorites_count(self):
        return len(self.favorite_movies)

    # ==================== WATCHLIST ====================
    def add_to_watchlist(self, movie_id):
        movie_id_str = str(movie_id)
        if movie_id_str not in self.watchlist:
            self.watchlist.append(movie_id_str)
            self.save()
            return True
        return False

    def remove_from_watchlist(self, movie_id):
        movie_id_str = str(movie_id)
        if movie_id_str in self.watchlist:
            self.watchlist.remove(movie_id_str)
            self.save()
            return True
        return False

    def toggle_watchlist(self, movie_id):
        return self.remove_from_watchlist(movie_id) if self.is_in_watchlist(movie_id) else self.add_to_watchlist(movie_id)

    def is_in_watchlist(self, movie_id):
        return str(movie_id) in self.watchlist

    def get_watchlist_movies(self):
        if not self.watchlist:
            return []
        query = """
        MATCH (m:Movie)
        WHERE m.id IN $movie_ids
        RETURN m.id AS id, m.original_title AS title, m.vote_average AS rating, m.poster_path AS poster_path
        ORDER BY m.popularity DESC
        """
        try:
            movie_ids = [int(mid) for mid in self.watchlist if mid.isdigit()]
            with get_session() as session:
                result = session.run(query, movie_ids=movie_ids)
                return [
                    {
                        "id": record["id"],
                        "title": record["title"],
                        "rating": round(float(record["rating"] or 0), 1),
                        "poster_url": f"https://image.tmdb.org/t/p/w500{record['poster_path']}" if record["poster_path"] else "",
                    }
                    for record in result
                ]
        except Exception as e:
            print(f"Error getting watchlist movies: {e}")
            return []

    def get_watchlist_count(self):
        return len(self.watchlist)

    # ==================== RECOMMENDATIONS ====================
    def get_recommendations(self, limit=10):
        """
        Retourne des films recommandés basés sur les genres des films favoris de l'utilisateur.
        Version adaptée à votre structure de base de données Neo4j.
        """
        print(f"DEBUG get_recommendations: User has {len(self.favorite_movies)} favorites")
        
        if not self.favorite_movies or len(self.favorite_movies) == 0:
            print("DEBUG: No favorites, returning popular movies")
            return self._get_popular_movies(limit)
        
        # Convertir les IDs de favoris
        favorite_ids = []
        for mid in self.favorite_movies:
            try:
                favorite_ids.append(int(mid))
            except ValueError:
                continue
        
        print(f"DEBUG: Favorite IDs: {favorite_ids}")
        
        if not favorite_ids:
            print("DEBUG: No valid favorite IDs")
            return self._get_popular_movies(limit)
        
        # Étape 1: Récupérer les noms de genres des films favoris
        favorite_genre_names = set()
        
        try:
            # Récupérer les genres de tous les films favoris
            query_fav_genres = """
            MATCH (m:Movie)
            WHERE m.id IN $favorite_ids
              AND m.genres IS NOT NULL
              AND m.genres <> '[]'
            RETURN m.genres AS genres_string
            """
            
            with get_session() as session:
                result = session.run(query_fav_genres, favorite_ids=favorite_ids)
                for record in result:
                    genres_string = record["genres_string"]
                    if genres_string:
                        try:
                            # Nettoyer et parser la chaîne JSON
                            cleaned = genres_string.replace("'", '"')
                            genres_list = json.loads(cleaned)
                            if isinstance(genres_list, list):
                                for genre in genres_list:
                                    if isinstance(genre, dict) and 'name' in genre:
                                        favorite_genre_names.add(genre['name'].strip().lower())
                        except Exception as e:
                            print(f"Error parsing genres: {e}, string: {genres_string}")
                            continue
            
            print(f"DEBUG: Favorite genre names found: {list(favorite_genre_names)}")
            
            if not favorite_genre_names:
                print("DEBUG: No genres found in favorites, returning popular movies excluding favorites")
                return self._get_popular_movies_excluding(limit, favorite_ids)
            
            # Étape 2: Chercher des films avec les mêmes genres
            # Construire une condition LIKE pour chaque genre
            recommendations = []
            seen_ids = set(favorite_ids)
            
            # Pour chaque genre, chercher des films
            for genre_name in favorite_genre_names:
                if len(recommendations) >= limit:
                    break
                    
                query_recommendations = """
                MATCH (m:Movie)
                WHERE NOT m.id IN $favorite_ids
                  AND m.poster_path IS NOT NULL 
                  AND m.poster_path <> ''
                  AND m.genres IS NOT NULL
                  AND m.genres <> '[]'
                  AND toLower(m.genres) CONTAINS $genre_name
                RETURN DISTINCT m.id AS id,
                               m.original_title AS title,
                               COALESCE(m.vote_average, 0) AS rating,
                               m.poster_path AS poster_path,
                               m.genres AS genres_string,
                               COALESCE(m.popularity, 0) AS popularity
                ORDER BY m.popularity DESC
                LIMIT $sublimit
                """
                
                sublimit = min(limit - len(recommendations), 5)  # Prendre quelques films par genre
                
                try:
                    result = session.run(query_recommendations, 
                                        favorite_ids=favorite_ids,
                                        genre_name=genre_name.lower(),
                                        sublimit=sublimit)
                    
                    for record in result:
                        movie_id = record["id"]
                        if movie_id not in seen_ids:
                            seen_ids.add(movie_id)
                            
                            # Formater le film
                            movie = self._format_movie_record(record)
                            if movie:
                                recommendations.append(movie)
                                
                                if len(recommendations) >= limit:
                                    break
                except Exception as e:
                    print(f"Error searching for genre {genre_name}: {e}")
                    continue
            
            print(f"DEBUG: Found {len(recommendations)} recommendations by genre")
            
            # Si pas assez de recommandations, compléter avec des films populaires
            if len(recommendations) < limit:
                print(f"DEBUG: Adding {limit - len(recommendations)} popular movies")
                additional = self._get_popular_movies_excluding(limit - len(recommendations), list(seen_ids))
                recommendations.extend(additional)
            
            # Trier par popularité
            recommendations.sort(key=lambda x: x.get('popularity', 0), reverse=True)
            
            print(f"DEBUG: Returning {len(recommendations)} recommendations")
            return recommendations[:limit]
            
        except Exception as e:
            print(f"ERROR in get_recommendations: {e}")
            import traceback
            traceback.print_exc()
            return self._get_popular_movies(limit)

    def _format_movie_record(self, record):
        """Formate un enregistrement de film depuis Neo4j"""
        try:
            poster_url = f"https://image.tmdb.org/t/p/w500{record['poster_path']}" if record.get('poster_path') else ""
            
            # Extraire le premier genre
            genre_name = "Movie"
            genres_string = record.get("genres_string", "")
            if genres_string and genres_string != '[]':
                try:
                    cleaned = genres_string.replace("'", '"')
                    genres_list = json.loads(cleaned)
                    if isinstance(genres_list, list) and len(genres_list) > 0:
                        if isinstance(genres_list[0], dict) and 'name' in genres_list[0]:
                            genre_name = genres_list[0]['name']
                except:
                    pass
            
            return {
                "id": record["id"],
                "title": record.get("title", "Unknown"),
                "rating": round(float(record.get("rating", 0) or 0), 1),
                "poster_url": poster_url,
                "genre": genre_name,
                "popularity": float(record.get("popularity", 0) or 0)
            }
        except Exception as e:
            print(f"Error formatting movie record: {e}")
            return None

    def _get_popular_movies(self, limit):
        """Récupère les films populaires"""
        query = """
        MATCH (m:Movie)
        WHERE m.poster_path IS NOT NULL 
          AND m.poster_path <> ''
          AND m.genres IS NOT NULL
        RETURN m.id AS id,
               m.original_title AS title,
               COALESCE(m.vote_average, 0) AS rating,
               m.poster_path AS poster_path,
               m.genres AS genres_string,
               COALESCE(m.popularity, 0) AS popularity
        ORDER BY COALESCE(m.popularity, 0) DESC
        LIMIT $limit
        """
        
        try:
            with get_session() as session:
                result = session.run(query, limit=limit)
                movies = []
                for record in result:
                    movie = self._format_movie_record(record)
                    if movie:
                        movies.append(movie)
                return movies
        except Exception as e:
            print(f"ERROR in _get_popular_movies: {e}")
            return []

    def _get_popular_movies_excluding(self, limit, exclude_ids):
        """Récupère les films populaires en excluant certains IDs"""
        query = """
        MATCH (m:Movie)
        WHERE NOT m.id IN $exclude_ids
          AND m.poster_path IS NOT NULL 
          AND m.poster_path <> ''
          AND m.genres IS NOT NULL
        RETURN m.id AS id,
               m.original_title AS title,
               COALESCE(m.vote_average, 0) AS rating,
               m.poster_path AS poster_path,
               m.genres AS genres_string,
               COALESCE(m.popularity, 0) AS popularity
        ORDER BY COALESCE(m.popularity, 0) DESC
        LIMIT $limit
        """
        
        try:
            with get_session() as session:
                result = session.run(query, exclude_ids=exclude_ids, limit=limit)
                movies = []
                for record in result:
                    movie = self._format_movie_record(record)
                    if movie:
                        movies.append(movie)
                return movies
        except Exception as e:
            print(f"ERROR in _get_popular_movies_excluding: {e}")
            return []