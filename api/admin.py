from django.contrib import admin
from .models import Service, Staff, Transaction, ClosingRecord, Expense

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price', 'category', 'icon')
    search_fields = ('name', 'category')
    list_filter = ('category',)

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'role', 'phone', 'active')
    search_fields = ('name', 'phone')
    list_filter = ('role', 'active')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'timestamp', 'client_name', 'grand_total', 'payment_method', 'barber_name', 'massage_therapist_name')
    search_fields = ('client_name', 'id', 'barber_name', 'massage_therapist_name')
    list_filter = ('payment_method', 'barber_tip_paid', 'massage_tip_paid')

@admin.register(ClosingRecord)
class ClosingRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'timestamp', 'total_diff', 'expected_cash', 'actual_cash', 'expected_mpesa', 'actual_mpesa', 'closed_by_staff_name')
    search_fields = ('closed_by_staff_name', 'id')

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('id', 'timestamp', 'title', 'amount', 'category', 'payment_method', 'logged_by_staff_name')
    search_fields = ('title', 'logged_by_staff_name', 'notes')
    list_filter = ('category', 'payment_method')
