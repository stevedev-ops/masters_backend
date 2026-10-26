from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from api.models import Service, Staff, Transaction, ClosingRecord, Expense, Appointment

class Command(BaseCommand):
    help = 'Seeds initial services, worker Shee, and user credentials for The Masters safely'

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
            Appointment.objects.all().delete()
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

        self.stdout.write('Staff roster initialized empty — admin enters workers directly via executive portal...')
        staff_data = []
        for st in staff_data:
            pass

        self.stdout.write(self.style.SUCCESS('Successfully verified/seeded The Masters data safely!'))
