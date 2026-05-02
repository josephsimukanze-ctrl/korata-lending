# users/permissions.py

def is_ceo_or_admin(user):
    """Check if user is CEO or Admin"""
    return user.is_superuser or (hasattr(user, 'role') and user.role in ['ceo', 'admin'])

def is_loan_officer(user):
    """Check if user is Loan Officer"""
    return user.is_superuser or (hasattr(user, 'role') and user.role in ['ceo', 'admin', 'loan_officer'])

def is_collateral_officer(user):
    """Check if user is Collateral Officer"""
    return user.is_superuser or (hasattr(user, 'role') and user.role in ['ceo', 'admin', 'collateral_officer'])

def is_accountant(user):
    """Check if user is Accountant"""
    return user.is_superuser or (hasattr(user, 'role') and user.role in ['ceo', 'admin', 'accountant'])

def is_auditor(user):
    """Check if user is Auditor"""
    return user.is_superuser or (hasattr(user, 'role') and user.role in ['ceo', 'admin', 'auditor'])

def can_view_clients(user):
    """Check if user can view clients"""
    return user.is_superuser or (hasattr(user, 'role') and user.role in ['ceo', 'admin', 'loan_officer', 'collateral_officer'])

def can_manage_collateral(user):
    """Check if user can manage collateral"""
    return user.is_superuser or (hasattr(user, 'role') and user.role in ['ceo', 'admin', 'collateral_officer'])

def can_manage_insurance(user):
    """Check if user can manage insurance"""
    return user.is_superuser or (hasattr(user, 'role') and user.role in ['ceo', 'admin', 'collateral_officer'])
# Add this at the very end of the file to ensure all functions are properly closed
def placeholder_function(request):
    """Placeholder function to avoid indentation errors"""
    pass