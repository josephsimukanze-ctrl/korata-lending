from django.db.models.signals import post_save
from django.dispatch import receiver
from loans.models import Loan, Payment
from clients.models import Client
from .models import Notification

@receiver(post_save, sender=Loan)
def loan_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            user=instance.created_by,
            title='New Loan Application',
            message=f'Loan application #{instance.loan_id} has been submitted for {instance.client.full_name}',
            notification_type='loan',
            link=f'/loans/{instance.id}/'
        )
    
    if instance.status == 'approved' and not kwargs.get('update_fields'):
        Notification.objects.create(
            user=instance.client.registered_by,
            title='Loan Approved',
            message=f'Loan #{instance.loan_id} has been approved for {instance.client.full_name}',
            notification_type='loan',
            link=f'/loans/{instance.id}/'
        )
    
    if instance.status == 'active':
        Notification.objects.create(
            user=instance.client.registered_by,
            title='Loan Activated',
            message=f'Loan #{instance.loan_id} has been activated. First payment due on {instance.expected_end_date}',
            notification_type='loan',
            link=f'/loans/{instance.id}/'
        )

@receiver(post_save, sender=Payment)
def payment_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            user=instance.collected_by,
            title='Payment Received',
            message=f'Payment of ZMW {instance.amount:,.2f} received for loan #{instance.loan.loan_id}',
            notification_type='payment',
            link=f'/loans/{instance.loan.id}/'
        )
        
        # Check if loan is completed
        if instance.loan.remaining_balance <= 0:
            Notification.objects.create(
                user=instance.loan.created_by,
                title='Loan Completed! 🎉',
                message=f'Loan #{instance.loan.loan_id} has been fully paid off!',
                notification_type='alert',
                link=f'/loans/{instance.loan.id}/'
            )