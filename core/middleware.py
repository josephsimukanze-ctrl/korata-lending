# core/middleware.py - Fixed version

from django.utils import timezone
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import logout
import logging

logger = logging.getLogger(__name__)


class ActivityTrackingMiddleware:
    """Track user activity and update last activity timestamp"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Update last activity for authenticated users
        if request.user.is_authenticated:
            # Update session last activity with timezone-aware datetime
            request.session['last_activity'] = timezone.now().isoformat()
        
        response = self.get_response(request)
        return response


class SessionIdleTimeoutMiddleware:
    """Log out users after idle timeout period (2 minutes)"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip timeout check for certain paths
        skip_paths = ['/keep-alive/', '/api/', '/media/', '/static/']
        current_path = request.path
        
        # Skip middleware for API and static paths
        if any(request.path.startswith(path) for path in skip_paths):
            return self.get_response(request)
        
        # Check if user is authenticated
        if request.user.is_authenticated:
            # Get last activity time from session
            last_activity = request.session.get('last_activity')
            current_time = timezone.now()
            
            if last_activity:
                try:
                    # Parse last activity time - handle both string and datetime objects
                    if isinstance(last_activity, str):
                        from datetime import datetime
                        # Parse ISO format string
                        last_activity_time = datetime.fromisoformat(last_activity)
                        # Make it timezone-aware if it's naive
                        if timezone.is_naive(last_activity_time):
                            from django.utils.timezone import make_aware
                            last_activity_time = make_aware(last_activity_time)
                    else:
                        # If it's already a datetime object
                        last_activity_time = last_activity
                        # Make it timezone-aware if it's naive
                        if timezone.is_naive(last_activity_time):
                            from django.utils.timezone import make_aware
                            last_activity_time = make_aware(last_activity_time)
                    
                    # Calculate idle time in seconds
                    idle_time = (current_time - last_activity_time).total_seconds()
                    
                    # Import settings
                    from django.conf import settings
                    
                    # If idle time exceeds IDLE_TIMEOUT_SECONDS (2 minutes), log out
                    if idle_time > settings.IDLE_TIMEOUT_SECONDS:
                        # Log the logout event
                        logger.warning(f"User {request.user.username} logged out due to inactivity ({int(idle_time)} seconds idle)")
                        
                        # Logout the user
                        logout(request)
                        
                        # Clear session
                        request.session.flush()
                        
                        # Redirect to login page with message (except for AJAX requests)
                        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            from django.contrib import messages
                            messages.warning(request, 'You have been logged out due to inactivity.')
                            return redirect(settings.LOGIN_URL)
                        else:
                            # For AJAX requests, return unauthorized
                            from django.http import JsonResponse
                            return JsonResponse({'error': 'Session expired'}, status=401)
                
                except Exception as e:
                    logger.error(f"Error processing session timeout: {str(e)}")
                    # If there's an error, reset the session
                    request.session['last_activity'] = current_time.isoformat()
            
            # Update activity timestamp for this request
            request.session['last_activity'] = current_time.isoformat()
        
        response = self.get_response(request)
        return response


class SecurityHeadersMiddleware:
    """Add security headers to all responses"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Cache control for authenticated pages
        if request.user.is_authenticated:
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
        
        return response