from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from manufacturing.models import (
    ProductionLine, Product, PackageSize, Shift,
    Machine, DowntimeCode
)
from datetime import time
import re
import json
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample manufacturing data for testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')

        # Create Production Lines from fixture
        self.create_production_lines_from_fixture()

        # Create Products from fixture
        self.create_products_from_fixture()

        # Create Package Sizes from fixture
        self.create_package_sizes_from_fixture()

        # Create Shifts from fixture
        self.create_shifts_from_fixture()
        # Create Machines from fixture
        self.create_machines_from_fixture()

        # Create Downtime Codes from fixture
        self.create_downtime_codes_from_fixture()


        self.stdout.write(
            self.style.SUCCESS('Successfully created sample data!')
        )
        self.stdout.write(
            'Created:\n'
            f'- {ProductionLine.objects.count()} Production Lines\n'
            f'- {Product.objects.count()} Products\n'
            f'- {PackageSize.objects.count()} Package Sizes\n'
            f'- {Shift.objects.count()} Shifts\n'
            f'- {Machine.objects.count()} Machines\n'
            f'- {DowntimeCode.objects.count()} Downtime Codes'
        )

    def create_downtime_codes_from_fixture(self):
        """Load downtime codes from fixture file"""
        # Get the path to the fixture file
        fixture_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'fixtures',
            'downtime_codes.json'
        )
        
        if not os.path.exists(fixture_path):
            self.stdout.write(
                self.style.WARNING(f'Fixture file not found: {fixture_path}')
            )
            return
        
        try:
            with open(fixture_path, 'r') as f:
                data = json.load(f)
            
            # Get machines by their codes
            can_machines = Machine.objects.filter(machine_code__in=['FCAN01', ])
            pet_machines = Machine.objects.filter(machine_code__in=['FA01','FB01', 'FC01'])
            
            # Create CAN downtime codes
            for can_machine in can_machines:
                for code_data in data.get('can_codes', []):
                    DowntimeCode.objects.get_or_create(
                        machine=can_machine,
                        code=code_data['code'],
                        defaults={'reason': code_data['reason']}
                    )
            
            # Create PET downtime codes
            for pet_machine in pet_machines:
                for code_data in data.get('pet_codes', []):
                    DowntimeCode.objects.get_or_create(
                        machine=pet_machine,
                        code=code_data['code'],
                        defaults={'reason': code_data['reason']}
                    )
            
            self.stdout.write(
                self.style.SUCCESS('Successfully loaded downtime codes from fixture')
            )
            
        except json.JSONDecodeError as e:
            self.stdout.write(
                self.style.ERROR(f'Error reading fixture file: {e}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating downtime codes: {e}')
            )

    def create_shifts_from_fixture(self):
        """Load shifts from fixture file"""
        fixture_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'fixtures',
            'shifts.json'
        )
        
        if not os.path.exists(fixture_path):
            self.stdout.write(
                self.style.WARNING(f'Shifts fixture file not found: {fixture_path}')
            )
            return
        
        try:
            with open(fixture_path, 'r') as f:
                data = json.load(f)
            
            for shift_data in data.get('shifts', []):
                # Parse time strings to time objects
                start_time = time(*[int(x) for x in shift_data['start_time'].split(':')])
                end_time = time(*[int(x) for x in shift_data['end_time'].split(':')])
                
                Shift.objects.get_or_create(
                    name=shift_data['name'],
                    defaults={
                        'start_time': start_time,
                        'end_time': end_time,
                        'duration_hours': shift_data['duration_hours']
                    }
                )
            
            self.stdout.write(
                self.style.SUCCESS('Successfully loaded shifts from fixture')
            )
            
        except json.JSONDecodeError as e:
            self.stdout.write(
                self.style.ERROR(f'Error reading shifts fixture file: {e}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating shifts: {e}')
            )

    def create_machines_from_fixture(self):
        """Load machines from fixture file"""
        fixture_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'fixtures',
            'machines.json'
        )
        
        if not os.path.exists(fixture_path):
            self.stdout.write(
                self.style.WARNING(f'Machines fixture file not found: {fixture_path}')
            )
            return
        
        try:
            with open(fixture_path, 'r') as f:
                data = json.load(f)
            
            for machine_data in data.get('machines', []):
                # Get the production line by name
                try:
                    production_line = ProductionLine.objects.get(
                        name=machine_data['production_line_name']
                    )
                except ProductionLine.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Production line not found: {machine_data["production_line_name"]}'
                        )
                    )
                    continue
                
                Machine.objects.get_or_create(
                    production_line=production_line,
                    machine_name=machine_data['machine_name'],
                    defaults={
                        'machine_code': machine_data['machine_code'],
                        'rated_output': machine_data['rated_output'],
                        'main_machine': machine_data['main_machine'],
                        'machine_description': machine_data.get('machine_description', ''),
                    }
                )
            
            self.stdout.write(
                self.style.SUCCESS('Successfully loaded machines from fixture')
            )
            
        except json.JSONDecodeError as e:
            self.stdout.write(
                self.style.ERROR(f'Error reading machines fixture file: {e}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating machines: {e}')
            )

    def create_production_lines_from_fixture(self):
        """Load production lines from fixture file"""
        fixture_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'fixtures',
            'production_lines.json'
        )
        
        if not os.path.exists(fixture_path):
            self.stdout.write(
                self.style.WARNING(f'Production lines fixture file not found: {fixture_path}')
            )
            return
        
        try:
            with open(fixture_path, 'r') as f:
                data = json.load(f)
            
            for line_data in data.get('production_lines', []):
                ProductionLine.objects.get_or_create(
                    name=line_data['name'],
                    defaults={
                        'description': line_data['description'],
                        'rated_speed': line_data['rated_speed'],
                        'is_active': line_data.get('is_active', True),
                    }
                )
            
            self.stdout.write(
                self.style.SUCCESS('Successfully loaded production lines from fixture')
            )
            
        except json.JSONDecodeError as e:
            self.stdout.write(
                self.style.ERROR(f'Error reading production lines fixture file: {e}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating production lines: {e}')
            )

    def create_products_from_fixture(self):
        """Load products from fixture file"""
        fixture_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'fixtures',
            'products.json'
        )
        
        if not os.path.exists(fixture_path):
            self.stdout.write(
                self.style.WARNING(f'Products fixture file not found: {fixture_path}')
            )
            return
        
        try:
            with open(fixture_path, 'r') as f:
                data = json.load(f)
            
            for product_data in data.get('products', []):
                Product.objects.get_or_create(
                    product_code=product_data['product_code'],
                    defaults={
                        'name': product_data['name'],
                        'standard_syrup_ratio': product_data.get('standard_syrup_ratio', 1.0),
                    }
                )
            
            self.stdout.write(
                self.style.SUCCESS('Successfully loaded products from fixture')
            )
            
        except json.JSONDecodeError as e:
            self.stdout.write(
                self.style.ERROR(f'Error reading products fixture file: {e}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating products: {e}')
            )

    def create_package_sizes_from_fixture(self):
        """Load package sizes from fixture file"""
        fixture_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'fixtures',
            'package_sizes.json'
        )
        
        if not os.path.exists(fixture_path):
            self.stdout.write(
                self.style.WARNING(f'Package sizes fixture file not found: {fixture_path}')
            )
            return
        
        try:
            with open(fixture_path, 'r') as f:
                data = json.load(f)
            
            for package_data in data.get('package_sizes', []):
                PackageSize.objects.get_or_create(
                    size=package_data['size'],
                    package_type=package_data['package_type'],
                    bottle_per_pack=package_data['bottle_per_pack'],
                    defaults={
                        'volume_ml': package_data['volume_ml'],
                    }
                )
            
            self.stdout.write(
                self.style.SUCCESS('Successfully loaded package sizes from fixture')
            )
            
        except json.JSONDecodeError as e:
            self.stdout.write(
                self.style.ERROR(f'Error reading package sizes fixture file: {e}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating package sizes: {e}')
            )
