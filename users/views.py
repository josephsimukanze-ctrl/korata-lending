from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
import json
import secrets
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
import json
import secrets

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
import json
import secrets
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse  # Add this import
from django.db import transaction
import json
import secrets
import logging

from .models import CustomUser, UserProfile, UserSession, UserActivityLog
from .forms import (
    CustomUserCreationForm, CustomUserChangeForm, UserProfileForm,
    UserSearchForm, UserPreferencesForm, TwoFactorSetupForm, APIKeyGenerateForm
)
from .utils import send_welcome_email, send_password_reset_email

logger = logging.getLogger(__name__)

from .models import CustomUser, UserProfile, UserSession, UserActivityLog
from .forms import (
    CustomUserCreationForm, CustomUserChangeForm, UserProfileForm,
    UserSearchForm, UserPreferencesForm, TwoFactorSetupForm, APIKeyGenerateForm
)
from .utils import send_welcome_email, send_password_reset_email

logger = logging.getLogger(__name__)

def is_admin_or_ceo(user):
    """Check if user has admin or CEO privileges"""
    return user.is_superuser or user.role in ['ceo', 'admin']


def log_user_activity(user, action, model_name=None, object_id=None, object_repr=None, changes=None, request=None):
    """Log user activity for audit trail"""
    try:
        activity = UserActivityLog(
            user=user,
            action=action,
            model_name=model_name,
            object_id=str(object_id) if object_id else None,
            object_repr=object_repr,
            changes=changes or {},
            ip_address=request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR')) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255] if request else ''
        )
        activity.save()
    except Exception as e:
        logger.error(f"Error logging activity: {e}")


@login_required
def user_list(request):
    """List all users with search, filter, and pagination"""
    if not is_admin_or_ceo(request.user):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard')
    
    # Get all users directly from database
    users_list = CustomUser.objects.all().order_by('-date_joined')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        users_list = users_list.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )
    
    # Filter by role
    role_filter = request.GET.get('role', '')
    if role_filter:
        users_list = users_list.filter(role=role_filter)
    
    # Filter by department
    dept_filter = request.GET.get('department', '')
    if dept_filter:
        users_list = users_list.filter(department=dept_filter)
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        users_list = users_list.filter(is_active=True)
    elif status_filter == 'inactive':
        users_list = users_list.filter(is_active=False)
    
    # Get statistics
    total_users = CustomUser.objects.count()
    active_users = CustomUser.objects.filter(is_active=True).count()
    inactive_users = CustomUser.objects.filter(is_active=False).count()
    
    # Online users (last 5 minutes)
    from django.utils import timezone
    five_minutes_ago = timezone.now() - timezone.timedelta(minutes=5)
    online_users = CustomUser.objects.filter(last_activity__gte=five_minutes_ago).count()
    
    # Prepare user data for template
    user_data = []
    for user in users_list:
        user_data.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'initials': user.initials,
            'role': user.role,
            'role_display': user.get_role_display(),
            'phone_number': user.phone_number or '',
            'is_active': user.is_active,
            'last_login': user.last_login,
            'department': user.department or '',
        })
    
    context = {
        'users': user_data,
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'online_users': online_users,
        'search_query': search_query,
        'role_filter': role_filter,
        'dept_filter': dept_filter,
        'status_filter': status_filter,
        'is_admin_or_ceo': is_admin_or_ceo(request.user),
    }
    
    return render(request, 'users/user_list.html', context)
@login_required
def user_detail(request, user_id):
    """View user details with activity logs and sessions"""
    user_obj = get_object_or_404(CustomUser, id=user_id)
    
    # Check permissions
    if not is_admin_or_ceo(request.user) and request.user.id != user_obj.id:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard')
    
    # Get or create user profile
    profile, created = UserProfile.objects.get_or_create(user=user_obj)
    
    # Get user activity logs (last 20)
    activity_logs = UserActivityLog.objects.filter(user=user_obj).order_by('-timestamp')[:20]
    
    # Get active sessions
    active_sessions = UserSession.objects.filter(user=user_obj, is_active=True).order_by('-login_time')
    
    # Get statistics
    total_logins = UserSession.objects.filter(user=user_obj).count()
    total_activities = UserActivityLog.objects.filter(user=user_obj).count()
    
    # Get related data
    created_by = None
    if hasattr(user_obj, 'created_by'):
        created_by = user_obj.created_by
    
    # Check if user is online
    five_minutes_ago = timezone.now() - timezone.timedelta(minutes=5)
    is_online = user_obj.last_activity and user_obj.last_activity >= five_minutes_ago
    
    # Check if we should show credentials (for newly created users)
    show_credentials = request.GET.get('show_credentials', False)
    generated_password = None
    generated_username = None
    
    if show_credentials:
        # Get password from session (set during user creation)
        generated_password = request.session.pop('generated_password', None)
        generated_username = request.session.pop('generated_username', None)
        
        # If not in session, try to get from query param (less secure, but works)
        if not generated_password:
            generated_password = request.GET.get('password', None)
    
    # Log this view
    log_user_activity(
        user=request.user,
        action='view',
        model_name='CustomUser',
        object_id=user_obj.id,
        object_repr=str(user_obj),
        request=request
    )
    
    context = {
        'user_obj': user_obj,
        'profile': profile,
        'activity_logs': activity_logs,
        'active_sessions': active_sessions,
        'total_logins': total_logins,
        'total_activities': total_activities,
        'created_by': created_by,
        'is_online': is_online,
        'show_credentials': show_credentials,
        'generated_password': generated_password,
        'generated_username': generated_username,
        'can_edit': is_admin_or_ceo(request.user) or request.user.id == user_obj.id,
        'can_delete': is_admin_or_ceo(request.user) and request.user.id != user_obj.id,
        'can_reset_password': is_admin_or_ceo(request.user) or request.user.id == user_obj.id,
        'is_own_profile': request.user.id == user_obj.id,
    }
    
    return render(request, 'users/user_detail.html', context)

@login_required
@user_passes_test(is_admin_or_ceo)
def user_create(request):
    """Create new user with auto-generated username and password"""
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    
                    # Get the generated username and password
                    username = form.cleaned_data.get('username')
                    password = form.cleaned_data.get('password1')
                    
                    # Set username if not already set
                    if not user.username and username:
                        user.username = username
                    
                    # Set password
                    if password:
                        user.set_password(password)
                    
                    # Save user
                    user.save()
                    
                    # Create user profile
                    UserProfile.objects.get_or_create(user=user)
                    
                    # Store generated password in session to display on detail page
                    request.session['generated_password'] = password
                    request.session['generated_username'] = user.username
                    
                    # Send welcome email
                    email_sent = False
                    if user.email:
                        try:
                            email_sent = send_welcome_email(user, password)
                        except Exception as e:
                            logger.error(f"Failed to send welcome email: {e}")
                    
                    # Log activity
                    log_user_activity(
                        user=request.user,
                        action='create',
                        model_name='CustomUser',
                        object_id=user.id,
                        object_repr=str(user),
                        changes={
                            'username': user.username,
                            'email': user.email,
                            'role': user.role,
                            'first_name': user.first_name,
                            'last_name': user.last_name
                        },
                        request=request
                    )
                    
                    if email_sent:
                        messages.success(
                            request, 
                            f'User {user.username} created successfully! Credentials sent to {user.email}'
                        )
                    else:
                        messages.warning(
                            request, 
                            f'User {user.username} created successfully! Password: {password}'
                        )
                    
                    # Redirect to user detail with show_credentials flag - No reverse needed
                    return redirect(f'/users/{user.id}/?show_credentials=true')
                    
            except Exception as e:
                messages.error(request, f'Error creating user: {str(e)}')
                logger.error(f"User creation error: {e}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'users/user_form.html', {'form': form, 'title': 'Create User'})
@login_required
def user_edit(request, user_id):
    """Edit user profile"""
    user_obj = get_object_or_404(CustomUser, id=user_id)
    
    if not is_admin_or_ceo(request.user) and request.user.id != user_obj.id:
        messages.error(request, 'You do not have permission to edit this user.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, request.FILES, instance=user_obj)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Get old data for logging
                    old_data = {
                        'username': user_obj.username,
                        'email': user_obj.email,
                        'role': user_obj.role,
                        'first_name': user_obj.first_name,
                        'last_name': user_obj.last_name,
                        'phone_number': user_obj.phone_number,
                        'is_active': user_obj.is_active,
                    }
                    
                    user = form.save()
                    
                    # Log changes
                    new_data = {
                        'username': user.username,
                        'email': user.email,
                        'role': user.role,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'phone_number': user.phone_number,
                        'is_active': user.is_active,
                    }
                    
                    changes = {}
                    for key in old_data:
                        if old_data[key] != new_data[key]:
                            changes[key] = {'old': str(old_data[key]), 'new': str(new_data[key])}
                    
                    if changes:
                        log_user_activity(
                            user=request.user,
                            action='update',
                            model_name='CustomUser',
                            object_id=user.id,
                            object_repr=str(user),
                            changes=changes,
                            request=request
                        )
                    
                    messages.success(request, 'Profile updated successfully!')
                    return redirect('users:user_detail', user_id=user.id)
                    
            except Exception as e:
                messages.error(request, f'Error updating user: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CustomUserChangeForm(instance=user_obj)
    
    return render(request, 'users/user_form.html', {'form': form, 'title': 'Edit User', 'user': user_obj})


@login_required
@user_passes_test(is_admin_or_ceo)
def user_delete(request, user_id):
    """Delete user"""
    user_obj = get_object_or_404(CustomUser, id=user_id)
    
    if request.user.id == user_obj.id:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('users:user_list')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                username = user_obj.username
                
                # Log before deletion
                log_user_activity(
                    user=request.user,
                    action='delete',
                    model_name='CustomUser',
                    object_id=user_obj.id,
                    object_repr=username,
                    changes={'deleted_user': username},
                    request=request
                )
                
                user_obj.delete()
                messages.success(request, f'User {username} deleted successfully!')
                return redirect('users:user_list')
                
        except Exception as e:
            messages.error(request, f'Error deleting user: {str(e)}')
    
    return render(request, 'users/user_confirm_delete.html', {'user': user_obj})

@login_required
def change_password(request):
    """Change user password"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            
            # Log activity
            log_user_activity(
                user=request.user,
                action='update',
                model_name='CustomUser',
                object_id=request.user.id,
                object_repr=str(request.user),
                changes={'password': 'changed'},
                request=request
            )
            
            messages.success(request, 'Your password was successfully updated!')
            return redirect('users:user_detail', user_id=request.user.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'users/change_password.html', {'form': form})


@login_required
def update_profile(request):
    """Update user profile settings"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            
            # Log activity
            log_user_activity(
                user=request.user,
                action='update',
                model_name='UserProfile',
                object_id=request.user.id,
                object_repr=f"Profile for {request.user.username}",
                changes={'profile_updated': True},
                request=request
            )
            
            messages.success(request, 'Profile settings updated successfully!')
            return redirect('users:user_detail', user_id=request.user.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserProfileForm(instance=profile)
    
    return render(request, 'users/profile_settings.html', {'form': form})


@login_required
def update_preferences(request):
    """Update user preferences"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = UserPreferencesForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            
            # Update session with user preferences
            request.session['user_preferences'] = {
                'language': profile.language,
                'timezone': profile.timezone,
                'theme': profile.theme,
                'sidebar_collapsed': profile.sidebar_collapsed,
            }
            
            messages.success(request, 'Preferences updated successfully!')
            return redirect('users:user_detail', user_id=request.user.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserPreferencesForm(instance=profile)
    
    return render(request, 'users/preferences.html', {'form': form})

@login_required
def two_factor_setup(request):
    """Setup two-factor authentication"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # Generate secret if not exists
    if not profile.two_factor_secret:
        profile.two_factor_secret = secrets.token_hex(20)
        profile.save()
    
    if request.method == 'POST':
        form = TwoFactorSetupForm(request.POST)
        if form.is_valid():
            # Verify OTP code (simplified - integrate with actual 2FA library)
            otp_code = form.cleaned_data['otp_code']
            # For demo purposes, accept any 6-digit code
            if len(otp_code) == 6 and otp_code.isdigit():
                profile.two_factor_enabled = True
                profile.save()
                
                log_user_activity(
                    user=request.user,
                    action='update',
                    model_name='UserProfile',
                    object_id=request.user.id,
                    object_repr=f"2FA enabled for {request.user.username}",
                    changes={'two_factor_enabled': True},
                    request=request
                )
                
                messages.success(request, 'Two-factor authentication enabled successfully!')
                return redirect('users:user_detail', user_id=request.user.id)
            else:
                messages.error(request, 'Invalid OTP code. Please try again.')
    else:
        form = TwoFactorSetupForm()
    
    context = {
        'form': form,
        'secret': profile.two_factor_secret,
        'two_factor_enabled': profile.two_factor_enabled,
    }
    
    return render(request, 'users/two_factor_setup.html', context)


@login_required
def disable_two_factor(request):
    """Disable two-factor authentication"""
    if request.method == 'POST':
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        profile.two_factor_enabled = False
        profile.two_factor_secret = None
        profile.save()
        
        messages.success(request, 'Two-factor authentication disabled.')
        return redirect('users:user_detail', user_id=request.user.id)
    
    return render(request, 'users/disable_two_factor.html')


@login_required
def api_key_management(request):
    """Manage API keys"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = APIKeyGenerateForm(request.POST)
        if form.is_valid():
            profile.regenerate_api_key()
            
            log_user_activity(
                user=request.user,
                action='update',
                model_name='UserProfile',
                object_id=request.user.id,
                object_repr=f"API key regenerated for {request.user.username}",
                changes={'api_key_regenerated': True},
                request=request
            )
            
            messages.success(request, 'New API key generated successfully!')
            return redirect('users:api_key_management')
    else:
        form = APIKeyGenerateForm()
    
    context = {
        'form': form,
        'api_key': profile.api_key,
        'api_key_created': profile.api_key_created,
        'api_key_last_used': profile.api_key_last_used,
    }
    
    return render(request, 'users/api_key_management.html', context)


@login_required
def user_sessions(request):
    """View and manage user sessions"""
    sessions = UserSession.objects.filter(user=request.user, is_active=True).order_by('-login_time')
    
    if request.method == 'POST':
        # Terminate all other sessions
        sessions.exclude(session_key=request.session.session_key).update(is_active=False)
        messages.success(request, 'All other sessions have been terminated.')
        return redirect('users:user_sessions')
    
    context = {
        'sessions': sessions,
        'current_session_key': request.session.session_key,
    }
    
    return render(request, 'users/user_sessions.html', context)


@login_required
def terminate_session(request, session_id):
    """Terminate a specific session"""
    session = get_object_or_404(UserSession, id=session_id, user=request.user)
    
    if request.method == 'POST':
        session.is_active = False
        session.save()
        messages.success(request, 'Session terminated successfully.')
    
    return redirect('users:user_sessions')


from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from .models import CustomUser
import json

@staff_member_required
def api_user_list(request):
    """API endpoint for user list"""
    try:
        users = CustomUser.objects.all().values(
            'id', 'username', 'email', 'first_name', 'last_name', 
            'role', 'phone_number', 'is_active', 'last_login', 'department'
        )
        
        user_list = []
        for user in users:
            # Get role display name
            role_display = dict(CustomUser.ROLE_CHOICES).get(user['role'], user['role'])
            
            # Get full name
            full_name = f"{user['first_name']} {user['last_name']}".strip()
            if not full_name:
                full_name = user['username']
            
            # Get initials
            initials = ""
            if user['first_name']:
                initials += user['first_name'][0]
            if user['last_name']:
                initials += user['last_name'][0]
            if not initials and user['username']:
                initials = user['username'][0].upper()
            
            user_list.append({
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'full_name': full_name,
                'initials': initials.upper(),
                'role': user['role'],
                'role_display': role_display,
                'phone_number': user['phone_number'] or '',
                'is_active': user['is_active'],
                'last_login': user['last_login'],
                'department': user['department'] or '',
            })
        
        return JsonResponse({'users': user_list}, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e), 'users': []}, status=500)


@staff_member_required
def api_user_count(request):
    """API endpoint for user count"""
    try:
        total = CustomUser.objects.count()
        active = CustomUser.objects.filter(is_active=True).count()
        inactive = CustomUser.objects.filter(is_active=False).count()
        
        # Count online users (last activity within last 5 minutes)
        from django.utils import timezone
        from datetime import timedelta
        five_minutes_ago = timezone.now() - timedelta(minutes=5)
        online = CustomUser.objects.filter(last_activity__gte=five_minutes_ago).count()
        
        # Role counts
        roles = {}
        for role_code, role_name in CustomUser.ROLE_CHOICES:
            roles[role_code] = CustomUser.objects.filter(role=role_code).count()
        
        return JsonResponse({
            'total': total,
            'active': active,
            'inactive': inactive,
            'online': online,
            'roles': roles
        })
    except Exception as e:
        return JsonResponse({'error': str(e), 'total': 0, 'active': 0, 'inactive': 0, 'online': 0}, status=500)


@staff_member_required
def api_user_detail(request, user_id):
    """API endpoint for user details"""
    user = get_object_or_404(CustomUser, id=user_id)
    
    return JsonResponse({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'full_name': user.full_name,
        'role': user.role,
        'role_display': user.get_role_display(),
        'phone_number': user.phone_number,
        'employee_id': user.employee_id,
        'department': user.department,
        'position': user.position,
        'is_active': user.is_active,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'last_login': user.last_login,
        'date_joined': user.date_joined,
        'last_activity': user.last_activity,
        'is_online': user.is_online,
    })


@login_required
def bulk_user_action(request):
    """Bulk actions on users (activate/deactivate/delete)"""
    if not is_admin_or_ceo(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        user_ids = data.get('user_ids', [])
        action = data.get('action', '')
        
        if not user_ids:
            return JsonResponse({'error': 'No users selected'}, status=400)
        
        users = CustomUser.objects.filter(id__in=user_ids)
        
        if action == 'activate':
            users.update(is_active=True)
            message = f'{users.count()} users activated'
        elif action == 'deactivate':
            users.update(is_active=False)
            message = f'{users.count()} users deactivated'
        elif action == 'delete':
            # Don't allow deleting own account
            users = users.exclude(id=request.user.id)
            count = users.count()
            users.delete()
            message = f'{count} users deleted'
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        return JsonResponse({'success': True, 'message': message})
    
    return JsonResponse({'error': 'Invalid method'}, status=405)


@login_required
def export_users(request):
    """Export users to CSV"""
    if not is_admin_or_ceo(request.user):
        messages.error(request, 'You do not have permission to export users.')
        return redirect('users:user_list')
    
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Username', 'Email', 'First Name', 'Last Name', 'Role', 'Phone', 'Department', 'Position', 'Status', 'Last Login', 'Date Joined'])
    
    users = CustomUser.objects.all().order_by('-date_joined')
    for user in users:
        writer.writerow([
            user.username,
            user.email,
            user.first_name,
            user.last_name,
            user.get_role_display(),
            user.phone_number or '',
            user.department or '',
            user.position or '',
            'Active' if user.is_active else 'Inactive',
            user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else '',
            user.date_joined.strftime('%Y-%m-%d %H:%M'),
        ])
    
    return response


from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from django.contrib import messages

from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from django.contrib import messages
# users/views.py - Complete fixed version
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.conf import settings
from .forms import UserRegistrationForm

def user_login(request):
    """Handle user login"""
    
    # Get the next parameter (where to redirect after login)
    next_url = request.GET.get('next', '')
    
    # Redirect if already logged in
    if request.user.is_authenticated:
        if next_url:
            return redirect(next_url)
        return redirect('/dashboard/')  # Direct URL instead of named URL
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember = request.POST.get('remember', False)
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Login successful
            login(request, user)
            
            # Set session expiry based on remember me
            if not remember:
                request.session.set_expiry(0)  # Session expires when browser closes
            else:
                request.session.set_expiry(2592000)  # 30 days
            
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            
            # Redirect to next URL if provided, otherwise dashboard
            next_url = request.POST.get('next', '')
            if next_url:
                return redirect(next_url)
            return redirect('/dashboard/')  # Direct URL
        else:
            messages.error(request, 'Invalid username or password.')
    
    # Pass next parameter to template
    context = {
        'next': next_url
    }
    return render(request, 'users/login.html', context)


def register(request):
    """Handle user registration"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            
            # Log the user in
            login(request, user)
            
            messages.success(request, 'Registration successful! Welcome to Korata Lending System.')
            return redirect('/dashboard/')  # Direct URL
    else:
        form = UserRegistrationForm()
    
    return render(request, 'users/register.html', {'form': form})

def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages

def user_logout(request):
    """User logout"""
    if request.user.is_authenticated:
        user = request.user
        user.is_online = False
        user.save(update_fields=['is_online'])
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
    return redirect('/users/login/')  # Redirect to login page URL directly

@login_required
@user_passes_test(is_admin_or_ceo)
def reset_user_password(request, user_id):
    """Reset user password and send new credentials"""
    user_obj = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        # Generate new password
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        new_password = ''.join(secrets.choice(alphabet) for _ in range(12))
        
        # Set new password
        user_obj.set_password(new_password)
        user_obj.save()
        
        # Log activity
        log_user_activity(
            user=request.user,
            action='update',
            model_name='CustomUser',
            object_id=user_obj.id,
            object_repr=str(user_obj),
            changes={'password_reset': True},
            request=request
        )
        
        messages.success(
            request, 
            f'Password reset for {user_obj.username}. New password: {new_password}'
        )
        
        return redirect('users:user_detail', user_id=user_obj.id)
    
    return render(request, 'users/reset_password.html', {'user': user_obj})

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from .models import ActivityLog

User = get_user_model()

@login_required
def api_user_stats(request):
    """API endpoint for user statistics"""
    stats = {
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'inactive_users': User.objects.filter(is_active=False).count(),
        'admins': User.objects.filter(is_superuser=True).count(),
        'staff': User.objects.filter(is_staff=True).count(),
        'by_role': {},
    }
    
    # Group by role if you have a role field
    if hasattr(User, 'role'):
        role_stats = User.objects.values('role').annotate(count=Count('id'))
        for stat in role_stats:
            stats['by_role'][stat['role']] = stat['count']
    
    return JsonResponse(stats)


@login_required
def api_recent_activity(request):
    """API endpoint for recent user activity"""
    limit = int(request.GET.get('limit', 10))
    
    activities = ActivityLog.objects.all().order_by('-created_at')[:limit]
    
    activity_data = []
    for activity in activities:
        activity_data.append({
            'id': activity.id,
            'user': activity.user.get_full_name() if activity.user and hasattr(activity.user, 'get_full_name') else str(activity.user) if activity.user else 'System',
            'action': activity.action,
            'details': activity.details,
            'ip_address': activity.ip_address,
            'created_at': activity.created_at.isoformat() if activity.created_at else None,
        })
    
    return JsonResponse({'activities': activity_data})


@login_required
def api_user_activity(request, user_id):
    """API endpoint for specific user activity"""
    user = get_object_or_404(User, id=user_id)
    
    if not request.user.is_superuser and request.user.id != user_id:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    limit = int(request.GET.get('limit', 20))
    activities = ActivityLog.objects.filter(user=user).order_by('-created_at')[:limit]
    
    activity_data = []
    for activity in activities:
        activity_data.append({
            'id': activity.id,
            'action': activity.action,
            'details': activity.details,
            'ip_address': activity.ip_address,
            'created_at': activity.created_at.isoformat() if activity.created_at else None,
        })
    
    return JsonResponse({'activities': activity_data})


@login_required
def user_toggle_status(request, user_id):
    """Toggle user active status"""
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to change user status.')
        return redirect('users:user_list')
    
    user = get_object_or_404(User, id=user_id)
    
    if user == request.user:
        messages.error(request, 'You cannot change your own status.')
        return redirect('users:user_list')
    
    user.is_active = not user.is_active
    user.save()
    
    status = 'activated' if user.is_active else 'deactivated'
    messages.success(request, f'User {user.username} has been {status}.')
    
    # Log the activity
    ActivityLog.objects.create(
        user=request.user,
        action=f'User {status}',
        details=f'User {user.username} was {status} by {request.user.username}',
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    return redirect('users:user_list')


@login_required
def bulk_import_users(request):
    """Bulk import users from CSV/Excel"""
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to import users.')
        return redirect('users:user_list')
    
    if request.method == 'POST':
        # Handle file upload and import logic
        import_file = request.FILES.get('import_file')
        if import_file:
            # Process the file
            messages.success(request, f'Successfully imported users from {import_file.name}')
            return redirect('users:user_list')
    
    return render(request, 'users/bulk_import.html')


@login_required
def export_template(request):
    """Download CSV template for user import"""
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="user_import_template.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['username', 'email', 'first_name', 'last_name', 'role', 'is_active'])
    writer.writerow(['john_doe', 'john@example.com', 'John', 'Doe', 'staff', 'True'])
    writer.writerow(['jane_smith', 'jane@example.com', 'Jane', 'Smith', 'loan_officer', 'True'])
    
    return response


@login_required
def user_notifications(request):
    """View user notifications"""
    from notifications.models import Notification
    
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    
    context = {
        'notifications': notifications,
        'unread_count': notifications.filter(is_read=False).count(),
    }
    return render(request, 'users/notifications.html', context)


@login_required
def mark_notifications_read(request):
    """Mark all notifications as read"""
    from notifications.models import Notification
    
    if request.method == 'POST':
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        messages.success(request, 'All notifications marked as read.')
    
    return redirect('users:user_notifications')


@login_required
def notification_detail(request, notification_id):
    """View notification details"""
    from notifications.models import Notification
    
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()
    
    return render(request, 'users/notification_detail.html', {'notification': notification})

# users/views.py - Add this function

from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

def api_user_stats(request):
    """API endpoint for user statistics"""
    
    # Get date thresholds for recent activity
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Basic counts
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    inactive_users = User.objects.filter(is_active=False).count()
    
    # Role-based counts (if role field exists)
    ceo_count = 0
    admin_count = 0
    loan_officer_count = 0
    accountant_count = 0
    auditor_count = 0
    collateral_officer_count = 0
    
    if hasattr(User, 'role'):
        ceo_count = User.objects.filter(role='ceo').count()
        admin_count = User.objects.filter(role='admin').count()
        loan_officer_count = User.objects.filter(role='loan_officer').count()
        accountant_count = User.objects.filter(role='accountant').count()
        auditor_count = User.objects.filter(role='auditor').count()
        collateral_officer_count = User.objects.filter(role='collateral_officer').count()
    
    # Staff and superuser counts
    staff_count = User.objects.filter(is_staff=True).count()
    superuser_count = User.objects.filter(is_superuser=True).count()
    
    # Recent activity
    active_today = User.objects.filter(last_login__date=today).count() if hasattr(User, 'last_login') else 0
    active_this_week = User.objects.filter(last_login__date__gte=week_ago).count() if hasattr(User, 'last_login') else 0
    active_this_month = User.objects.filter(last_login__date__gte=month_ago).count() if hasattr(User, 'last_login') else 0
    
    # New users
    new_today = User.objects.filter(date_joined__date=today).count()
    new_this_week = User.objects.filter(date_joined__date__gte=week_ago).count()
    new_this_month = User.objects.filter(date_joined__date__gte=month_ago).count()
    
    # Online users (if is_online field exists)
    online_users = User.objects.filter(is_online=True).count() if hasattr(User, 'is_online') else 0
    
    # Locked accounts (if account_locked field exists)
    locked_accounts = User.objects.filter(account_locked=True).count() if hasattr(User, 'account_locked') else 0
    
    # Email verified (if email_verified field exists)
    email_verified = User.objects.filter(email_verified=True).count() if hasattr(User, 'email_verified') else 0
    
    # Two-factor enabled (if profile has two_factor_enabled)
    two_factor_enabled = 0
    try:
        from .models import UserProfile
        two_factor_enabled = UserProfile.objects.filter(two_factor_enabled=True).count()
    except (ImportError, Exception):
        pass
    
    stats = {
        # Basic counts
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'staff_count': staff_count,
        'superuser_count': superuser_count,
        
        # Role counts
        'ceo_count': ceo_count,
        'admin_count': admin_count,
        'loan_officer_count': loan_officer_count,
        'accountant_count': accountant_count,
        'auditor_count': auditor_count,
        'collateral_officer_count': collateral_officer_count,
        
        # Activity stats
        'active_today': active_today,
        'active_this_week': active_this_week,
        'active_this_month': active_this_month,
        'online_users': online_users,
        'locked_accounts': locked_accounts,
        
        # Growth stats
        'new_today': new_today,
        'new_this_week': new_this_week,
        'new_this_month': new_this_month,
        
        # Security stats
        'email_verified': email_verified,
        'two_factor_enabled': two_factor_enabled,
        
        # Additional stats
        'male_users': 0,
        'female_users': 0,
        'users_with_2fa': two_factor_enabled,
    }
    
    # Gender stats if field exists
    if hasattr(User, 'gender'):
        stats['male_users'] = User.objects.filter(gender='male').count()
        stats['female_users'] = User.objects.filter(gender='female').count()
    
    # Calculate percentages
    if total_users > 0:
        stats['active_percentage'] = round((active_users / total_users) * 100, 1)
        stats['inactive_percentage'] = round((inactive_users / total_users) * 100, 1)
    else:
        stats['active_percentage'] = 0
        stats['inactive_percentage'] = 0
    
    # Return response with CORS headers if needed
    response = JsonResponse(stats)
    response['Access-Control-Allow-Origin'] = '*'
    
    return response


@login_required
def profile_view(request):
    """View user's own profile"""
    return render(request, 'users/profile.html', {'user': request.user})

@login_required
def profile_edit(request):
    """User editing their own profile"""
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('users:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProfileUpdateForm(instance=request.user)
    
    return render(request, 'users/profile_edit.html', {'form': form, 'title': 'Edit Profile'})

from .forms import (
    CustomUserCreationForm, 
    CustomUserChangeForm, 
    ProfileUpdateForm,  # Add this import
    UserProfileForm,
    CustomPasswordChangeForm,
    UserLoginForm,
    UserSearchForm,
    UserPreferencesForm,
    BulkUserActionForm
)
