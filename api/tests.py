from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from api.models import Service, Staff, Transaction, Expense, Appointment

class SecurityAndPermissionsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Admin / Boss
        self.boss_user = User.objects.create_superuser('boss', 'boss@themasters.co.ke', 'adminpass123')
        self.boss_token = Token.objects.create(user=self.boss_user)

        # Barber: James
        self.james_user = User.objects.create_user('james', 'james@themasters.co.ke', 'barberpass123')
        self.james_token = Token.objects.create(user=self.james_user)
        self.james_staff = Staff.objects.create(
            id='stf-james',
            user=self.james_user,
            name='James',
            role='Barber',
            must_change_password=True
        )

        # Therapist: Sarah
        self.sarah_user = User.objects.create_user('sarah', 'sarah@themasters.co.ke', 'therapistpass123')
        self.sarah_token = Token.objects.create(user=self.sarah_user)
        self.sarah_staff = Staff.objects.create(
            id='stf-sarah',
            user=self.sarah_user,
            name='Sarah',
            role='Massage Therapist',
            must_change_password=True
        )

        # Sample Service
        self.service = Service.objects.create(
            id='srv-1',
            name='Luxury Shave',
            price=300,
            category='Barber'
        )

        # Sample Transaction with split tips
        self.tx = Transaction.objects.create(
            id='tx-split-1',
            client_name='Test Client',
            barber_id=self.james_staff.id,
            barber_name=self.james_staff.name,
            massage_therapist_id=self.sarah_staff.id,
            massage_therapist_name=self.sarah_staff.name,
            service_total=2000,
            barber_tip=200,
            massage_tip=500,
            grand_total=2700,
            payment_method='M-Pesa'
        )

    def test_services_catalog_is_publicly_readable(self):
        # Public visitor should be able to view services for booking
        res = self.client.get('/api/services/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_unauthenticated_cannot_access_transactions_or_expenses(self):
        # Unauthenticated calls must be blocked
        tx_res = self.client.get('/api/transactions/')
        self.assertEqual(tx_res.status_code, status.HTTP_401_UNAUTHORIZED)

        exp_res = self.client.get('/api/expenses/')
        self.assertEqual(exp_res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_staff_tip_isolation(self):
        # Authenticate as James (Barber)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.james_token.key}')
        res = self.client.get('/api/transactions/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tx_data = res.json()[0]
        # James sees his barber tip
        self.assertEqual(tx_data['barberTip'], 200.0)
        # Sarah's tip is masked to 0.0 for James!
        self.assertEqual(tx_data['massageTip'], 0.0)

    def test_boss_sees_full_ledger_and_all_tips(self):
        # Authenticate as Boss
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.boss_token.key}')
        res = self.client.get('/api/transactions/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tx_data = res.json()[0]
        # Boss sees full split
        self.assertEqual(tx_data['barberTip'], 200.0)
        self.assertEqual(tx_data['massageTip'], 500.0)

    def test_script_injection_sanitization(self):
        # Authenticate as James
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.james_token.key}')
        
        # Attempt to submit a script payload
        payload = {
            'title': 'Cleaning Supplies <script>alert("hacked")</script>',
            'amount': 350.0,
            'category': 'Shop Supplies',
            'paymentMethod': 'Cash',
            'notes': '<script src="evil.js"></script>Normal notes here <iframe src="bad"></iframe>'
        }
        res = self.client.post('/api/expenses/', data=payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        created_expense = Expense.objects.get(id=res.json()['id'])
        
        # Script tags must be stripped and never pushed to database
        self.assertNotIn('<script>', created_expense.title)
        self.assertNotIn('alert("hacked")', created_expense.title)
        self.assertNotIn('<script', created_expense.notes)
        self.assertNotIn('<iframe', created_expense.notes)
        self.assertIn('Normal notes here', created_expense.notes)

    def test_unauthorized_user_cannot_trigger_reset_demo(self):
        # Non-admin or unauthenticated cannot call reset_demo
        res = self.client.post('/api/reset_demo/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_forced_password_reset_workflow(self):
        # 1. Login with initial default credentials
        login_res = self.client.post('/api/auth/login/', {'username': 'james', 'password': 'barberpass123'})
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        self.assertTrue(login_res.json()['mustChangePassword'])

        token = login_res.json()['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

        # 2. Reject incorrect current password
        bad_old_res = self.client.post('/api/auth/change-password/', {
            'oldPassword': 'wrongPassword!',
            'newPassword': 'SecureNewPassword2026!'
        })
        self.assertEqual(bad_old_res.status_code, status.HTTP_400_BAD_REQUEST)

        # 3. Reject password under 8 characters
        short_res = self.client.post('/api/auth/change-password/', {
            'oldPassword': 'barberpass123',
            'newPassword': 'short'
        })
        self.assertEqual(short_res.status_code, status.HTTP_400_BAD_REQUEST)

        # 4. Successfully change password
        change_res = self.client.post('/api/auth/change-password/', {
            'oldPassword': 'barberpass123',
            'newPassword': 'JamesBrandNewPrivatePass2026!'
        })
        self.assertEqual(change_res.status_code, status.HTTP_200_OK)
        self.assertFalse(change_res.json()['mustChangePassword'])

        # 5. Check staff profile flag in DB is now False
        self.james_staff.refresh_from_db()
        self.assertFalse(self.james_staff.must_change_password)

        # 6. Next login with new password succeeds and mustChangePassword is False
        new_login_res = self.client.post('/api/auth/login/', {
            'username': 'james',
            'password': 'JamesBrandNewPrivatePass2026!'
        })
        self.assertEqual(new_login_res.status_code, status.HTTP_200_OK)
        self.assertFalse(new_login_res.json()['mustChangePassword'])

    def test_appointment_booking_and_routing_workflow(self):
        # 1. Public customer books an appointment with preferred staff
        public_client = APIClient()
        booking_data = {
            'clientName': 'Marcus Vance',
            'clientPhone': '0711223344',
            'serviceId': 'srv-1',
            'serviceName': 'Executive Haircut & Beard Grooming',
            'serviceCategory': 'Barber',
            'servicePrice': 600.0,
            'preferredDate': '2026-09-10',
            'preferredStaffId': self.james_staff.id,
            'preferredStaffName': self.james_staff.name,
        }
        res1 = public_client.post('/api/appointments/', booking_data, format='json')
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        apt1_id = res1.json()['id']
        self.assertEqual(res1.json()['clientName'], 'Marcus Vance')
        self.assertEqual(res1.json()['preferredStaffId'], self.james_staff.id)
        self.assertEqual(res1.json()['status'], 'pending')

        # 2. Public customer books an open appointment ("Any Available")
        open_booking = {
            'clientName': 'Alice Smith',
            'clientPhone': '0799887766',
            'serviceName': 'Hot Stone Full Body Massage',
            'serviceCategory': 'Massage & Bodywork',
            'servicePrice': 2500.0,
            'preferredDate': '2026-09-11',
            'preferredStaffId': None,
            'preferredStaffName': None,
        }
        res2 = public_client.post('/api/appointments/', open_booking, format='json')
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        apt2_id = res2.json()['id']

        # 3. Staff member logs in and claims / picks up the open appointment
        staff_client = APIClient()
        staff_client.credentials(HTTP_AUTHORIZATION=f'Token {self.james_token.key}')
        claim_res = staff_client.post(f'/api/appointments/{apt2_id}/claim/')
        self.assertEqual(claim_res.status_code, status.HTTP_200_OK)
        self.assertEqual(claim_res.json()['assignedStaffId'], self.james_staff.id)
        self.assertEqual(claim_res.json()['status'], 'confirmed')

        # 4. Boss assigns the first appointment to another staff member
        boss_client = APIClient()
        boss_client.credentials(HTTP_AUTHORIZATION=f'Token {self.boss_token.key}')
        assign_res = boss_client.post(f'/api/appointments/{apt1_id}/assign/', {
            'staffId': self.james_staff.id,
            'staffName': self.james_staff.name
        }, format='json')
        self.assertEqual(assign_res.status_code, status.HTTP_200_OK)
        self.assertEqual(assign_res.json()['assignedStaffId'], self.james_staff.id)
        self.assertEqual(assign_res.json()['status'], 'confirmed')
