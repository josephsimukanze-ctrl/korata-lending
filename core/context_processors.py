# core/context_processors.py
from django.conf import settings
from django.utils import timezone


def session_timeout(request):
    """Add session timeout settings to template context"""
    
    # Calculate remaining time for JS warning
    remaining_seconds = 0
    warning_seconds = getattr(settings, 'SESSION_IDLE_WARNING_TIME', 100)
    idle_timeout = getattr(settings, 'IDLE_TIMEOUT_SECONDS', 120)
    session_age = getattr(settings, 'SESSION_COOKIE_AGE', 1500)
    
    if request.user.is_authenticated:
        last_activity = request.session.get('last_activity')
        if last_activity:
            last_activity_time = timezone.datetime.fromisoformat(last_activity)
            current_time = timezone.now()
            elapsed = (current_time - last_activity_time).total_seconds()
            remaining_seconds = max(0, idle_timeout - elapsed)
    
    return {
        'SESSION_IDLE_TIMEOUT': idle_timeout,
        'SESSION_IDLE_WARNING_TIME': warning_seconds,
        'SESSION_COOKIE_AGE': session_age,
        'SESSION_REMAINING_SECONDS': int(remaining_seconds),
        'SESSION_TIMEOUT_ENABLED': True,
    }