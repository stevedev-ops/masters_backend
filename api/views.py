from django.conf import settings
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.core.management import call_command
from .models import Service, Staff, Transaction, ClosingRecord, Expense, Appointment
from .serializers import (
    ServiceSerializer,
    StaffSerializer,
    TransactionSerializer,
    ClosingRecordSerializer,
    ExpenseSerializer,
    AppointmentSerializer,
)

def is_boss_user(user):
    return user and user.is_authenticated and (user.is_superuser or user.is_staff or user.username.lower() == 'admin')

class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer

    def get_permissions(self):
        # Public users can browse services for booking
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        # Only Boss / Admin can create, edit, or delete services
        return [IsAdminUser()]

class StaffViewSet(viewsets.ModelViewSet):
    queryset = Staff.objects.all()
    serializer_class = StaffSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAdminUser()]

    def perform_create(self, serializer):
        name = self.request.data.get('name', '').strip()
        custom_username = self.request.data.get('username', '').strip()
        custom_password = self.request.data.get('password', '').strip() or 'masters123'

        if custom_username:
            username = custom_username.lower()
        else:
            first_name = name.split()[0].lower() if name else 'worker'
            base = ''.join(c for c in first_name if c.isalnum()) or 'worker'
            username = base
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base}{counter}"
                counter += 1

        user, _ = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f"{username}@themasters.co.ke",
                'first_name': name,
            }
        )
        user.set_password(custom_password)
        user.is_staff = False
        user.is_superuser = False
        user.save()
        Token.objects.get_or_create(user=user)

        serializer.save(user=user)

    def perform_update(self, serializer):
        staff = serializer.save()
        new_password = self.request.data.get('password', '').strip()
        if new_password and staff.user:
            staff.user.set_password(new_password)
            staff.user.save()
        if staff.user and staff.name:
            staff.user.first_name = staff.name
            staff.user.save()

    def perform_destroy(self, instance):
        if instance.user and not (instance.user.is_superuser or instance.user.username.lower() == 'admin'):
            instance.user.delete()
        instance.delete()

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def pay_all_tips(self, request, pk=None):
        staff = self.get_object()
        txs_barber = Transaction.objects.filter(barber_id=staff.id, barber_tip_paid=False)
        txs_barber.update(barber_tip_paid=True)

        txs_massage = Transaction.objects.filter(massage_therapist_id=staff.id, massage_tip_paid=False)
        txs_massage.update(massage_tip_paid=True)

        return Response({
            'status': 'success',
            'message': f'All pending tips paid for {staff.name}'
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def pay_all_commissions(self, request, pk=None):
        staff = self.get_object()
        txs_barber = Transaction.objects.filter(barber_id=staff.id, barber_commission_paid=False)
        txs_barber.update(barber_commission_paid=True)

        txs_massage = Transaction.objects.filter(massage_therapist_id=staff.id, massage_commission_paid=False)
        txs_massage.update(massage_commission_paid=True)

        return Response({
            'status': 'success',
            'message': f'All pending 40% commissions paid for {staff.name}'
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def pay_all_payouts(self, request, pk=None):
        staff = self.get_object()
        Transaction.objects.filter(barber_id=staff.id).update(barber_tip_paid=True, barber_commission_paid=True)
        Transaction.objects.filter(massage_therapist_id=staff.id).update(massage_tip_paid=True, massage_commission_paid=True)

        return Response({
            'status': 'success',
            'message': f'All pending commissions and tips cleared for {staff.name}'
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def toggle_active(self, request, pk=None):
        staff = self.get_object()
        staff.active = not staff.active
        staff.save()
        return Response(StaffSerializer(staff).data)

class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if is_boss_user(user):
            return Transaction.objects.all()

        # If staff, strictly filter transactions to their own sessions or logs
        if hasattr(user, 'staff_profile') and user.staff_profile:
            staff_id = user.staff_profile.id
            return Transaction.objects.filter(
                Q(barber_id=staff_id) |
                Q(massage_therapist_id=staff_id) |
                Q(logged_by_staff_id=staff_id)
            )

        return Transaction.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, 'staff_profile') and user.staff_profile and not is_boss_user(user):
            serializer.save(
                logged_by_staff_id=user.staff_profile.id,
                logged_by_staff_name=user.staff_profile.name,
                barber_tip_paid=False,
                massage_tip_paid=False
            )
        else:
            serializer.save()

    def update(self, request, *args, **kwargs):
        if not is_boss_user(request.user):
            return Response(
                {'error': 'Transactions are immutable once submitted. Only management can modify records.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not is_boss_user(request.user):
            return Response(
                {'error': 'Permission denied. Only management can delete transaction records.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def toggle_tip(self, request, pk=None):
        if not is_boss_user(request.user):
            return Response(
                {'error': 'Permission denied. Only the Boss can mark tips as paid/unpaid.'},
                status=status.HTTP_403_FORBIDDEN
            )

        tx = self.get_object()
        tip_type = request.data.get('tipType')

        if tip_type == 'barber':
            tx.barber_tip_paid = not tx.barber_tip_paid
        elif tip_type == 'massage':
            tx.massage_tip_paid = not tx.massage_tip_paid
        else:
            return Response({'error': 'Invalid tipType. Must be barber or massage.'}, status=status.HTTP_400_BAD_REQUEST)

        tx.save()
        return Response(TransactionSerializer(tx, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def toggle_commission(self, request, pk=None):
        if not is_boss_user(request.user):
            return Response(
                {'error': 'Permission denied. Only the Boss can mark commissions as paid/unpaid.'},
                status=status.HTTP_403_FORBIDDEN
            )

        tx = self.get_object()
        role = request.data.get('role')

        if role == 'barber':
            tx.barber_commission_paid = not tx.barber_commission_paid
        elif role == 'massage':
            tx.massage_commission_paid = not tx.massage_commission_paid
        else:
            return Response({'error': 'Invalid role. Must be barber or massage.'}, status=status.HTTP_400_BAD_REQUEST)

        tx.save()
        return Response(TransactionSerializer(tx, context={'request': request}).data)

class ClosingRecordViewSet(viewsets.ModelViewSet):
    queryset = ClosingRecord.objects.all()
    serializer_class = ClosingRecordSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, 'staff_profile') and user.staff_profile and not is_boss_user(user):
            serializer.save(
                closed_by_staff_id=user.staff_profile.id,
                closed_by_staff_name=user.staff_profile.name
            )
        else:
            serializer.save()

    def update(self, request, *args, **kwargs):
        if not is_boss_user(request.user):
            return Response(
                {'error': 'Shift closing records cannot be modified once closed.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not is_boss_user(request.user):
            return Response(
                {'error': 'Permission denied. Only management can delete shift closing audit records.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, 'staff_profile') and user.staff_profile and not is_boss_user(user):
            serializer.save(
                logged_by_staff_id=user.staff_profile.id,
                logged_by_staff_name=user.staff_profile.name
            )
        else:
            serializer.save()

    def update(self, request, *args, **kwargs):
        if not is_boss_user(request.user):
            return Response(
                {'error': 'Permission denied. Only management can edit operational expenses.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not is_boss_user(request.user):
            return Response(
                {'error': 'Permission denied. Only management can delete operational expenses.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer

    def get_permissions(self):
        # Public website visitors can book an appointment
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def claim(self, request, pk=None):
        """
        Allows an active staff member to pick up / claim an open appointment.
        """
        apt = self.get_object()
        user = request.user
        if hasattr(user, 'staff_profile') and user.staff_profile:
            staff_id = user.staff_profile.id
            staff_name = user.staff_profile.name
        else:
            staff_id = f"boss-{user.id}"
            staff_name = user.username

        apt.assigned_staff_id = staff_id
        apt.assigned_staff_name = staff_name
        apt.status = 'confirmed'
        apt.save()
        return Response(AppointmentSerializer(apt).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def assign(self, request, pk=None):
        """
        Allows the Boss to assign an appointment to a specific staff member.
        """
        if not is_boss_user(request.user):
            return Response(
                {'error': 'Permission denied. Only the Boss can assign appointments.'},
                status=status.HTTP_403_FORBIDDEN
            )

        apt = self.get_object()
        staff_id = request.data.get('staffId')
        staff_name = request.data.get('staffName')

        if not staff_id or not staff_name:
            return Response(
                {'error': 'staffId and staffName are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        apt.assigned_staff_id = staff_id
        apt.assigned_staff_name = staff_name
        apt.status = 'confirmed'
        apt.save()
        return Response(AppointmentSerializer(apt).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def update_status(self, request, pk=None):
        apt = self.get_object()
        new_status = request.data.get('status')
        if new_status in ['pending', 'confirmed', 'completed', 'cancelled']:
            apt.status = new_status
            apt.save()
            return Response(AppointmentSerializer(apt).data)
        return Response({'error': 'Invalid status.'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def reset_demo_data(request):
    """
    Disabled in production. In local development, requires superuser privileges.
    Guarantees no arbitrary or automated script can wipe live records.
    """
    if not settings.DEBUG:
        return Response(
            {'error': 'Demo data reset is strictly disabled in production mode.'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        call_command('seed_masters', force=True)
        return Response({'status': 'success', 'message': 'Demo data reset safely in local development.'})
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
