from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ServiceViewSet,
    StaffViewSet,
    TransactionViewSet,
    ClosingRecordViewSet,
    ExpenseViewSet,
    AppointmentViewSet,
    reset_demo_data,
)
from .auth_views import login_view, me_view, logout_view, change_password_view

router = DefaultRouter()
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'staff', StaffViewSet, basename='staff')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'closing_records', ClosingRecordViewSet, basename='closing-record')
router.register(r'expenses', ExpenseViewSet, basename='expense')
router.register(r'appointments', AppointmentViewSet, basename='appointment')

urlpatterns = [
    path('auth/login/', login_view, name='auth-login'),
    path('auth/me/', me_view, name='auth-me'),
    path('auth/logout/', logout_view, name='auth-logout'),
    path('auth/change-password/', change_password_view, name='auth-change-password'),
    path('', include(router.urls)),
    path('reset_demo/', reset_demo_data, name='reset-demo'),
]
