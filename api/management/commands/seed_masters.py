from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from api.models import Service, Staff, Transaction, ClosingRecord, Expense

class Command(BaseCommand):
    help = 'Seeds initial services, staff members, user credentials, demo transactions, and expenses for The Masters safely'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reset: wipe all existing database records before seeding (NEVER run in live production!)',
        )

    def handle(self, *args, **options):
        has_existing_data = User.objects.exists() or Transaction.objects.exists()

        if has_existing_data and not options['force']:
            self.stdout.write(
                self.style.WARNING(
                    'Database already contains data! To prevent accidental loss of live transactions and users, '
                    'seed_masters will NOT delete existing records without the explicit --force flag.'
                )
            )
            return

        if options['force']:
            self.stdout.write(self.style.WARNING('FORCE RESET REQUESTED: Clearing existing records...'))
            Expense.objects.all().delete()
            ClosingRecord.objects.all().delete()
            Transaction.objects.all().delete()
            Staff.objects.all().delete()
            Service.objects.all().delete()
            Token.objects.all().delete()
            User.objects.all().delete()

        self.stdout.write('Creating Boss / Admin account...')
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'boss@themasters.co.ke',
                'first_name': 'The Boss',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        admin_user.set_password('masters2026!')
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()
        Token.objects.get_or_create(user=admin_user)

        self.stdout.write('Seeding initial services...')
        services_data = [
            {'id': 'srv-1', 'name': 'Shaving', 'price': 250, 'category': 'Barber', 'icon': 'Scissors', 'description': 'Precision razor or clipper beard trim & shave with hot towel finish.'},
            {'id': 'srv-2', 'name': 'Scrubbing', 'price': 200, 'category': 'Barber', 'icon': 'Sparkles', 'description': 'Deep scalp & face exfoliating scrub treatment.'},
            {'id': 'srv-3', 'name': 'Dying', 'price': 200, 'category': 'Barber', 'icon': 'Palette', 'description': 'Beard & hair color enhancement or gray coverage.'},
            {'id': 'srv-4', 'name': 'Bleaching', 'price': 600, 'category': 'Barber', 'icon': 'Sun', 'description': 'Hair & beard lightening & custom tone bleach treatment.'},
            {'id': 'srv-5', 'name': 'Facial Treatment', 'price': 800, 'category': 'Spa & Skincare', 'icon': 'Smile', 'description': 'Deep cleansing, steaming, pore detox & soothing moisturization.'},
            {'id': 'srv-6', 'name': 'Manicure', 'price': 100, 'category': 'Nail Care', 'icon': 'Hand', 'description': 'Nail shaping, cuticle grooming & buffing.'},
            {'id': 'srv-7', 'name': 'Back Massage', 'price': 700, 'category': 'Massage & Bodywork', 'icon': 'Activity', 'description': 'Targeted deep tissue tension release for shoulders & back (30 mins).'},
            {'id': 'srv-8', 'name': 'Full Body Massage', 'price': 1700, 'category': 'Massage & Bodywork', 'icon': 'Heart', 'description': 'Relaxing Swedish or deep tissue full body massage treatment (60 mins).'},
            {'id': 'srv-9', 'name': 'Hot Stone Massage', 'price': 2700, 'category': 'Massage & Bodywork', 'icon': 'Flame', 'description': 'Luxury heated basalt stone therapy for muscular restoration (90 mins).'},
        ]
        for s in services_data:
            Service.objects.get_or_create(
                id=s['id'],
                defaults={
                    'name': s['name'],
                    'price': s['price'],
                    'category': s['category'],
                    'icon': s['icon'],
                    'description': s['description']
                }
            )

        self.stdout.write('Seeding staff members and authentication user accounts...')
        staff_data = [
            {'id': 'stf-1', 'username': 'james', 'name': 'James', 'role': 'Barber', 'phone': '+254 712 345 678', 'active': True, 'title': 'Master Barber & Stylist'},
            {'id': 'stf-2', 'username': 'david', 'name': 'David', 'role': 'Barber', 'phone': '+254 722 987 654', 'active': True, 'title': 'Senior Barber'},
            {'id': 'stf-3', 'username': 'sarah', 'name': 'Sarah', 'role': 'Massage Therapist', 'phone': '+254 733 112 233', 'active': True, 'title': 'Lead Spa Therapist'},
            {'id': 'stf-4', 'username': 'grace', 'name': 'Grace', 'role': 'Massage Therapist', 'phone': '+254 744 556 677', 'active': True, 'title': 'Hot Stone Specialist'},
            {'id': 'stf-5', 'username': 'alex', 'name': 'Alex', 'role': 'Dual', 'phone': '+254 755 889 900', 'active': True, 'title': 'Grooming & Bodywork Specialist'},
        ]
        for st in staff_data:
            u, _ = User.objects.get_or_create(
                username=st['username'],
                defaults={
                    'email': f"{st['username']}@themasters.co.ke",
                    'first_name': st['name'],
                }
            )
            u.set_password('masters123')
            u.save()
            Token.objects.get_or_create(user=u)
            Staff.objects.get_or_create(
                id=st['id'],
                defaults={
                    'user': u,
                    'name': st['name'],
                    'role': st['role'],
                    'phone': st['phone'],
                    'active': st['active'],
                    'title': st['title']
                }
            )

        now = timezone.now()
        if not Transaction.objects.exists():
            self.stdout.write('Seeding initial demo transactions...')
            txs_data = [
                {
                    'id': 'tx-101',
                    'timestamp': now - timedelta(hours=3),
                    'client_name': 'Michael K.',
                    'services': [
                        {'id': 'srv-9', 'name': 'Hot Stone Massage', 'price': 2700, 'category': 'Massage & Bodywork'},
                        {'id': 'srv-1', 'name': 'Shaving', 'price': 250, 'category': 'Barber'}
                    ],
                    'logged_by_staff_id': 'stf-3',
                    'logged_by_staff_name': 'Sarah',
                    'barber_id': 'stf-1',
                    'barber_name': 'James',
                    'massage_therapist_id': 'stf-3',
                    'massage_therapist_name': 'Sarah',
                    'service_total': 2950,
                    'barber_tip': 150,
                    'massage_tip': 350,
                    'grand_total': 3450,
                    'payment_method': 'M-Pesa',
                    'barber_tip_paid': True,
                    'massage_tip_paid': False,
                    'notes': 'Hot stone therapy + beard trim.'
                }
            ]
            for tx in txs_data:
                Transaction.objects.get_or_create(id=tx['id'], defaults=tx)

        self.stdout.write(self.style.SUCCESS('Successfully verified/seeded The Masters data safely!'))
