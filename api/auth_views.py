from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .serializers import StaffSerializer

class LoginRateThrottle(AnonRateThrottle):
    scope = 'login'

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def login_view(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '').strip()

    if not username or not password:
        return Response(
            {'error': 'Both username and password are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(username=username, password=password)
    if not user:
        return Response(
            {'error': 'Invalid credentials. Please check your username and password.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.is_active:
        return Response(
            {'error': 'This user account has been disabled.'},
            status=status.HTTP_403_FORBIDDEN
        )

    token, _ = Token.objects.get_or_create(user=user)

    # Determine role & password reset requirements
    role = 'boss'
    staff_data = None
    must_change = False

    if user.is_superuser or user.is_staff or user.username.lower() == 'admin':
        role = 'boss'
        # For admin user, if they are still on the initial temporary password, require change
        must_change = user.check_password('masters2026!')

    if hasattr(user, 'staff_profile') and user.staff_profile:
        staff_data = StaffSerializer(user.staff_profile).data
        if not user.is_superuser and user.username.lower() != 'admin':
            role = 'staff'
        must_change = user.staff_profile.must_change_password

    return Response({
        'token': token.key,
        'mustChangePassword': must_change,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': role,
            'mustChangePassword': must_change,
            'staffProfile': staff_data,
        }
    })

@api_view(['GET'])
def me_view(request):
    user = request.user
    if not user.is_authenticated:
        return Response({'authenticated': False}, status=status.HTTP_200_OK)

    role = 'boss' if (user.is_superuser or user.is_staff or user.username.lower() == 'admin') else 'staff'
    staff_data = None
    must_change = False

    if role == 'boss':
        must_change = user.check_password('masters2026!')

    if hasattr(user, 'staff_profile') and user.staff_profile:
        staff_data = StaffSerializer(user.staff_profile).data
        must_change = user.staff_profile.must_change_password

    return Response({
        'authenticated': True,
        'mustChangePassword': must_change,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': role,
            'mustChangePassword': must_change,
            'staffProfile': staff_data,
        }
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    """
    Allows authenticated Boss or Staff to change their password.
    Clears the must_change_password flag and updates auth token.
    """
    user = request.user
    old_password = request.data.get('oldPassword', '').strip()
    new_password = request.data.get('newPassword', '').strip()

    if not old_password or not new_password:
        return Response(
            {'error': 'Both current password and new password are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not user.check_password(old_password):
        return Response(
            {'error': 'Current password is incorrect. Please enter your existing password.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if len(new_password) < 8:
        return Response(
            {'error': 'New password must be at least 8 characters long for security.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if old_password == new_password:
        return Response(
            {'error': 'New password must be different from your temporary password.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Set new secure password
    user.set_password(new_password)
    user.save()

    # Clear must_change_password flag if staff profile exists
    if hasattr(user, 'staff_profile') and user.staff_profile:
        user.staff_profile.must_change_password = False
        user.staff_profile.save()

    # Ensure valid token
    token, _ = Token.objects.get_or_create(user=user)

    return Response({
        'status': 'success',
        'message': 'Password changed successfully! Your account is secured.',
        'token': token.key,
        'mustChangePassword': False,
    })

@api_view(['POST'])
def logout_view(request):
    if request.user.is_authenticated:
        try:
            request.user.auth_token.delete()
        except Exception:
            pass
    return Response({'status': 'success', 'message': 'Logged out successfully.'})
