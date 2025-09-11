from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from manufacturing.models import (
    ProductionLine, Product, PackageSize, Shift, ManufacturingOrder,
    Machine, DowntimeCode
)
from datetime import time

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample manufacturing data for testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')

        # Create Production Lines
        line1, created = ProductionLine.objects.get_or_create(
            name='Line A',
            defaults={'description': 'Main production line for PET bottles', 'rated_speed': 12000}
        )
        line2, created = ProductionLine.objects.get_or_create(
            name='Line B', 
            defaults={'description': 'Secondary production line for cans', 'rated_speed': 8000}
        )

        # Create Products
        product1, created = Product.objects.get_or_create(
            product_code='COLA-001',
            defaults={'name': 'Classic Cola', 'standard_syrup_ratio': 1.2}
        )
        product2, created = Product.objects.get_or_create(
            product_code='LEMON-001',
            defaults={'name': 'Lemon Soda', 'standard_syrup_ratio': 1.1}
        )

        # Create Package Sizes
        package1, created = PackageSize.objects.get_or_create(
            size='500ml',
            package_type='PET',
            defaults={'volume_ml': 500}
        )
        package2, created = PackageSize.objects.get_or_create(
            size='330ml',
            package_type='CAN',
            defaults={'volume_ml': 330}
        )
        package3, created = PackageSize.objects.get_or_create(
            size='330ml',
            package_type='PET',
            defaults={'volume_ml': 330}
        )
        package4, created = PackageSize.objects.get_or_create(
            size='250ml',
            package_type='CAN',
            defaults={'volume_ml': 250}
        )

        # Create Shifts
        shift1, created = Shift.objects.get_or_create(
            name='8H_SHIFT_1',
            defaults={'start_time': time(7, 0), 'end_time': time(15, 0), 'duration_hours': 8}
        )
        shift2, created = Shift.objects.get_or_create(
            name='8H_SHIFT_2',
            defaults={'start_time': time(15, 0), 'end_time': time(23, 0), 'duration_hours': 8}
        )
        shift3, created = Shift.objects.get_or_create(
            name='8H_SHIFT_3',
            defaults={'start_time': time(23, 0), 'end_time': time(7, 0), 'duration_hours': 8}
        )

        shift4, created = Shift.objects.get_or_create(
            name='12H_SHIFT_1',
            defaults={'start_time': time(7, 0), 'end_time': time(19, 0), 'duration_hours': 12}
        )
        shift5, created = Shift.objects.get_or_create(
            name='12H_SHIFT_2',
            defaults={'start_time': time(19, 0), 'end_time': time(7, 0), 'duration_hours': 12}
        )
        # Create Machines
        machine1, created = Machine.objects.get_or_create(
            production_line=line1,
            machine_name='Filler A1',
            defaults={'machine_code': 'FA01', 'rated_output': 12000}
        )
        machine2, created = Machine.objects.get_or_create(
            production_line=line2,
            machine_name='Filler B1',
            defaults={'machine_code': 'FB01', 'rated_output': 8000}
        )

        # Create Downtime Codes
        code1, created = DowntimeCode.objects.get_or_create(
            machine=machine1,
            code='M001',
            defaults={'reason': 'Mechanical failure'}
        )
        code2, created = DowntimeCode.objects.get_or_create(
            machine=machine1,
            code='C001',
            defaults={'reason': 'Changeover'}
        )

        # Create Sample Manufacturing Orders
        order1, created = ManufacturingOrder.objects.get_or_create(
            order_number='MO-2024-001',
            defaults={
                'order_date': '2024-01-15',
                'product': product1,
                'package_size': package1,
                'quantity': 10000,
                'status': 'Pending'
            }
        )
        order2, created = ManufacturingOrder.objects.get_or_create(
            order_number='MO-2024-002',
            defaults={
                'order_date': '2024-01-15',
                'product': product2,
                'package_size': package2,
                'quantity': 15000,
                'status': 'In Progress'
            }
        )

        self.stdout.write(
            self.style.SUCCESS('Successfully created sample data!')
        )
        self.stdout.write(
            'Created:\n'
            f'- {ProductionLine.objects.count()} Production Lines\n'
            f'- {Product.objects.count()} Products\n'
            f'- {PackageSize.objects.count()} Package Sizes\n'
            f'- {Shift.objects.count()} Shifts\n'
            f'- {ManufacturingOrder.objects.count()} Manufacturing Orders\n'
            f'- {Machine.objects.count()} Machines\n'
            f'- {DowntimeCode.objects.count()} Downtime Codes'
        )
