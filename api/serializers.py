import re
from rest_framework import serializers
from .models import Service, Staff, Transaction, ClosingRecord, Expense, Appointment

def sanitize_text(value):
    """
    Strips script tags, executable javascript, and dangerous HTML tags
    to ensure no executable script can be stored in the database or rendered unescaped.
    """
    if not isinstance(value, str):
        return value
    # Remove <script ...>...</script>
    cleaned = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', value, flags=re.IGNORECASE)
    # Remove javascript: pseudo-protocol
    cleaned = re.sub(r'javascript:[^\s\'"]*', '', cleaned, flags=re.IGNORECASE)
    # Remove dangerous tags like <iframe>, <object>, <embed>, <applet>
    cleaned = re.sub(r'<\/?(iframe|object|embed|applet|meta|link|style)[^>]*>', '', cleaned, flags=re.IGNORECASE)
    # Remove inline event handlers (onerror=, onload=, onclick=, etc.)
    cleaned = re.sub(r'\bon\w+\s*=\s*(?:".*?"|\'.*?\'|[^\s>]+)', '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

class SanitizedCharField(serializers.CharField):
    def to_internal_value(self, data):
        val = super().to_internal_value(data)
        return sanitize_text(val)

class ServiceSerializer(serializers.ModelSerializer):
    name = SanitizedCharField(max_length=120)
    price = serializers.FloatField(min_value=0.0)
    category = SanitizedCharField(max_length=100)
    description = SanitizedCharField(required=False, allow_blank=True)

    class Meta:
        model = Service
        fields = ['id', 'name', 'price', 'category', 'icon', 'description']

class StaffSerializer(serializers.ModelSerializer):
    name = SanitizedCharField(max_length=120)
    phone = SanitizedCharField(required=False, allow_blank=True)
    title = SanitizedCharField(required=False, allow_blank=True)
    username = serializers.CharField(source='user.username', read_only=True)
    mustChangePassword = serializers.BooleanField(source='must_change_password', read_only=True)

    class Meta:
        model = Staff
        fields = ['id', 'name', 'role', 'phone', 'title', 'active', 'username', 'mustChangePassword']

class TransactionSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, max_length=50)
    clientName = SanitizedCharField(source='client_name', required=False, allow_blank=True)
    loggedByStaffId = serializers.CharField(source='logged_by_staff_id', required=False, allow_null=True)
    loggedByStaffName = serializers.CharField(source='logged_by_staff_name', required=False, allow_null=True)
    barberId = serializers.CharField(source='barber_id', required=False, allow_null=True)
    barberName = serializers.CharField(source='barber_name', required=False, allow_null=True)
    massageTherapistId = serializers.CharField(source='massage_therapist_id', required=False, allow_null=True)
    massageTherapistName = serializers.CharField(source='massage_therapist_name', required=False, allow_null=True)
    
    # Financial fields: must be non-negative
    serviceTotal = serializers.FloatField(source='service_total', required=False, min_value=0.0)
    barberTip = serializers.FloatField(source='barber_tip', required=False, min_value=0.0)
    massageTip = serializers.FloatField(source='massage_tip', required=False, min_value=0.0)
    grandTotal = serializers.FloatField(source='grand_total', required=False, min_value=0.0)
    
    paymentMethod = serializers.CharField(source='payment_method', required=False)
    barberTipPaid = serializers.BooleanField(source='barber_tip_paid', required=False)
    massageTipPaid = serializers.BooleanField(source='massage_tip_paid', required=False)
    barberCommissionPaid = serializers.BooleanField(source='barber_commission_paid', required=False)
    massageCommissionPaid = serializers.BooleanField(source='massage_commission_paid', required=False)
    notes = SanitizedCharField(required=False, allow_blank=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'timestamp', 'clientName', 'services',
            'loggedByStaffId', 'loggedByStaffName',
            'barberId', 'barberName',
            'massageTherapistId', 'massageTherapistName',
            'serviceTotal', 'barberTip', 'massageTip', 'grandTotal',
            'paymentMethod', 'barberTipPaid', 'massageTipPaid', 'barberCommissionPaid', 'massageCommissionPaid', 'notes'
        ]

    def validate(self, attrs):
        request = self.context.get('request')
        is_boss = request and request.user and (request.user.is_superuser or request.user.is_staff or request.user.username.lower() == 'admin')
        
        # Staff cannot mark tips as paid upon creation or update
        if not is_boss:
            if 'barber_tip_paid' in attrs and self.instance is None:
                attrs['barber_tip_paid'] = False
            elif 'barber_tip_paid' in attrs and self.instance:
                attrs.pop('barber_tip_paid')

            if 'massage_tip_paid' in attrs and self.instance is None:
                attrs['massage_tip_paid'] = False
            elif 'massage_tip_paid' in attrs and self.instance:
                attrs.pop('massage_tip_paid')

        # Validate services payload if provided
        services = attrs.get('services')
        if services is not None:
            if not isinstance(services, list):
                raise serializers.ValidationError({'services': 'Services must be a list.'})
            for s in services:
                if isinstance(s, dict) and 'price' in s:
                    try:
                        if float(s['price']) < 0:
                            raise serializers.ValidationError({'services': 'Service prices cannot be negative.'})
                    except (ValueError, TypeError):
                        pass

        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            is_boss = request.user.is_superuser or request.user.is_staff or request.user.username.lower() == 'admin'
            if not is_boss and hasattr(request.user, 'staff_profile') and request.user.staff_profile:
                staff_id = request.user.staff_profile.id
                # Enforce tip privacy at serialization: staff only sees their own tip amount
                if instance.barber_id != staff_id:
                    data['barberTip'] = 0.0
                if instance.massage_therapist_id != staff_id:
                    data['massageTip'] = 0.0
        return data

class ClosingRecordSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, max_length=50)
    expectedCash = serializers.FloatField(source='expected_cash', required=False, min_value=0.0)
    actualCash = serializers.FloatField(source='actual_cash', required=False, min_value=0.0)
    cashDiff = serializers.FloatField(source='cash_diff', required=False)
    expectedMpesa = serializers.FloatField(source='expected_mpesa', required=False, min_value=0.0)
    actualMpesa = serializers.FloatField(source='actual_mpesa', required=False, min_value=0.0)
    mpesaDiff = serializers.FloatField(source='mpesa_diff', required=False)
    totalDiff = serializers.FloatField(source='total_diff', required=False)
    closedByStaffId = serializers.CharField(source='closed_by_staff_id', required=False, allow_null=True)
    closedByStaffName = serializers.CharField(source='closed_by_staff_name', required=False, allow_null=True)
    notes = SanitizedCharField(required=False, allow_blank=True)

    class Meta:
        model = ClosingRecord
        fields = [
            'id', 'timestamp',
            'expectedCash', 'actualCash', 'cashDiff',
            'expectedMpesa', 'actualMpesa', 'mpesaDiff',
            'totalDiff', 'notes',
            'closedByStaffId', 'closedByStaffName'
        ]

class ExpenseSerializer(serializers.ModelSerializer):
    id = serializers.CharField(required=False, max_length=50)
    title = SanitizedCharField(max_length=150)
    amount = serializers.FloatField(required=True, min_value=0.01)
    paymentMethod = serializers.CharField(source='payment_method', required=False)
    loggedByStaffId = serializers.CharField(source='logged_by_staff_id', required=False, allow_null=True)
    loggedByStaffName = serializers.CharField(source='logged_by_staff_name', required=False, allow_null=True)
    notes = SanitizedCharField(required=False, allow_blank=True)

    class Meta:
        model = Expense
        fields = [
            'id', 'timestamp', 'title', 'amount',
            'category', 'paymentMethod',
            'loggedByStaffId', 'loggedByStaffName',
            'notes'
        ]

class AppointmentSerializer(serializers.ModelSerializer):
    clientName = SanitizedCharField(source='client_name', max_length=120)
    clientPhone = SanitizedCharField(source='client_phone', max_length=40)
    serviceId = serializers.CharField(source='service_id', required=False, allow_null=True)
    serviceName = SanitizedCharField(source='service_name', max_length=120)
    serviceCategory = SanitizedCharField(source='service_category', required=False, allow_blank=True)
    servicePrice = serializers.FloatField(source='service_price', required=False, min_value=0.0)
    preferredDate = serializers.CharField(source='preferred_date', required=False, allow_blank=True)
    preferredStaffId = serializers.CharField(source='preferred_staff_id', required=False, allow_null=True)
    preferredStaffName = SanitizedCharField(source='preferred_staff_name', required=False, allow_null=True, allow_blank=True)
    assignedStaffId = serializers.CharField(source='assigned_staff_id', required=False, allow_null=True)
    assignedStaffName = SanitizedCharField(source='assigned_staff_name', required=False, allow_null=True, allow_blank=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    notes = SanitizedCharField(required=False, allow_blank=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'createdAt', 'clientName', 'clientPhone',
            'serviceId', 'serviceName', 'serviceCategory', 'servicePrice',
            'preferredDate', 'preferredStaffId', 'preferredStaffName',
            'assignedStaffId', 'assignedStaffName',
            'status', 'notes'
        ]
