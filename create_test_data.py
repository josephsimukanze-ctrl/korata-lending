#!/usr/bin/env python
import os
import django
import random
from datetime import datetime, timedelta

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import CustomUser
from clients.models import Client
from loans.models import Loan, Payment
from collateral.models import Collateral

def create_test_data():
    print("Creating test data...")
    
    # Create admin user if not exists
    admin, created = CustomUser.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@korata.com',
            'first_name': 'Admin',
            'last_name': 'User',
            'is_staff': True,
            'is_superuser': True,
            'role': 'ceo'
        }
    )
    if created:
        admin.set_password('admin123')
        admin.save()
        print("✓ Admin user created (password: admin123)")
    else:
        print("✓ Admin user already exists")
    
    # Create clients
    clients_data = [
        {'first_name': 'John', 'last_name': 'Doe', 'nrc': '123456/12/1', 'phone': '+260977123456', 'city': 'Lusaka'},
        {'first_name': 'Sarah', 'last_name': 'Banda', 'nrc': '123457/12/1', 'phone': '+260977123457', 'city': 'Lusaka'},
        {'first_name': 'Michael', 'last_name': 'Phiri', 'nrc': '123458/12/1', 'phone': '+260977123458', 'city': 'Kitwe'},
        {'first_name': 'Grace', 'last_name': 'Mulenga', 'nrc': '123459/12/1', 'phone': '+260977123459', 'city': 'Ndola'},
        {'first_name': 'Peter', 'last_name': 'Mwanza', 'nrc': '123460/12/1', 'phone': '+260977123460', 'city': 'Lusaka'},
        {'first_name': 'Alice', 'last_name': 'Chanda', 'nrc': '123461/12/1', 'phone': '+260977123461', 'city': 'Livingstone'},
        {'first_name': 'James', 'last_name': 'Zulu', 'nrc': '123462/12/1', 'phone': '+260977123462', 'city': 'Chipata'},
        {'first_name': 'Mary', 'last_name': 'Mwila', 'nrc': '123463/12/1', 'phone': '+260977123463', 'city': 'Kabwe'},
        {'first_name': 'David', 'last_name': 'Tembo', 'nrc': '123464/12/1', 'phone': '+260977123464', 'city': 'Mufulira'},
        {'first_name': 'Elizabeth', 'last_name': 'Kasonde', 'nrc': '123465/12/1', 'phone': '+260977123465', 'city': 'Lusaka'},
    ]
    
    created_clients = []
    for client_data in clients_data:
        client, created = Client.objects.get_or_create(
            nrc=client_data['nrc'],
            defaults={
                'first_name': client_data['first_name'],
                'last_name': client_data['last_name'],
                'phone_number': client_data['phone'],
                'physical_address': f"{client_data['city']} Main Road",
                'city': client_data['city'],
                'district': client_data['city'],
                'province': 'Lusaka' if client_data['city'] == 'Lusaka' else 'Copperbelt',
                'country': 'Zambia',
                'employment_status': 'employed',
                'monthly_income': random.randint(3000, 15000),
                'status': 'active',
                'kyc_verified': True,
                'registered_by': admin
            }
        )
        if created:
            created_clients.append(client)
            print(f"✓ Client created: {client.full_name}")
    
    print(f"✓ Total clients: {Client.objects.count()}")
    
    # Create loans for clients
    loan_statuses = ['active', 'active', 'active', 'completed', 'pending', 'approved']
    created_loans = []
    
    for client in Client.objects.all():
        # Create 1-2 loans per client
        num_loans = random.randint(1, 2)
        for i in range(num_loans):
            principal = random.randint(5000, 50000)
            interest_rate = random.choice([8, 10, 12, 15])
            duration_weeks = random.choice([8, 12, 16, 24, 36])
            status = random.choice(loan_statuses)
            
            loan = Loan.objects.create(
                client=client,
                principal=principal,
                interest_rate=interest_rate,
                interest_period='week',
                duration_weeks=duration_weeks,
                status=status,
                purpose=f"Business expansion - {client.first_name}'s project",
                created_by=admin
            )
            loan.calculate_loan()
            loan.save()
            created_loans.append(loan)
            print(f"✓ Loan created: {loan.loan_id} - ZMW {principal} ({status})")
    
    print(f"✓ Total loans: {Loan.objects.count()}")
    
    # Create payments for active loans
    payment_methods = ['cash', 'mobile_money', 'bank_transfer']
    created_payments = []
    
    for loan in Loan.objects.filter(status__in=['active', 'completed']):
        # Create 2-5 payments per loan
        num_payments = random.randint(2, 5)
        for i in range(num_payments):
            amount = random.randint(500, 3000)
            payment_date = datetime.now() - timedelta(days=random.randint(1, 30))
            
            payment = Payment.objects.create(
                loan=loan,
                amount=amount,
                payment_method=random.choice(payment_methods),
                reference_number=f"TXN-{random.randint(10000, 99999)}",
                collected_by=admin,
                payment_date=payment_date
            )
            created_payments.append(payment)
    
    print(f"✓ Total payments: {Payment.objects.count()}")
    
    # Summary
    print("\n" + "="*50)
    print("TEST DATA SUMMARY")
    print("="*50)
    print(f"📊 Users: {CustomUser.objects.count()}")
    print(f"👥 Clients: {Client.objects.count()}")
    print(f"💰 Loans: {Loan.objects.count()}")
    print(f"   - Active: {Loan.objects.filter(status='active').count()}")
    print(f"   - Completed: {Loan.objects.filter(status='completed').count()}")
    print(f"   - Pending: {Loan.objects.filter(status='pending').count()}")
    print(f"💵 Payments: {Payment.objects.count()}")
    print(f"💸 Total Disbursed: ZMW {Loan.objects.aggregate(total=Sum('principal'))['total']:,.2f}")
    print(f"💳 Total Repaid: ZMW {Payment.objects.aggregate(total=Sum('amount'))['total']:,.2f}")
    print("="*50)
    print("\n✓ Test data creation complete!")
    print("\nLogin with:")
    print("  Username: admin")
    print("  Password: admin123")

if __name__ == '__main__':
    create_test_data()