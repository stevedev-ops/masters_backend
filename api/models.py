import time
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

def generate_service_id():
    return f'srv-{int(time.time() * 1000)}'

def generate_staff_id():
    return f'stf-{int(time.time() * 1000)}'

def generate_transaction_id():
    return f'tx-{int(time.time() * 1000)}'

def generate_closing_id():
    return f'close-{int(time.time() * 1000)}'

def generate_expense_id():
    return f'exp-{int(time.time() * 1000)}'

def generate_appointment_id():
    return f'apt-{int(time.time() * 1000)}'

class Service(models.Model):
    id = models.CharField(max_length=50, primary_key=True, default=generate_service_id)
    name = models.CharField(max_length=120)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=100, default='Barber')
    icon = models.CharField(max_length=50, default='Scissors', blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} (KSh {self.price})'

class Staff(models.Model):
    ROLE_CHOICES = [
        ('Barber', 'Barber'),
        ('Massage Therapist', 'Massage Therapist'),
        ('Dual', 'Dual'),
        ('Boss', 'Boss'),
    ]

    id = models.CharField(max_length=50, primary_key=True, default=generate_staff_id)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_profile')
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='Barber')
    phone = models.CharField(max_length=50, blank=True)
    title = models.CharField(max_length=120, blank=True)
    active = models.BooleanField(default=True)
    must_change_password = models.BooleanField(default=True, help_text='Requires user to change password on next login')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} - {self.role}'

class Transaction(models.Model):
    PAYMENT_CHOICES = [
        ('M-Pesa', 'M-Pesa'),
        ('Cash', 'Cash'),
        ('Card', 'Card'),
    ]

    id = models.CharField(max_length=50, primary_key=True, default=generate_transaction_id)
    timestamp = models.DateTimeField(default=timezone.now)
    client_name = models.CharField(max_length=120, blank=True, default='Walk-in Client')
    services = models.JSONField(default=list, help_text='Snapshot of services selected for this visit')
    
    logged_by_staff_id = models.CharField(max_length=50, blank=True, null=True)
    logged_by_staff_name = models.CharField(max_length=120, blank=True, null=True)

    barber_id = models.CharField(max_length=50, blank=True, null=True)
    barber_name = models.CharField(max_length=120, blank=True, null=True)

    massage_therapist_id = models.CharField(max_length=50, blank=True, null=True)
    massage_therapist_name = models.CharField(max_length=120, blank=True, null=True)

    service_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    barber_tip = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    massage_tip = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    payment_method = models.CharField(max_length=50, choices=PAYMENT_CHOICES, default='M-Pesa')
    barber_tip_paid = models.BooleanField(default=False)
    massage_tip_paid = models.BooleanField(default=False)
    barber_commission_paid = models.BooleanField(default=False)
    massage_commission_paid = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.id} | {self.client_name} - {self.grand_total}'

class ClosingRecord(models.Model):
    id = models.CharField(max_length=50, primary_key=True, default=generate_closing_id)
    timestamp = models.DateTimeField(default=timezone.now)
    
    expected_cash = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    actual_cash = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cash_diff = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    expected_mpesa = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    actual_mpesa = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    mpesa_diff = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    total_diff = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    closed_by_staff_id = models.CharField(max_length=50, blank=True, null=True)
    closed_by_staff_name = models.CharField(max_length=120, blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.id} | Net Diff: {self.total_diff}'

class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('Shop Supplies', 'Shop Supplies'),
        ('Laundry & Cleaning', 'Laundry & Cleaning'),
        ('Utilities / Power', 'Utilities / Power'),
        ('Refreshments', 'Refreshments'),
        ('Equipment / Maintenance', 'Equipment / Maintenance'),
        ('Other', 'Other'),
    ]

    PAYMENT_CHOICES = [
        ('Cash', 'Cash'),
        ('M-Pesa', 'M-Pesa'),
        ('Both', 'Both'),
    ]

    id = models.CharField(max_length=50, primary_key=True, default=generate_expense_id)
    timestamp = models.DateTimeField(default=timezone.now)
    title = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Shop Supplies')
    payment_method = models.CharField(max_length=50, choices=PAYMENT_CHOICES, default='Cash')
    
    logged_by_staff_id = models.CharField(max_length=50, blank=True, null=True)
    logged_by_staff_name = models.CharField(max_length=120, blank=True, null=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.title} - KSh {self.amount} ({self.payment_method})'

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.CharField(max_length=50, primary_key=True, default=generate_appointment_id)
    created_at = models.DateTimeField(default=timezone.now)
    client_name = models.CharField(max_length=120)
    client_phone = models.CharField(max_length=40)
    service_id = models.CharField(max_length=50, blank=True, null=True)
    service_name = models.CharField(max_length=120)
    service_category = models.CharField(max_length=60, blank=True, default='')
    service_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    preferred_date = models.CharField(max_length=40, blank=True, default='')
    
    # Staff routing
    preferred_staff_id = models.CharField(max_length=50, blank=True, null=True)
    preferred_staff_name = models.CharField(max_length=120, blank=True, null=True)
    assigned_staff_id = models.CharField(max_length=50, blank=True, null=True)
    assigned_staff_name = models.CharField(max_length=120, blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.client_name} - {self.service_name} ({self.status})'
