from django.db import models
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone
from users.models import CustomUser
import uuid

class Client(models.Model):
    """Main Client Model"""
    
    # Client Status Choices
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('blacklisted', 'Blacklisted'),
        ('pending', 'Pending Verification'),
    )
    
    RISK_CHOICES = (
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
    )
    
    EMPLOYMENT_CHOICES = (
        ('employed', 'Employed'),
        ('self_employed', 'Self Employed'),
        ('business', 'Business Owner'),
        ('unemployed', 'Unemployed'),
        ('retired', 'Retired'),
    )
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], blank=True, null=True)
    # Personal Information
    client_id = models.CharField(max_length=20, unique=True, editable=False)
    nrc = models.CharField(
        max_length=20, 
        unique=True,
        validators=[RegexValidator(r'^\d{6}/\d{2}/\d$', 'Invalid NRC format. Use: 123456/12/1')],
        help_text="Format: 123456/12/1"
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    
    # Contact Information
    phone_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\+?260\d{9}$|^0\d{9}$', 'Invalid phone number. Use: +260977123456 or 0977123456')]
    )
    alternate_phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    
    # Address Information
    physical_address = models.TextField()
    postal_address = models.CharField(max_length=200, blank=True, null=True)
    city = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='Zambia')
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    # Employment Information
    employment_status = models.CharField(max_length=20, choices=EMPLOYMENT_CHOICES, default='employed')
    employer = models.CharField(max_length=200, blank=True, null=True)
    job_title = models.CharField(max_length=100, blank=True, null=True)
    monthly_income = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    employment_start_date = models.DateField(null=True, blank=True)
    
    # Business Information (for business owners)
    business_name = models.CharField(max_length=200, blank=True, null=True)
    business_type = models.CharField(max_length=100, blank=True, null=True)
    business_registration_number = models.CharField(max_length=50, blank=True, null=True)
    
    # KYC Documents
    nrc_photo = models.ImageField(upload_to='clients/nrc/', help_text="Upload NRC photo")
    client_photo = models.ImageField(upload_to='clients/photos/', help_text="Upload client photo")
    proof_of_residence = models.FileField(upload_to='clients/proof_of_residence/', blank=True, null=True)
    proof_of_income = models.FileField(upload_to='clients/proof_of_income/', blank=True, null=True)
    
    # KYC Status
    kyc_verified = models.BooleanField(default=False)
    kyc_verified_date = models.DateTimeField(null=True, blank=True)
    kyc_verified_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_clients')
    
    # Risk Assessment
    risk_rating = models.CharField(max_length=10, choices=RISK_CHOICES, default='medium')
    credit_score = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(1000)])
    risk_notes = models.TextField(blank=True, null=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    blacklist_reason = models.TextField(blank=True, null=True)
    blacklisted_date = models.DateTimeField(null=True, blank=True)
    
    # Tracking
    registered_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='registered_clients')
    registration_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    last_contact_date = models.DateTimeField(null=True, blank=True)
    
    # Additional Info
    general_notes = models.TextField(blank=True, null=True, help_text="General notes about the client")
    tags = models.CharField(max_length=500, blank=True, null=True, help_text="Comma-separated tags")
    
    class Meta:
        db_table = 'clients'
        ordering = ['-registration_date']
        indexes = [
            models.Index(fields=['nrc']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['first_name', 'last_name']),
            models.Index(fields=['status']),
            models.Index(fields=['risk_rating']),
            models.Index(fields=['registration_date']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.client_id:
            # Generate unique client ID: CLT-YYYY-XXXX
            year = timezone.now().year
            last_client = Client.objects.filter(client_id__startswith=f'CLT-{year}').order_by('-client_id').first()
            if last_client:
                last_num = int(last_client.client_id.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            self.client_id = f'CLT-{year}-{new_num:04d}'
        super().save(*args, **kwargs)
    
    @property
    def full_name(self):
        """Return full name"""
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"
    
    @property
    def short_name(self):
        """Return short name (First Last)"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def initials(self):
        """Return initials"""
        return f"{self.first_name[0]}{self.last_name[0]}".upper()
    
    @property
    def is_active_client(self):
        """Check if client is active"""
        return self.status == 'active'
    
    @property
    def is_blacklisted(self):
        """Check if client is blacklisted"""
        return self.status == 'blacklisted'
    
    def blacklist(self, reason, user):
        """Blacklist the client"""
        self.status = 'blacklisted'
        self.blacklist_reason = reason
        self.blacklisted_date = timezone.now()
        self.save()
    
    def verify_kyc(self, user):
        """Verify KYC documents"""
        self.kyc_verified = True
        self.kyc_verified_date = timezone.now()
        self.kyc_verified_by = user
        self.status = 'active'
        self.save()
    
    def __str__(self):
        return f"{self.client_id} - {self.full_name}"


class Guarantor(models.Model):
    """Guarantor Information"""
    
    RELATIONSHIP_CHOICES = (
        ('parent', 'Parent'),
        ('sibling', 'Sibling'),
        ('spouse', 'Spouse'),
        ('friend', 'Friend'),
        ('colleague', 'Colleague'),
        ('other', 'Other'),
    )
    
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name='guarantor')
    
    # Personal Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    nrc = models.CharField(max_length=20, unique=True)
    
    # Contact
    phone_number = models.CharField(max_length=15)
    alternate_phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    
    # Address
    physical_address = models.TextField()
    city = models.CharField(max_length=100)
    
    # Employment
    employer = models.CharField(max_length=200)
    job_title = models.CharField(max_length=100, blank=True, null=True)
    monthly_income = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Relationship
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    relationship_years = models.IntegerField(default=0)
    
    # Documents
    nrc_photo = models.ImageField(upload_to='guarantors/nrc/')
    photo = models.ImageField(upload_to='guarantors/photos/', blank=True, null=True)
    proof_of_residence = models.FileField(upload_to='guarantors/proof_of_residence/', blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'guarantors'
        indexes = [
            models.Index(fields=['nrc']),
            models.Index(fields=['phone_number']),
        ]
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __str__(self):
        return f"Guarantor: {self.full_name} for {self.client.full_name}"


class ClientAsset(models.Model):
    """Client Assets (for tracking what assets they have)"""
    
    ASSET_TYPES = (
        ('vehicle', 'Vehicle'),
        ('property', 'Property/Land'),
        ('equipment', 'Equipment/Machinery'),
        ('livestock', 'Livestock'),
        ('electronics', 'Electronics'),
        ('jewelry', 'Jewelry'),
        ('business', 'Business'),
        ('other', 'Other'),
    )
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='assets')
    
    # Asset Details
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPES)
    description = models.TextField()
    estimated_value = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Specific fields based on asset type
    make = models.CharField(max_length=100, blank=True, null=True)
    model = models.CharField(max_length=100, blank=True, null=True)
    year = models.IntegerField(null=True, blank=True)
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    
    # Location
    location = models.CharField(max_length=200, blank=True, null=True)
    
    # Documents
    proof_of_ownership = models.FileField(upload_to='client_assets/proof/', blank=True, null=True)
    photos = models.ImageField(upload_to='client_assets/photos/', blank=True, null=True)
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    verification_notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'client_assets'
        ordering = ['-estimated_value']
    
    def __str__(self):
        return f"{self.get_asset_type_display()} - {self.description[:50]}"


class ClientNote(models.Model):
    """Notes and communication log for clients"""
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='notes')
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    note = models.TextField()
    note_type = models.CharField(max_length=50, default='general')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'client_notes'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Note for {self.client.full_name} - {self.created_at.date()}"