from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from clients.models import Client
from users.models import CustomUser
import uuid
import re

class AssetType(models.Model):
    """Asset type categories"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'asset_types'
        ordering = ['name']
        verbose_name = 'Asset Type'
        verbose_name_plural = 'Asset Types'
    
    def __str__(self):
        return self.name


class Collateral(models.Model):
    """Main Collateral Model for tracking assets"""
    
    # Condition Choices
    CONDITION_CHOICES = (
        ('new', '🆕 New'),
        ('excellent', '⭐ Excellent'),
        ('very_good', '✅ Very Good'),
        ('good', '👍 Good'),
        ('fair', '⚠️ Fair'),
        ('poor', '🔻 Poor'),
        ('damaged', '💔 Damaged'),
    )
    
    # Status Choices
    STATUS_CHOICES = (
        ('available', '🟢 Available'),
        ('pledged', '🔵 Pledged'),
        ('seized', '🔴 Seized'),
        ('sold', '💸 Sold'),
        ('released', '⬜ Released'),
        ('pending', '🟡 Pending Review'),
        ('assigned', 'Assigned'),
    )
    
    # Verification Choices
    VERIFICATION_CHOICES = (
        ('pending', '⏳ Pending'),
        ('verified', '✅ Verified'),
        ('rejected', '❌ Rejected'),
        ('requires_review', '⚠️ Requires Review'),
    )
    
    # Ownership Type
    OWNERSHIP_CHOICES = (
        ('owned', 'Fully Owned'),
        ('financed', 'Financed'),
        ('leased', 'Leased'),
        ('joint', 'Joint Ownership'),
    )
    ASSET_TYPES = [
        ('vehicle', 'Vehicle'),
        ('property', 'Property'),
        ('equipment', 'Equipment'),
        ('jewelry', 'Jewelry'),
        ('electronics', 'Electronics'),
        ('livestock', 'Livestock'),
        ('crops', 'Crops'),
        ('machinery', 'Machinery'),
        ('other', 'Other'),
    ]
    
    # Then use it in your field
    asset_type = models.CharField(max_length=50, choices=ASSET_TYPES, default='other')
    # Basic Information
    collateral_id = models.CharField(max_length=20, unique=True, editable=False, null=True)
    client = models.ForeignKey(
        Client, 
        on_delete=models.CASCADE, 
        related_name='collaterals',
        verbose_name='Client'
    )
    asset_type = models.ForeignKey(
        AssetType, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='collaterals',
        verbose_name='Asset Type'
    )
    
    # Asset Details
    title = models.CharField(max_length=200, verbose_name='Asset Title')
    description = models.TextField(verbose_name='Description')
    make = models.CharField(max_length=100, blank=True, null=True, verbose_name='Make/Brand')
    model = models.CharField(max_length=100, blank=True, null=True, verbose_name='Model')
    year = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1900), MaxValueValidator(timezone.now().year)],
        verbose_name='Year'
    )
    color = models.CharField(max_length=50, blank=True, null=True, verbose_name='Color')
    serial_number = models.CharField(
        max_length=100, 
        unique=True,
        validators=[RegexValidator(r'^[A-Za-z0-9\-_]+$', 'Only alphanumeric characters, hyphens and underscores allowed')],
        verbose_name='Serial Number'
    )
    
    # Ownership
    ownership_type = models.CharField(
        max_length=20, 
        choices=OWNERSHIP_CHOICES, 
        default='owned',
        verbose_name='Ownership Type'
    )
    ownership_proof = models.FileField(
        upload_to='collateral/ownership_proof/', 
        blank=True, 
        null=True,
        verbose_name='Proof of Ownership'
    )
    
    # Condition and Valuation
    condition = models.CharField(
        max_length=20, 
        choices=CONDITION_CHOICES, 
        default='good',
        verbose_name='Condition'
    )
    estimated_value = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[MinValueValidator(0)],
        verbose_name='Estimated Value (ZMW)'
    )
    appraised_value = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name='Appraised Value (ZMW)'
    )
    loan_to_value_ratio = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=70,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Percentage of value that can be lent",
        verbose_name='LTV Ratio (%)'
    )
    
    # Location and Storage
    storage_location = models.CharField(max_length=200, verbose_name='Storage Location')
    storage_section = models.CharField(max_length=100, blank=True, null=True, verbose_name='Section')
    storage_shelf = models.CharField(max_length=50, blank=True, null=True, verbose_name='Shelf/Rack')
    storage_condition = models.TextField(blank=True, null=True, verbose_name='Storage Conditions')
    
    # Documents and Photos
    primary_photo = models.ImageField(
        upload_to='collateral/photos/', 
        blank=True, 
        null=True,
        verbose_name='Primary Photo'
    )
    additional_photos = models.ImageField(
        upload_to='collateral/additional_photos/', 
        blank=True, 
        null=True,
        verbose_name='Additional Photos'
    )
    certificate_of_ownership = models.FileField(
        upload_to='collateral/certificates/', 
        blank=True, 
        null=True,
        verbose_name='Certificate of Ownership'
    )
    valuation_certificate = models.FileField(
        upload_to='collateral/valuations/', 
        blank=True, 
        null=True,
        verbose_name='Valuation Certificate'
    )
    insurance_certificate = models.FileField(
        upload_to='collateral/insurance/', 
        blank=True, 
        null=True,
        verbose_name='Insurance Certificate'
    )
    
    # QR Code for tracking
    qr_code = models.ImageField(
        upload_to='collateral/qrcodes/', 
        blank=True, 
        null=True,
        verbose_name='QR Code'
    )
    
    # Verification
    verification_status = models.CharField(
        max_length=20, 
        choices=VERIFICATION_CHOICES, 
        default='pending',
        verbose_name='Verification Status'
    )
    verified_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='verified_collaterals',
        verbose_name='Verified By'
    )
    verification_date = models.DateTimeField(null=True, blank=True, verbose_name='Verification Date')
    verification_notes = models.TextField(blank=True, null=True, verbose_name='Verification Notes')
    
    # Insurance
    is_insured = models.BooleanField(default=False, verbose_name='Is Insured?')
    insurance_provider = models.CharField(max_length=200, blank=True, null=True, verbose_name='Insurance Provider')
    insurance_policy_number = models.CharField(max_length=100, blank=True, null=True, verbose_name='Policy Number')
    insurance_expiry_date = models.DateField(null=True, blank=True, verbose_name='Insurance Expiry Date')
    insurance_value = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name='Insured Value (ZMW)'
    )
    
    # Status Tracking
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='available',
        verbose_name='Status'
    )
    is_seized = models.BooleanField(default=False, verbose_name='Is Seized?')
    seized_date = models.DateTimeField(null=True, blank=True, verbose_name='Seized Date')
    seized_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='seized_collaterals',
        verbose_name='Seized By'
    )
    release_date = models.DateTimeField(null=True, blank=True, verbose_name='Release Date')
    
    # Loan Association
    current_loan = models.ForeignKey(
        'loans.Loan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='collaterals',
        verbose_name='Associated Loan'
    )
    
    # Tracking
    created_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_collaterals',
        verbose_name='Created By'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    last_physical_check = models.DateField(null=True, blank=True, verbose_name='Last Physical Check')
    next_physical_check = models.DateField(null=True, blank=True, verbose_name='Next Physical Check')
    
    # Additional Info
    notes = models.TextField(blank=True, null=True, verbose_name='Additional Notes')
    tags = models.CharField(
        max_length=500, 
        blank=True, 
        null=True, 
        help_text="Comma-separated tags for easy searching",
        verbose_name='Tags'
    )
    
    class Meta:
        db_table = 'collateral'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['collateral_id']),
            models.Index(fields=['serial_number']),
            models.Index(fields=['client', 'status']),
            models.Index(fields=['verification_status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['asset_type']),
            models.Index(fields=['condition']),
        ]
        verbose_name = 'Collateral'
        verbose_name_plural = 'Collaterals'
    
    def clean(self):
        """Custom validation"""
        if self.estimated_value < 0:
            raise ValidationError({'estimated_value': 'Estimated value cannot be negative'})
        
        if self.appraised_value and self.appraised_value < 0:
            raise ValidationError({'appraised_value': 'Appraised value cannot be negative'})
        
        if self.loan_to_value_ratio < 0 or self.loan_to_value_ratio > 100:
            raise ValidationError({'loan_to_value_ratio': 'LTV ratio must be between 0 and 100'})
        
        if self.insurance_expiry_date and self.insurance_expiry_date < timezone.now().date():
            raise ValidationError({'insurance_expiry_date': 'Insurance expiry date cannot be in the past'})
    
    def save(self, *args, **kwargs):
        if not self.collateral_id:
            year = timezone.now().year
            last_collateral = Collateral.objects.filter(
                collateral_id__startswith=f'COL-{year}'
            ).order_by('-collateral_id').first()
            
            if last_collateral and last_collateral.collateral_id:
                try:
                    last_num = int(last_collateral.collateral_id.split('-')[-1])
                    new_num = last_num + 1
                except (ValueError, IndexError):
                    new_num = 1
            else:
                new_num = 1
            
            self.collateral_id = f'COL-{year}-{new_num:04d}'
        
        # Set next physical check date if not set
        if not self.next_physical_check and self.last_physical_check:
            from datetime import timedelta
            self.next_physical_check = self.last_physical_check + timedelta(days=90)
        
        # Generate QR code if not exists
        if not self.qr_code:
            self.generate_qr_code()
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    def generate_qr_code(self):
        """Generate QR code for the collateral"""
        try:
            import qrcode
            from io import BytesIO
            from django.core.files import File
            
            qr_data = f"""
            Collateral ID: {self.collateral_id}
            Serial: {self.serial_number}
            Client: {self.client.full_name}
            Value: ZMW {self.estimated_value:,.2f}
            Status: {self.get_status_display()}
            """
            
            qr = qrcode.QRCode(
                version=1,
                box_size=10,
                border=5,
                error_correction=qrcode.constants.ERROR_CORRECT_M
            )
            qr.add_data(qr_data.strip())
            qr.make(fit=True)
            
            qr_image = qr.make_image(fill_color='#1e3a8a', back_color='white')
            
            buffer = BytesIO()
            qr_image.save(buffer, 'PNG', quality=95)
            self.qr_code.save(f'qr_{self.collateral_id}.png', File(buffer), save=False)
        except ImportError:
            pass
        except Exception as e:
            print(f"QR Code generation failed: {e}")
    
    def get_asset_type_display(self):
        """Get display name for asset type"""
        # Since asset_type is a ForeignKey to AssetType, return the name
        if self.asset_type:
            return self.asset_type.name
        return 'Asset'
    
    # DO NOT override get_condition_display - Django provides it automatically!
    # DO NOT override get_status_display - Django provides it automatically!
    
    def verify(self, user, notes=None):
        """Verify the collateral"""
        self.verification_status = 'verified'
        self.verified_by = user
        self.verification_date = timezone.now()
        self.verification_notes = notes
        self.status = 'available'
        self.save()
    
    def reject_verification(self, user, reason=None):
        """Reject collateral verification"""
        self.verification_status = 'rejected'
        self.verified_by = user
        self.verification_date = timezone.now()
        self.verification_notes = reason
        self.save()
    
    def seize(self, user, reason=None):
        """Seize the collateral"""
        self.status = 'seized'
        self.is_seized = True
        self.seized_date = timezone.now()
        self.seized_by = user
        if reason:
            self.notes = reason
        self.save()
    
    def release(self, user=None):
        """Release the collateral"""
        self.status = 'available'
        self.is_seized = False
        self.release_date = timezone.now()
        if user:
            self.notes = f"Released by {user.username} on {timezone.now()}"
        self.save()
    
    def mark_as_sold(self, sale_price, buyer_info=None):
        """Mark collateral as sold"""
        self.status = 'sold'
        self.sale_price = sale_price
        self.sale_date = timezone.now()
        self.sale_buyer_info = buyer_info
        self.save()
    
    @property
    def get_condition_display_name(self):
        """Get condition display name with emoji"""
        conditions = {
            'new': '🆕 New',
            'excellent': '⭐ Excellent',
            'very_good': '✅ Very Good',
            'good': '👍 Good',
            'fair': '⚠️ Fair',
            'poor': '🔻 Poor',
            'damaged': '💔 Damaged'
        }
        return conditions.get(self.condition, self.condition.capitalize())
    
    @property
    def get_status_display_name(self):
        """Get status display name with emoji"""
        statuses = {
            'available': '🟢 Available',
            'pledged': '🔵 Pledged',
            'seized': '🔴 Seized',
            'sold': '💸 Sold',
            'released': '⬜ Released',
            'pending': '🟡 Pending Review',
            'assigned': 'Assigned'
        }
        return statuses.get(self.status, self.status.capitalize())
    
    @property
    def get_max_loan_amount(self):
        """Calculate maximum loan amount based on LTV ratio"""
        return self.estimated_value * (self.loan_to_value_ratio / 100)
    
    @property
    def is_insurance_valid(self):
        """Check if insurance is valid"""
        if not self.is_insured or not self.insurance_expiry_date:
            return False
        return self.insurance_expiry_date >= timezone.now().date()
    
    @property
    def age_in_days(self):
        """Calculate age of collateral record in days"""
        return (timezone.now() - self.created_at).days
    
    @property
    def days_since_last_check(self):
        """Calculate days since last physical check"""
        if not self.last_physical_check:
            return None
        return (timezone.now().date() - self.last_physical_check).days
    
    def __str__(self):
        return f"{self.collateral_id} - {self.title} - {self.client.full_name}"


class CollateralInspection(models.Model):
    """Regular inspections of collateral"""
    
    INSPECTION_TYPE_CHOICES = (
        ('initial', '📋 Initial'),
        ('quarterly', '📅 Quarterly'),
        ('annual', '📆 Annual'),
        ('special', '🔍 Special'),
        ('release', '✅ Pre-release'),
        ('random', '🎲 Random'),
    )
    
    collateral = models.ForeignKey(
        Collateral, 
        on_delete=models.CASCADE, 
        related_name='inspections',
        verbose_name='Collateral'
    )
    inspection_type = models.CharField(
        max_length=20, 
        choices=INSPECTION_TYPE_CHOICES,
        verbose_name='Inspection Type'
    )
    inspection_date = models.DateField(default=timezone.now, verbose_name='Inspection Date')
    inspected_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name='Inspected By'
    )
    
    # Findings
    condition = models.CharField(
        max_length=20, 
        choices=Collateral.CONDITION_CHOICES,
        verbose_name='Condition Found'
    )
    notes = models.TextField(verbose_name='Inspection Notes')
    photos = models.ImageField(
        upload_to='collateral/inspections/', 
        blank=True, 
        null=True,
        verbose_name='Inspection Photos'
    )
    
    # Recommendations
    recommendation = models.TextField(blank=True, null=True, verbose_name='Recommendations')
    requires_action = models.BooleanField(default=False, verbose_name='Requires Action')
    action_taken = models.BooleanField(default=False, verbose_name='Action Taken')
    action_notes = models.TextField(blank=True, null=True, verbose_name='Action Notes')
    
    # Follow-up
    next_inspection_date = models.DateField(null=True, blank=True, verbose_name='Next Inspection Date')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'collateral_inspections'
        ordering = ['-inspection_date']
        indexes = [
            models.Index(fields=['collateral', '-inspection_date']),
            models.Index(fields=['inspection_type']),
        ]
        verbose_name = 'Collateral Inspection'
        verbose_name_plural = 'Collateral Inspections'
    
    def __str__(self):
        return f"Inspection of {self.collateral.collateral_id} - {self.inspection_date}"


class CollateralMovement(models.Model):
    """Track collateral movements and transfers"""
    
    MOVEMENT_TYPE_CHOICES = (
        ('received', '📥 Received'),
        ('moved', '🚚 Moved'),
        ('released', '📤 Released'),
        ('seized', '🔒 Seized'),
        ('sold', '💸 Sold'),
        ('transferred', '🔄 Transferred'),
        ('returned', '↩️ Returned'),
    )
    
    collateral = models.ForeignKey(
        Collateral, 
        on_delete=models.CASCADE, 
        related_name='movements',
        verbose_name='Collateral'
    )
    movement_type = models.CharField(
        max_length=20, 
        choices=MOVEMENT_TYPE_CHOICES,
        verbose_name='Movement Type'
    )
    from_location = models.CharField(max_length=200, blank=True, null=True, verbose_name='From Location')
    to_location = models.CharField(max_length=200, verbose_name='To Location')
    reason = models.TextField(verbose_name='Reason for Movement')
    moved_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name='Moved By'
    )
    movement_date = models.DateTimeField(auto_now_add=True, verbose_name='Movement Date')
    notes = models.TextField(blank=True, null=True, verbose_name='Additional Notes')
    
    # Authorization
    authorized_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='authorized_movements',
        verbose_name='Authorized By'
    )
    authorization_date = models.DateTimeField(null=True, blank=True, verbose_name='Authorization Date')
    
    class Meta:
        db_table = 'collateral_movements'
        ordering = ['-movement_date']
        indexes = [
            models.Index(fields=['collateral', '-movement_date']),
            models.Index(fields=['movement_type']),
            models.Index(fields=['movement_date']),
        ]
        verbose_name = 'Collateral Movement'
        verbose_name_plural = 'Collateral Movements'
    
    def __str__(self):
        return f"{self.collateral.collateral_id} - {self.movement_type} - {self.movement_date}"
    

