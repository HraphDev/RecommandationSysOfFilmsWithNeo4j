# film_app/backends.py
from django.contrib.auth.backends import BaseBackend
from .models import User

class Neo4jAuthBackend(BaseBackend):
    """
    Authentication backend that works with Django User model
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Try username first
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                # Try email
                try:
                    user = User.objects.get(email=username)
                except User.DoesNotExist:
                    return None
            
            # Check password
            if user.check_password(password):
                return user
        
        except Exception as e:
            print(f"Authentication error: {e}")
        
        return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None