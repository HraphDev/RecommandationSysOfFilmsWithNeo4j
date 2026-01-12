# neo4j_api/views.py
from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from film_app.neo4j_driver import get_session
import json

# Helper function for parsing genres
def parse_genres_string(genres_string):
    """Parse genres string to list of names"""
    if not genres_string or genres_string == '[]' or genres_string == '':
        return []
    
    try:
        # Try to parse as JSON
        cleaned = genres_string.replace("'", '"')
        genres_list = json.loads(cleaned)
        
        if isinstance(genres_list, list):
            return [g.get('name', str(g)) for g in genres_list if isinstance(g, dict)]
        elif isinstance(genres_list, dict):
            return [genres_list.get('name', '')] if 'name' in genres_list else []
        return []
    except json.JSONDecodeError:
        # Try with ast.literal_eval for Python-like strings
        try:
            import ast
            genres_list = ast.literal_eval(genres_string)
            if isinstance(genres_list, list):
                return [g.get('name', str(g)) for g in genres_list if isinstance(g, dict)]
            return []
        except:
            return []
    except Exception:
        return []

@api_view(['GET'])
def get_movie_short_by_id(request, movie_id):
    """Get basic movie info by ID"""
    try:
        movie_id = int(movie_id)
    except ValueError:
        return Response({"error": "Invalid movie ID"}, status=status.HTTP_400_BAD_REQUEST)

    query = """
    MATCH (m:Movie)
    WHERE toInteger(m.id) = $movie_id
    RETURN m.id AS id, 
           m.original_title AS title,
           m.vote_average AS rating,
           m.poster_path AS poster_path
    """

    with get_session() as session:
        record = session.run(query, movie_id=movie_id).single()

    if record is None:
        return Response({"error": "Movie not found"}, status=status.HTTP_404_NOT_FOUND)

    poster_url = ""
    if record["poster_path"]:
        poster_url = f"https://image.tmdb.org/t/p/w500{record['poster_path']}"
    
    return Response({
        "id": record["id"],
        "title": record["title"],
        "rating": round(float(record["rating"] or 0), 1),
        "poster_url": poster_url
    })

@api_view(['GET'])
def get_movie_full_by_id(request, movie_id):
    """Get complete movie details by ID"""
    try:
        movie_id = int(movie_id)
    except ValueError:
        return Response({"error": "Invalid movie ID"}, status=status.HTTP_400_BAD_REQUEST)

    query = """
    MATCH (m:Movie)
    WHERE toInteger(m.id) = $movie_id
    RETURN m.id AS id, 
           m.original_title AS title,
           m.adult AS adult,
           m.budget AS budget,
           m.genres AS genres,
           m.original_language AS original_language,
           m.overview AS overview,
           m.popularity AS popularity,
           toString(m.release_date) AS release_date,
           m.revenue AS revenue,
           m.runtime AS runtime,
           m.vote_average AS vote_average,
           m.vote_count AS vote_count,
           m.poster_path AS poster_path,
           m.tagline AS tagline,
           m.homepage AS homepage,
           m.imdb_id AS imdb_id
    """

    with get_session() as session:
        record = session.run(query, movie_id=movie_id).single()

    if record is None:
        return Response({"error": "Movie not found"}, status=status.HTTP_404_NOT_FOUND)

    # Parse genres
    genres = parse_genres_string(record.get("genres", ""))
    
    # Get poster URL
    poster_url = ""
    if record["poster_path"]:
        poster_url = f"https://image.tmdb.org/t/p/w500{record['poster_path']}"
    
    # Get year
    year = ""
    if record["release_date"]:
        try:
            year = str(record["release_date"]).split("-")[0]
        except:
            pass
    
    # Create IMDB URL
    imdb_url = None
    if record.get("imdb_id"):
        imdb_id_clean = str(record["imdb_id"]).replace('tt', '').zfill(7)
        imdb_url = f"https://www.imdb.com/title/tt{imdb_id_clean}"

    return Response({
        "id": record["id"],
        "title": record["title"],
        "adult": record["adult"],
        "budget": record["budget"],
        "genres": genres,
        "original_language": record["original_language"],
        "overview": record["overview"],
        "popularity": round(float(record["popularity"] or 0), 2),
        "release_date": record["release_date"],
        "year": year,
        "revenue": record["revenue"],
        "runtime": record["runtime"],
        "vote_average": round(float(record["vote_average"] or 0), 1),
        "vote_count": record["vote_count"],
        "poster_path": record["poster_path"],
        "poster_url": poster_url,
        "tagline": record.get("tagline", "") or "",
        "homepage": record.get("homepage", "") or "",
        "imdb_id": record.get("imdb_id", "") or "",
        "imdb_url": imdb_url
    })

@api_view(['GET'])
def get_movie_links(request, movie_id):
    """Get IMDB and TMDB links for a movie"""
    try:
        movie_id = int(movie_id)
    except ValueError:
        return Response({"error": "Invalid movie ID"}, status=status.HTTP_400_BAD_REQUEST)

    query = """
    MATCH (m:Link)
    WHERE toInteger(m.movieId) = $movie_id
    RETURN m.imdbId AS imdbId, m.tmdbId AS tmdbId
    """

    with get_session() as session:
        record = session.run(query, movie_id=movie_id).single()

    if record is None:
        return Response({"error": "Links not found"}, status=status.HTTP_404_NOT_FOUND)

    imdb_url = None
    if record["imdbId"]:
        imdb_id_clean = str(record["imdbId"]).replace('tt', '').zfill(7)
        imdb_url = f"https://www.imdb.com/title/tt{imdb_id_clean}"

    tmdb_url = None
    if record["tmdbId"]:
        tmdb_url = f"https://www.themoviedb.org/movie/{record['tmdbId']}"

    return Response({
        "imdb_id": record["imdbId"],
        "tmdb_id": record["tmdbId"],
        "imdb_url": imdb_url,
        "tmdb_url": tmdb_url
    })

@api_view(['GET'])
def get_movie_keywords(request, movie_id):
    """Get keywords for a movie"""
    try:
        movie_id = int(movie_id)
    except ValueError:
        return Response({"error": "Invalid movie ID"}, status=status.HTTP_400_BAD_REQUEST)

    query = """
    MATCH (k:Keyword)
    WHERE toInteger(k.id) = $movie_id
    RETURN k.keywords AS keywords
    """

    with get_session() as session:
        record = session.run(query, movie_id=movie_id).single()

    if record is None:
        return Response({"keywords": []})

    keywords = []
    if record["keywords"]:
        try:
            # Try to parse as JSON
            cleaned = record["keywords"].replace("'", '"')
            keywords_data = json.loads(cleaned)
            
            if isinstance(keywords_data, list):
                keywords = [k.get('name', str(k)) for k in keywords_data if isinstance(k, dict)][:20]  # Limit to 20
        except:
            pass

    return Response({"keywords": keywords})

@api_view(['GET'])
def get_movie_credits(request, movie_id):
    """Get cast and crew for a movie"""
    try:
        movie_id = int(movie_id)
    except ValueError:
        return Response({"error": "Invalid movie ID"}, status=status.HTTP_400_BAD_REQUEST)

    query = """
    MATCH (c:Credit)
    WHERE toInteger(c.id) = $movie_id
    RETURN c.cast AS cast, c.crew AS crew
    """

    with get_session() as session:
        record = session.run(query, movie_id=movie_id).single()

    if record is None:
        return Response({
            "cast": [],
            "crew": [],
            "directors": [],
            "writers": []
        })

    cast = record["cast"] or []
    crew = record["crew"] or []
    
    # Extract directors and writers
    directors = []
    writers = []
    
    for person in crew[:50]:  # Limit to first 50 crew members
        if isinstance(person, dict):
            job = person.get('job', '').lower()
            department = person.get('department', '').lower()
            
            if job == 'director':
                directors.append({
                    'name': person.get('name', ''),
                    'character': person.get('character', ''),
                    'profile_path': f"https://image.tmdb.org/t/p/w200{person.get('profile_path', '')}" if person.get('profile_path') else None
                })
            elif department == 'writing':
                writers.append({
                    'name': person.get('name', ''),
                    'job': person.get('job', ''),
                    'profile_path': f"https://image.tmdb.org/t/p/w200{person.get('profile_path', '')}" if person.get('profile_path') else None
                })
    
    # Format cast with profile images
    formatted_cast = []
    for person in cast[:20]:  # Limit to first 20 cast members
        if isinstance(person, dict):
            formatted_cast.append({
                'name': person.get('name', ''),
                'character': person.get('character', ''),
                'profile_path': f"https://image.tmdb.org/t/p/w200{person.get('profile_path', '')}" if person.get('profile_path') else None
            })

    return Response({
        "cast": formatted_cast,
        "crew": crew[:50],  # Limit to first 50
        "directors": directors[:5],  # Limit to 5 directors
        "writers": writers[:5]  # Limit to 5 writers
    })

@api_view(['GET'])
def get_user_rating(request, movie_id, user_id):
    """Get a user's rating for a movie"""
    try:
        movie_id = int(movie_id)
        user_id = int(user_id)
    except ValueError:
        return Response({"error": "Invalid ID"}, status=status.HTTP_400_BAD_REQUEST)

    query = """
    MATCH (r:Rating)
    WHERE toInteger(r.userId) = $user_id
      AND toInteger(r.movieId) = $movie_id
    RETURN r.userId AS userId,
           r.movieId AS movieId,
           r.rating AS rating,
           r.timestamp AS timestamp
    """

    with get_session() as session:
        record = session.run(query, user_id=user_id, movie_id=movie_id).single()

    if record is None:
        return Response({
            "user_id": user_id,
            "movie_id": movie_id,
            "rating": None,
            "has_rated": False
        })

    return Response({
        "user_id": record["userId"],
        "movie_id": record["movieId"],
        "rating": record["rating"],
        "timestamp": record["timestamp"],
        "has_rated": True
    })

@api_view(['POST'])
def add_user_rating(request, movie_id, user_id):
    """Add or update a user's rating for a movie"""
    try:
        movie_id = int(movie_id)
        user_id = int(user_id)
    except ValueError:
        return Response({"error": "Invalid ID"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        rating = float(request.data.get("rating", 0))
        if rating < 0 or rating > 10:
            return Response({"error": "Rating must be between 0 and 10"}, status=status.HTTP_400_BAD_REQUEST)
    except (TypeError, ValueError):
        return Response({"error": "Invalid rating value"}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if rating exists
    check_query = """
    MATCH (r:Rating)
    WHERE toInteger(r.userId) = $user_id
      AND toInteger(r.movieId) = $movie_id
    RETURN r
    """
    
    with get_session() as session:
        existing = session.run(check_query, user_id=user_id, movie_id=movie_id).single()
        
        if existing:
            # Update existing rating
            update_query = """
            MATCH (r:Rating)
            WHERE toInteger(r.userId) = $user_id
              AND toInteger(r.movieId) = $movie_id
            SET r.rating = $rating,
                r.timestamp = timestamp()
            RETURN r
            """
            result = session.run(update_query, user_id=user_id, movie_id=movie_id, rating=rating)
            action = "updated"
        else:
            # Create new rating
            create_query = """
            CREATE (r:Rating {
                userId: $user_id,
                movieId: $movie_id,
                rating: $rating,
                timestamp: timestamp()
            })
            RETURN r
            """
            result = session.run(create_query, user_id=user_id, movie_id=movie_id, rating=rating)
            action = "added"
    
    return Response({
        "success": True,
        "message": f"Rating {action} successfully",
        "user_id": user_id,
        "movie_id": movie_id,
        "rating": rating
    })

@api_view(['GET'])
def get_similar_movies(request, movie_id):
    """Get movies similar to a given movie"""
    try:
        movie_id = int(movie_id)
    except ValueError:
        return Response({"error": "Invalid movie ID"}, status=status.HTTP_400_BAD_REQUEST)

    query = """
    MATCH (m:Movie)
    WHERE toInteger(m.id) = $movie_id
    UNWIND m.genres AS g

    MATCH (rec:Movie)
    WHERE rec.id <> $movie_id
      AND rec.poster_path IS NOT NULL 
      AND rec.poster_path <> ''
      AND any(x IN rec.genres WHERE x.name = g.name)
    RETURN rec.id AS id, 
           rec.original_title AS title,
           rec.vote_average AS rating,
           rec.poster_path AS poster_path,
           rec.release_date AS release_date,
           rec.overview AS overview
    ORDER BY rec.popularity DESC
    LIMIT 12
    """

    with get_session() as session:
        records = session.run(query, movie_id=movie_id)
        
        similar_movies = []
        for record in records:
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
                'year': year,
                'overview': (record["overview"] or "")[:100] + "..." if record["overview"] else ""
            })
        
        return Response({"similar_movies": similar_movies})

@api_view(['GET'])
def search_movies(request):
    """Search movies by title"""
    query = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 20))
    offset = (page - 1) * limit
    
    if not query:
        return Response({"error": "Search query is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    search_query = """
    MATCH (m:Movie)
    WHERE toLower(m.original_title) CONTAINS toLower($query)
      AND m.poster_path IS NOT NULL 
      AND m.poster_path <> ''
    RETURN m.id AS id, 
           m.original_title AS title,
           m.vote_average AS rating,
           m.poster_path AS poster_path,
           m.release_date AS release_date,
           m.overview AS overview
    ORDER BY m.popularity DESC
    SKIP $offset
    LIMIT $limit
    """
    
    count_query = """
    MATCH (m:Movie)
    WHERE toLower(m.original_title) CONTAINS toLower($query)
    RETURN count(m) AS total_count
    """
    
    with get_session() as session:
        # Get total count
        total_result = session.run(count_query, query=query)
        total_count = total_result.single()["total_count"]
        
        # Get movies
        result = session.run(search_query, query=query, offset=offset, limit=limit)
        
        movies = []
        for record in result:
            poster_url = ""
            if record["poster_path"]:
                poster_url = f"https://image.tmdb.org/t/p/w300{record['poster_path']}"
            
            year = ""
            if record["release_date"]:
                try:
                    year = str(record["release_date"]).split("-")[0]
                except:
                    pass
            
            movies.append({
                'id': record["id"],
                'title': record["title"],
                'rating': round(float(record["rating"] or 0), 1),
                'poster_url': poster_url,
                'year': year,
                'overview': (record["overview"] or "")[:150] + "..." if record["overview"] else ""
            })
        
        total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1
        
        return Response({
            "query": query,
            "page": page,
            "total_pages": total_pages,
            "total_results": total_count,
            "results": movies
        })

@api_view(['GET'])
def get_popular_movies(request):
    """Get popular movies"""
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 20))
    offset = (page - 1) * limit
    
    query = """
    MATCH (m:Movie)
    WHERE m.poster_path IS NOT NULL AND m.poster_path <> ''
    RETURN m.id AS id, 
           m.original_title AS title,
           m.vote_average AS rating,
           m.poster_path AS poster_path,
           m.release_date AS release_date,
           m.overview AS overview,
           m.popularity AS popularity
    ORDER BY m.popularity DESC
    SKIP $offset
    LIMIT $limit
    """
    
    with get_session() as session:
        result = session.run(query, offset=offset, limit=limit)
        
        movies = []
        for record in result:
            poster_url = ""
            if record["poster_path"]:
                poster_url = f"https://image.tmdb.org/t/p/w300{record['poster_path']}"
            
            year = ""
            if record["release_date"]:
                try:
                    year = str(record["release_date"]).split("-")[0]
                except:
                    pass
            
            movies.append({
                'id': record["id"],
                'title': record["title"],
                'rating': round(float(record["rating"] or 0), 1),
                'poster_url': poster_url,
                'year': year,
                'overview': (record["overview"] or "")[:150] + "..." if record["overview"] else "",
                'popularity': round(float(record["popularity"] or 0), 2)
            })
        
        return Response({
            "page": page,
            "results": movies
        })

@api_view(['GET'])
def get_top_rated_movies(request):
    """Get top rated movies"""
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 20))
    offset = (page - 1) * limit
    min_votes = int(request.GET.get('min_votes', 100))
    
    query = """
    MATCH (m:Movie)
    WHERE m.poster_path IS NOT NULL 
      AND m.poster_path <> ''
      AND m.vote_count >= $min_votes
    RETURN m.id AS id, 
           m.original_title AS title,
           m.vote_average AS rating,
           m.vote_count AS vote_count,
           m.poster_path AS poster_path,
           m.release_date AS release_date,
           m.overview AS overview
    ORDER BY m.vote_average DESC
    SKIP $offset
    LIMIT $limit
    """
    
    with get_session() as session:
        result = session.run(query, offset=offset, limit=limit, min_votes=min_votes)
        
        movies = []
        for record in result:
            poster_url = ""
            if record["poster_path"]:
                poster_url = f"https://image.tmdb.org/t/p/w300{record['poster_path']}"
            
            year = ""
            if record["release_date"]:
                try:
                    year = str(record["release_date"]).split("-")[0]
                except:
                    pass
            
            movies.append({
                'id': record["id"],
                'title': record["title"],
                'rating': round(float(record["rating"] or 0), 1),
                'vote_count': record["vote_count"],
                'poster_url': poster_url,
                'year': year,
                'overview': (record["overview"] or "")[:150] + "..." if record["overview"] else ""
            })
        
        return Response({
            "page": page,
            "min_votes": min_votes,
            "results": movies
        })