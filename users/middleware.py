from django.utils import timezone
from django.core.exceptions import ImproperlyConfigured

class UserPreferencesMiddleware:
    """Apply user preferences globally"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                profile = request.user.profile
                
                # Apply timezone - try to import pytz, fallback to Django's timezone
                if profile.timezone:
                    try:
                        import pytz
                        try:
                            timezone.activate(pytz.timezone(profile.timezone))
                        except Exception:
                            # Fallback to default
                            pass
                    except ImportError:
                        # pytz not installed, use Django's timezone handling
                        pass
                
                # Store preferences in session
                request.session['user_theme'] = profile.theme
                request.session['user_language'] = profile.language
                request.session['sidebar_collapsed'] = profile.sidebar_collapsed
                
            except Exception:
                pass
        
        response = self.get_response(request)
        return response