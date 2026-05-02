# collateral/management/commands/check_collateral.py
from django.core.management.base import BaseCommand
from collateral.models import Collateral

class Command(BaseCommand):
    help = 'Check collateral status for loan availability'

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*60)
        self.stdout.write("COLLATERAL STATUS CHECK")
        self.stdout.write("="*60)
        
        all_collateral = Collateral.objects.all()
        self.stdout.write(f"\nTotal collateral in system: {all_collateral.count()}")
        
        for coll in all_collateral:
            self.stdout.write(f"\n--- Collateral: {coll.serial_number} ---")
            self.stdout.write(f"  ID: {coll.id}")
            self.stdout.write(f"  Title: {coll.title if hasattr(coll, 'title') else 'N/A'}")
            self.stdout.write(f"  Client: {coll.client.full_name if coll.client else 'NO CLIENT!'}")
            self.stdout.write(f"  Status: {coll.status}")
            self.stdout.write(f"  Is Seized: {coll.is_seized}")
            
            # Check for loan relationship - try different possible field names
            if hasattr(coll, 'loan'):
                self.stdout.write(f"  Loan: {coll.loan.id if coll.loan else 'None'}")
                self.stdout.write(f"  Loan Status: {coll.loan.status if coll.loan else 'N/A'}")
            elif hasattr(coll, 'loans'):
                if coll.loans:
                    loan_info = []
                    for loan in coll.loans.all():
                        loan_info.append(f"#{loan.id} ({loan.status})")
                    self.stdout.write(f"  Loans: {', '.join(loan_info) if loan_info else 'None'}")
                else:
                    self.stdout.write(f"  Loans: None")
            else:
                self.stdout.write(f"  Loan Relationship: Not found")
            
            # Check available fields
            self.stdout.write(f"  Asset Type: {coll.get_asset_type_display() if hasattr(coll, 'get_asset_type_display') else 'N/A'}")
            self.stdout.write(f"  Value: {coll.estimated_value}")
            
            # Determine availability
            is_available = (
                coll.is_seized == False and 
                coll.status in ['available', 'approved']
            )
            self.stdout.write(f"  Available for loan: {is_available}")