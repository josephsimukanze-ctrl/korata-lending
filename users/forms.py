from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.utils import timezone
from .models import CustomUser, UserProfile
import secrets
import string
import re
import random

CustomUser = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """Custom user creation form with auto-generated username and password"""
    
    # Make username optional since it will be auto-generated
    username = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Auto-generated',
            'readonly': 'readonly'
        })
    )
    
    # Make password fields optional since they will be auto-generated
    password1 = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Auto-generated'
        })
    )
    password2 = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm auto-generated password'
        })
    )
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'role',
                  'department', 'position', 'bio', 'address', 'city', 'country', 'postal_code')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+260XXXXXXXXX'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Job Position'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Short biography'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Street address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Postal Code'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add custom classes to fields
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
    
    def generate_username(self, first_name, last_name):
        """Generate a unique username from first name and last name"""
        if first_name and last_name:
            base = f"{first_name.lower()}.{last_name.lower()}"
        elif first_name:
            base = first_name.lower()
        elif last_name:
            base = last_name.lower()
        else:
            base = "user"
        
        # Remove any special characters
        base = re.sub(r'[^a-z0-9.]', '', base)
        
        # Add random numbers
        random_num = random.randint(100, 999)
        username = f"{base}{random_num}"
        
        # Ensure username is unique
        while CustomUser.objects.filter(username=username).exists():
            random_num = random.randint(100, 999)
            username = f"{base}{random_num}"
        
        return username
    
    def generate_password(self):
        """Generate a secure random password"""
        # Define character sets
        uppercase = string.ascii_uppercase
        lowercase = string.ascii_lowercase
        digits = string.digits
        special = "!@#$%^&*"
        
        # Ensure at least one of each type
        password = [
            secrets.choice(uppercase),
            secrets.choice(lowercase),
            secrets.choice(digits),
            secrets.choice(special)
        ]
        
        # Fill the rest with random characters
        all_chars = uppercase + lowercase + digits + special
        for _ in range(8):
            password.append(secrets.choice(all_chars))
        
        # Shuffle the password
        random.shuffle(password)
        return ''.join(password)
    
    def clean_username(self):
        """Username is auto-generated, so return None if not provided"""
        username = self.cleaned_data.get('username')
        if not username:
            return None
        return username
    
    def clean_phone_number(self):
        """Validate phone number format"""
        phone = self.cleaned_data.get('phone_number')
        if phone:
            # Basic phone number validation for Zambian format
            pattern = re.compile(r'^\+260\d{9}$|^0\d{9}$')
            if not pattern.match(phone):
                raise forms.ValidationError(
                    'Enter a valid phone number (e.g., +260977123456 or 0977123456)'
                )
        return phone
    
    def clean_email(self):
        """Validate email is unique"""
        email = self.cleaned_data.get('email')
        if email and CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        email = cleaned_data.get('email')
        phone_number = cleaned_data.get('phone_number')
        
        # Validate required fields
        if not first_name:
            self.add_error('first_name', 'First name is required.')
        if not last_name:
            self.add_error('last_name', 'Last name is required.')
        if not email:
            self.add_error('email', 'Email address is required.')
        if not phone_number:
            self.add_error('phone_number', 'Phone number is required.')
        
        # Generate username if not provided
        if first_name or last_name:
            username = self.generate_username(first_name or '', last_name or '')
            cleaned_data['username'] = username
            self.data = self.data.copy()
            self.data['username'] = username
        
        # Generate password if not provided
        password1 = cleaned_data.get('password1')
        if not password1:
            password = self.generate_password()
            cleaned_data['password1'] = password
            cleaned_data['password2'] = password
            self.data = self.data.copy()
            self.data['password1'] = password
            self.data['password2'] = password
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Set username if not set
        if not user.username:
            user.username = self.cleaned_data['username']
        
        if commit:
            user.save()
            # Create profile automatically
            UserProfile.objects.get_or_create(user=user)
        
        return user


class CustomUserChangeForm(UserChangeForm):
    """Form for editing existing users"""
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'role', 
                  'profile_picture', 'department', 'position', 'bio', 'address', 'city', 
                  'country', 'postal_code', 'is_active')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'address': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Remove password field from change form
        if 'password' in self.fields:
            self.fields.pop('password')
        
        # Add classes to all fields
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
    
    def clean_phone_number(self):
        """Validate phone number format"""
        phone = self.cleaned_data.get('phone_number')
        if phone:
            pattern = re.compile(r'^\+260\d{9}$|^0\d{9}$')
            if not pattern.match(phone):
                raise forms.ValidationError(
                    'Enter a valid phone number (e.g., +260977123456 or 0977123456)'
                )
        return phone


class UserProfileForm(forms.ModelForm):
    """Form for user profile settings with enhanced validation"""
    
    class Meta:
        model = UserProfile
        fields = (
            'employee_number', 
            'hire_date', 
            'email_notifications', 
            'sms_notifications', 
            'whatsapp_notifications',
            'push_notifications',
            'language',
            'timezone',
            'theme',
            'sidebar_collapsed'
        )
        widgets = {
            'employee_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'EMP-XXXX',
                'pattern': '^EMP-[A-Z0-9]{4}$',
            }),
            'hire_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
            'language': forms.Select(attrs={'class': 'form-control'}),
            'timezone': forms.Select(attrs={'class': 'form-control'}),
            'theme': forms.Select(attrs={'class': 'form-control'}),
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sms_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'whatsapp_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'push_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sidebar_collapsed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make all fields optional
        for field_name, field in self.fields.items():
            field.required = False
    
    def clean_employee_number(self):
        """Validate employee number format"""
        employee_number = self.cleaned_data.get('employee_number')
        if employee_number:
            pattern = r'^EMP-[A-Z0-9]{4}$'
            if not re.match(pattern, employee_number):
                raise forms.ValidationError('Employee number must follow format: EMP-XXXX (e.g., EMP-1234)')
            
            # Check uniqueness
            instance = getattr(self, 'instance', None)
            if instance and instance.pk:
                if UserProfile.objects.exclude(pk=instance.pk).filter(employee_number=employee_number).exists():
                    raise forms.ValidationError('This employee number is already in use.')
            else:
                if UserProfile.objects.filter(employee_number=employee_number).exists():
                    raise forms.ValidationError('This employee number is already in use.')
        
        return employee_number
    
    def clean_hire_date(self):
        """Validate hire date"""
        hire_date = self.cleaned_data.get('hire_date')
        if hire_date and hire_date > timezone.now().date():
            raise forms.ValidationError('Hire date cannot be in the future.')
        return hire_date
    
    def save(self, commit=True):
        """Save the form data"""
        instance = super().save(commit=False)
        
        # Auto-generate employee number if not provided
        if not instance.employee_number:
            random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            instance.employee_number = f'EMP-{random_suffix}'
        
        if commit:
            instance.save()
        
        return instance


class UserLoginForm(forms.Form):
    """Custom login form with remember me option"""
    username = forms.CharField(
        max_length=150, 
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    remember_me = forms.BooleanField(
        required=False, 
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        
        if username and password:
            from django.contrib.auth import authenticate
            user = authenticate(username=username, password=password)
            if not user:
                raise forms.ValidationError('Invalid username or password.')
            if not user.is_active:
                raise forms.ValidationError('This account is inactive.')
        
        return cleaned_data


class UserSearchForm(forms.Form):
    """Form for searching and filtering users"""
    search = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, email, or username...'
        })
    )
    role = forms.ChoiceField(
        required=False, 
        choices=[('', 'All Roles')] + list(CustomUser.ROLE_CHOICES), 
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    department = forms.ChoiceField(
        required=False, 
        choices=[('', 'All Departments')] + list(getattr(CustomUser, 'DEPARTMENT_CHOICES', [])), 
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    is_active = forms.ChoiceField(
        required=False, 
        choices=[('', 'All'), ('true', 'Active'), ('false', 'Inactive')], 
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class PasswordResetRequestForm(forms.Form):
    """Password reset request form"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('No user found with this email address.')
        return email


class SetPasswordForm(forms.Form):
    """Set new password form with validation"""
    new_password1 = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New password (min. 8 characters)'
        })
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        })
    )
    
    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1')
        
        # Password strength validation
        if len(password) < 8:
            raise forms.ValidationError('Password must be at least 8 characters long.')
        
        if not any(c.isupper() for c in password):
            raise forms.ValidationError('Password must contain at least one uppercase letter.')
        
        if not any(c.islower() for c in password):
            raise forms.ValidationError('Password must contain at least one lowercase letter.')
        
        if not any(c.isdigit() for c in password):
            raise forms.ValidationError('Password must contain at least one number.')
        
        if not any(c in "!@#$%^&*" for c in password):
            raise forms.ValidationError('Password must contain at least one special character (!@#$%^&*).')
        
        return password
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        
        return cleaned_data


class UserPreferencesForm(forms.ModelForm):
    """Form for user preferences"""
    
    class Meta:
        model = UserProfile
        fields = ('language', 'timezone', 'date_format', 'theme', 'sidebar_collapsed', 
                  'email_notifications', 'sms_notifications', 'whatsapp_notifications', 'push_notifications')
        widgets = {
            'language': forms.Select(attrs={'class': 'form-control'}),
            'timezone': forms.Select(attrs={'class': 'form-control'}),
            'date_format': forms.Select(attrs={'class': 'form-control'}),
            'theme': forms.Select(attrs={'class': 'form-control'}),
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sms_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'whatsapp_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'push_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sidebar_collapsed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-control'


class TwoFactorSetupForm(forms.Form):
    """Two-factor authentication setup form"""
    otp_code = forms.CharField(
        max_length=6, 
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control text-center',
            'placeholder': '000000',
            'autocomplete': 'off',
            'pattern': '[0-9]{6}',
            'maxlength': '6'
        })
    )
    
    def clean_otp_code(self):
        code = self.cleaned_data.get('otp_code')
        if not code.isdigit() or len(code) != 6:
            raise forms.ValidationError('Please enter a valid 6-digit code.')
        return code


class APIKeyGenerateForm(forms.Form):
    """Form to generate API key"""
    confirm = forms.BooleanField(
        required=True, 
        label="I understand that old API keys will be invalidated",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean_confirm(self):
        confirm = self.cleaned_data.get('confirm')
        if not confirm:
            raise forms.ValidationError('You must confirm to generate a new API key.')
        return confirm


class BulkUserActionForm(forms.Form):
    """Form for bulk user actions"""
    ACTION_CHOICES = (
        ('activate', 'Activate Users'),
        ('deactivate', 'Deactivate Users'),
        ('delete', 'Delete Users'),
        ('export', 'Export Selected'),
    )
    
    action = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    confirm = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        confirm = cleaned_data.get('confirm')
        
        if action == 'delete' and not confirm:
            raise forms.ValidationError('Please confirm you want to delete selected users.')
        
        return cleaned_data
    

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.utils import timezone
from .models import CustomUser, UserProfile
import secrets
import string
import re
import random

CustomUser = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """Custom user creation form with auto-generated username and password"""
    
    username = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Auto-generated',
            'readonly': 'readonly'
        })
    )
    password1 = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Auto-generated'
        })
    )
    password2 = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm auto-generated password'
        })
    )
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'role',
                  'department', 'position', 'bio', 'address', 'city', 'country', 'postal_code')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+260XXXXXXXXX'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Job Position'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Short biography'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Street address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Postal Code'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
    
    def generate_username(self, first_name, last_name):
        if first_name and last_name:
            base = f"{first_name.lower()}.{last_name.lower()}"
        elif first_name:
            base = first_name.lower()
        elif last_name:
            base = last_name.lower()
        else:
            base = "user"
        
        base = re.sub(r'[^a-z0-9.]', '', base)
        random_num = random.randint(100, 999)
        username = f"{base}{random_num}"
        
        while CustomUser.objects.filter(username=username).exists():
            random_num = random.randint(100, 999)
            username = f"{base}{random_num}"
        
        return username
    
    def generate_password(self):
        uppercase = string.ascii_uppercase
        lowercase = string.ascii_lowercase
        digits = string.digits
        special = "!@#$%^&*"
        
        password = [
            secrets.choice(uppercase),
            secrets.choice(lowercase),
            secrets.choice(digits),
            secrets.choice(special)
        ]
        
        all_chars = uppercase + lowercase + digits + special
        for _ in range(8):
            password.append(secrets.choice(all_chars))
        
        random.shuffle(password)
        return ''.join(password)
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            pattern = re.compile(r'^\+260\d{9}$|^0\d{9}$')
            if not pattern.match(phone):
                raise forms.ValidationError('Enter a valid phone number (e.g., +260977123456 or 0977123456)')
        return phone
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        email = cleaned_data.get('email')
        phone_number = cleaned_data.get('phone_number')
        
        if not first_name:
            self.add_error('first_name', 'First name is required.')
        if not last_name:
            self.add_error('last_name', 'Last name is required.')
        if not email:
            self.add_error('email', 'Email address is required.')
        if not phone_number:
            self.add_error('phone_number', 'Phone number is required.')
        
        if first_name or last_name:
            username = self.generate_username(first_name or '', last_name or '')
            cleaned_data['username'] = username
        
        password1 = cleaned_data.get('password1')
        if not password1:
            password = self.generate_password()
            cleaned_data['password1'] = password
            cleaned_data['password2'] = password
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        if not user.username:
            user.username = self.cleaned_data['username']
        
        if commit:
            user.save()
            UserProfile.objects.get_or_create(user=user)
        
        return user


class CustomUserChangeForm(UserChangeForm):
    """Form for editing existing users"""
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'role', 
                  'profile_picture', 'department', 'position', 'bio', 'address', 'city', 
                  'country', 'postal_code', 'is_active')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'address': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'password' in self.fields:
            self.fields.pop('password')
        
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            pattern = re.compile(r'^\+260\d{9}$|^0\d{9}$')
            if not pattern.match(phone):
                raise forms.ValidationError('Enter a valid phone number (e.g., +260977123456 or 0977123456)')
        return phone


class UserProfileForm(forms.ModelForm):
    """Form for user profile settings"""
    
    class Meta:
        model = UserProfile
        fields = (
            'employee_number', 'hire_date', 'email_notifications', 'sms_notifications',
            'whatsapp_notifications', 'push_notifications', 'language', 'timezone',
            'theme', 'sidebar_collapsed'
        )
        widgets = {
            'employee_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'EMP-XXXX'}),
            'hire_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'language': forms.Select(attrs={'class': 'form-control'}),
            'timezone': forms.Select(attrs={'class': 'form-control'}),
            'theme': forms.Select(attrs={'class': 'form-control'}),
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sms_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'whatsapp_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'push_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sidebar_collapsed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.required = False


class ProfileUpdateForm(forms.ModelForm):
    """Form for users to update their own profile"""
    
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'phone_number', 'bio', 
                  'address', 'city', 'country', 'profile_picture')
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email Address'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+260XXXXXXXXX'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Short biography'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Street address'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Country'
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and CustomUser.objects.filter(email=email).exclude(id=self.instance.id).exists():
            raise forms.ValidationError('This email is already in use.')
        return email
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            pattern = re.compile(r'^\+260\d{9}$|^0\d{9}$')
            if not pattern.match(phone):
                raise forms.ValidationError('Enter a valid phone number (e.g., +260977123456 or 0977123456)')
        return phone


class CustomPasswordChangeForm(PasswordChangeForm):
    """Custom password change form"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'
            self.fields[field].widget.attrs['placeholder'] = self.fields[field].label


class UserLoginForm(forms.Form):
    """Custom login form"""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class UserSearchForm(forms.Form):
    """Form for searching users"""
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, email, or username...'
        })
    )
    role = forms.ChoiceField(
        required=False,
        choices=[('', 'All Roles')] + list(CustomUser.ROLE_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    is_active = forms.ChoiceField(
        required=False,
        choices=[('', 'All'), ('true', 'Active'), ('false', 'Inactive')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class UserPreferencesForm(forms.ModelForm):
    """Form for user preferences"""
    
    class Meta:
        model = UserProfile
        fields = ('language', 'timezone', 'theme', 'sidebar_collapsed',
                  'email_notifications', 'sms_notifications', 'push_notifications')
        widgets = {
            'language': forms.Select(attrs={'class': 'form-control'}),
            'timezone': forms.Select(attrs={'class': 'form-control'}),
            'theme': forms.Select(attrs={'class': 'form-control'}),
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sms_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'push_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sidebar_collapsed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if not isinstance(self.fields[field].widget, forms.CheckboxInput):
                self.fields[field].widget.attrs['class'] = 'form-control'


class BulkUserActionForm(forms.Form):
    """Form for bulk user actions"""
    ACTION_CHOICES = (
        ('activate', 'Activate Users'),
        ('deactivate', 'Deactivate Users'),
        ('delete', 'Delete Users'),
        ('export', 'Export Selected'),
    )
    
    action = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    confirm = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        confirm = cleaned_data.get('confirm')
        
        if action == 'delete' and not confirm:
            raise forms.ValidationError('Please confirm you want to delete selected users.')
        
        return cleaned_data

# users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone_number = forms.CharField(max_length=15, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            field.help_text = None