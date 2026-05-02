from django.db import models
from django.utils import timezone
from decimal import Decimal
from clients.models import Client
from loans.models import Loan
from collateral.models import Collateral
from users.models import CustomUser

class Auction(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('scheduled', 'Scheduled'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    # Basic Information
    auction_id = models.CharField(max_length=20, unique=True, editable=False)
    loan = models.OneToOneField(Loan, on_delete=models.CASCADE, related_name='auction')
    collateral = models.ForeignKey(Collateral, on_delete=models.CASCADE, related_name='auctions')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='auctions')
    
    # Auction Details
    title = models.CharField(max_length=200)
    description = models.TextField()
    starting_bid = models.DecimalField(max_digits=12, decimal_places=2)
    reserve_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    current_bid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bid_increment = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    
    # Dates
    scheduled_date = models.DateTimeField()
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    actual_end_date = models.DateTimeField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Financials
    final_sale_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    loan_balance_at_auction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    surplus_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    deficit_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Fees
    auction_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    storage_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    legal_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Winner Information
    winner_name = models.CharField(max_length=200, blank=True, null=True)
    winner_contact = models.CharField(max_length=50, blank=True, null=True)
    winner_email = models.EmailField(blank=True, null=True)
    
    # Tracking
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_auctions')
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_auctions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Documents
    legal_notice = models.FileField(upload_to='auction/legal_notices/', blank=True, null=True)
    auction_certificate = models.FileField(upload_to='auction/certificates/', blank=True, null=True)
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'auctions'
        ordering = ['-scheduled_date']
        indexes = [
            models.Index(fields=['auction_id']),
            models.Index(fields=['status']),
            models.Index(fields=['scheduled_date']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.auction_id:
            year = timezone.now().year
            last_auction = Auction.objects.filter(auction_id__startswith=f'AUC-{year}').order_by('-auction_id').first()
            if last_auction:
                last_num = int(last_auction.auction_id.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            self.auction_id = f'AUC-{year}-{new_num:04d}'
        super().save(*args, **kwargs)
    
    def start_auction(self):
        """Start the auction"""
        self.status = 'active'
        self.start_date = timezone.now()
        self.save()
    
    def end_auction(self, final_price, winner_name, winner_contact):
        """End the auction with a winner"""
        self.status = 'completed'
        self.actual_end_date = timezone.now()
        self.final_sale_price = final_price
        self.winner_name = winner_name
        self.winner_contact = winner_contact
        
        # Calculate surplus or deficit
        if final_price > self.loan_balance_at_auction:
            self.surplus_amount = final_price - self.loan_balance_at_auction
            self.deficit_amount = 0
        else:
            self.surplus_amount = 0
            self.deficit_amount = self.loan_balance_at_auction - final_price
        
        self.save()
        
        # Update collateral as seized and sold
        self.collateral.is_seized = True
        self.collateral.seized_date = timezone.now()
        self.collateral.save()
        
        # Update loan status to defaulted
        self.loan.status = 'defaulted'
        self.loan.save()
    
    def cancel_auction(self, reason):
        """Cancel the auction"""
        self.status = 'cancelled'
        self.notes = reason
        self.save()
    
    @property
    def is_active(self):
        return self.status == 'active'
    
    @property
    def is_completed(self):
        return self.status == 'completed'
    
    def __str__(self):
        return f"{self.auction_id} - {self.collateral.serial_number}"


class AuctionBid(models.Model):
    """Bids placed on auctions"""
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='bids')
    bidder_name = models.CharField(max_length=200)
    bidder_contact = models.CharField(max_length=50)
    bidder_email = models.EmailField(blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    bid_time = models.DateTimeField(auto_now_add=True)
    is_winning_bid = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'auction_bids'
        ordering = ['-amount', '-bid_time']
    
    def __str__(self):
        return f"{self.bidder_name} - ZMW {self.amount}"


class DefaultNotice(models.Model):
    """Legal notices sent to clients before auction"""
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='default_notices')
    notice_number = models.CharField(max_length=50, unique=True, editable=False)
    days_overdue = models.IntegerField()
    notice_date = models.DateField(auto_now_add=True)
    response_deadline = models.DateField()
    is_responded = models.BooleanField(default=False)
    response_notes = models.TextField(blank=True, null=True)
    legal_action_taken = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'default_notices'
        ordering = ['-notice_date']
    
    def save(self, *args, **kwargs):
        if not self.notice_number:
            import uuid
            self.notice_number = f"DN-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Notice {self.notice_number} - Loan {self.loan.loan_id}"