from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal
from datetime import timedelta

User = get_user_model()

class ProductionLine(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    rated_speed = models.DecimalField(max_digits=10, decimal_places=2, help_text="Rated speed in bottles per hour",default=10000)
    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=100)
    product_code = models.CharField(max_length=50, unique=True)
    standard_syrup_ratio = models.DecimalField(max_digits=5, decimal_places=3, default=1.0, 
                                               help_text="Standard syrup ratio for yield calculations")
    
    def __str__(self):
        return f"{self.name}"

class PackageSize(models.Model):
    PACKAGE_TYPES = [
        ('PET', 'PET Bottle'),
        ('CAN', 'Can'),
    ]
    
    size = models.CharField(max_length=50)  # e.g., "500ml", "1L"
    package_type = models.CharField(max_length=10, choices=PACKAGE_TYPES)
    volume_ml = models.PositiveIntegerField(help_text="Volume in milliliters",default=500)
    bottle_per_pack = models.PositiveIntegerField(default=12)
    def __str__(self):
        return f"{self.size} {self.package_type}"

class Shift(models.Model):
    SHIFT_TYPES = [
        ('8H_SHIFT_1', '8H Shift 1'),
        ('8H_SHIFT_2', '8H Shift 2'), 
        ('8H_SHIFT_3', '8H Shift 3'),
        ('12H_SHIFT_1', '12H Shift 1'),
        ('12H_SHIFT_2', '12H Shift 2'),
    ]
    
    name = models.CharField(max_length=20, choices=SHIFT_TYPES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    duration_hours = models.DecimalField(max_digits=4, decimal_places=2, default=8.0)
    
    def __str__(self):
        return f"{self.get_name_display()} ({self.start_time}-{self.end_time})"

class Machine(models.Model):
    production_line = models.ForeignKey(ProductionLine, on_delete=models.CASCADE)
    machine_name = models.CharField(max_length=100)
    machine_code = models.CharField(max_length=100)
    machine_description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    rated_output = models.DecimalField(max_digits=10, decimal_places=2, help_text="Rated output in bottles per hour")
    main_machine = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.machine_name} ({self.machine_code})"
    
    class Meta:
        verbose_name = "Machine"
        verbose_name_plural = "Machines"
        unique_together = ['production_line', 'machine_name']

class DowntimeCode(models.Model):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE)
    code = models.CharField(max_length=100)
    reason = models.TextField(blank=True)

    def __str__(self):
        return f"{self.code} - {self.reason}"

    class Meta:
        unique_together = ['machine', 'code']

class ProductionRun(models.Model):
    """Main model representing a single production run"""
    # Basic Information
    production_batch_number = models.CharField(max_length=100, unique=True)
    date = models.DateField()
    production_line = models.ForeignKey(ProductionLine, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    package_size = models.ForeignKey(PackageSize, on_delete=models.CASCADE)
    production_start = models.DateTimeField()
    production_end = models.DateTimeField(null=True, blank=True)
    
    # Shift Information
    shift_teamleader = models.ForeignKey(User, on_delete=models.CASCADE)
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE)
    
    # Production Data
    total_downtime_minutes = models.PositiveIntegerField(default=0)
    final_syrup_volume = models.DecimalField(max_digits=10, decimal_places=2)
    mixing_ratio = models.DecimalField(max_digits=10, decimal_places=2)
    filler_output = models.DecimalField(max_digits=10, decimal_places=2)
    good_products_pack = models.PositiveIntegerField()
    
    # Status
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['production_batch_number', 'production_line', 'date']
    
    def __str__(self):
        return f"{self.production_batch_number} - {self.product.name}"
    
    # def split_production_line_name(self):
    #     """Split production line name and nerge with a -"""
    #     return self.production_line.name.replace(' ', '-')

    @staticmethod
    def generate_batch_number(product, package_size, shift, date, production_line):
        """Generate production batch number from components"""
        if not all([product, package_size, shift, date, production_line]):
            return ""
        
        # Format: PRODUCT_CODE-SIZE-SHIFT_TYPE-YYYYMMDD
        # Example: COLA-500ML-8H1-20250912
        date_str = date.strftime('%Y%m%d') if hasattr(date, 'strftime') else str(date).replace('-', '')
        shift_code = shift.name.replace('_SHIFT_', 'H') if hasattr(shift, 'name') else str(shift)
        size_str = package_size.size.replace(' ', '').upper() if hasattr(package_size, 'size') else str(package_size)
        product_code = product.product_code.upper() if hasattr(product, 'product_code') else str(product)
        line_code = production_line.name.replace(' ', '-').upper() if hasattr(production_line, 'name') else str(production_line)

        batch_number = f"{product_code}-{size_str}-{shift_code}-{date_str}-{line_code}"
        
        # Ensure uniqueness by adding sequence number if needed
        base_batch = batch_number
        counter = 1
        while ProductionRun.objects.filter(production_batch_number=batch_number).exists():
            batch_number = f"{base_batch}-{counter:02d}"
            counter += 1
            
        return batch_number
    
    # ===== CALCULATION METHODS =====
    @property
    def good_products_in_packaging_units(self):
        """Calculate good products in packaging units. This is the number of good products in the packaging units."""
        return self.good_products_pack * self.package_size.bottle_per_pack

    @property
    def production_duration_minutes(self):
        """Calculate total production duration in minutes"""
        if self.production_end and self.production_start:
            return (self.production_end - self.production_start).total_seconds() / 60
        return 0
    
    @property
    def planned_production_time_minutes(self):
        """Planned production time (excluding planned downtime like CIP)"""
        total_minutes = self.production_duration_minutes
        return total_minutes if total_minutes > 0 else self.shift.duration_hours * 60
    
    @property
    def planned_downtime_minutes(self):
        """Calculate total planned downtime minutes"""
        return sum(
            self.stop_events.filter(is_planned=True).values_list('duration_minutes', flat=True)
        )
    
    @property
    def unplanned_downtime_minutes(self):
        """Calculate total unplanned downtime minutes"""
        return self.total_downtime_minutes
    


    def calculate_availability(self):
        """Calculate availability = (Planned Production Time - Downtime) / Planned Production Time"""
        planned_time = self.planned_production_time_minutes
        if planned_time <= 0:
            return Decimal('0.00')
        
        actual_runtime = planned_time - self.unplanned_downtime_minutes
        return Decimal(actual_runtime / planned_time * 100).quantize(Decimal('0.01'))
    
    def calculate_performance(self):
        """Calculate performance = (Actual Output / Rated Output) * 100"""
        if not hasattr(self, 'production_line') or self.production_duration_minutes <= 0:
            return Decimal('0.00')
        
        # Get the main machine for this production line (first active machine)
        main_machine = self.production_line.machine_set.filter(main_machine=True).first()
        if not main_machine:
            return Decimal('0.00')
        operating_time = Decimal(self.production_duration_minutes) - Decimal(self.unplanned_downtime_minutes)
        operating_hours = operating_time / Decimal('60')
        theoretical_output = main_machine.rated_output * operating_hours
        
        if theoretical_output <= 0:
            return Decimal('0.00')
       

        performance = (Decimal(self.good_products_in_packaging_units) / theoretical_output * 100)
        return performance.quantize(Decimal('0.01'))
    
    def calculate_quality(self):
        """Calculate quality = Good Products / Total Products Produced"""
        if not hasattr(self, 'packaging_material'):
            return Decimal('0.00')
        
        packaging = self.packaging_material
        product_reject = packaging.qty_product_reject or 0
        bottle_reject = packaging.qty_bottle_reject or 0
        total_products = (self.good_products_in_packaging_units) + product_reject + bottle_reject
        
        if total_products <= 0:
            return Decimal('0.00')
        
        quality = (Decimal(self.good_products_in_packaging_units) / Decimal(total_products) * 100)
        return quality.quantize(Decimal('0.01'))
    
    def calculate_oee(self):
        """Calculate Overall Equipment Effectiveness (OEE)"""
        availability = self.calculate_availability()
        performance = self.calculate_performance()
        quality = self.calculate_quality()
        
        oee = (availability * performance * quality) / Decimal('10000')  # Divide by 100^2 since we're dealing with percentages
        return oee.quantize(Decimal('0.01'))
    
    def calculate_syrup_yield(self):
        """Calculate syrup yield percentage based on expected vs actual"""
        # This would be based on your business rules
        # Example: Expected syrup = good_products * package_volume * standard_ratio
        syrup_in_bottle = (Decimal(self.good_products_in_packaging_units) * 
                           Decimal(self.package_size.volume_ml) 
                           ) / (Decimal(self.mixing_ratio) * 1000)
        
        if syrup_in_bottle <= 0:
            return Decimal('0.00')
        
        yield_percentage = (syrup_in_bottle / self.final_syrup_volume  * 100)
        return yield_percentage.quantize(Decimal('0.01'))
    
    def update_calculations(self):
        """Update all calculated fields and save to ProductionReport"""
        report, created = ProductionReport.objects.get_or_create(production_run=self)
        
        # Calculate all metrics
        report.availability = self.calculate_availability()
        report.performance = self.calculate_performance()
        report.quality = self.calculate_quality()
        report.oee = self.calculate_oee()
        report.syrup_yield_percentage = self.calculate_syrup_yield()
        
        # Calculate packaging yields if packaging material exists
        if hasattr(self, 'packaging_material'):
            packaging = self.packaging_material
            
            # Preform yield
            preform_used = packaging.qty_preform_used or 0
            preform_reject = packaging.qty_preform_reject or 0
            total_preforms = preform_used + preform_reject
            if total_preforms > 0:
                report.preform_yield_percentage = Decimal(
                    (preform_used / total_preforms) * 100
                ).quantize(Decimal('0.01'))
            
            # Bottle reject percentage
            bottle_reject = packaging.qty_bottle_reject or 0
            total_bottles = self.good_products_pack + bottle_reject
            if total_bottles > 0:
                report.bottle_reject_percentage = Decimal(
                    (bottle_reject / total_bottles) * 100
                ).quantize(Decimal('0.01'))
        
        # Calculate utility metrics if utility data exists
        if hasattr(self, 'utility'):
            utility = self.utility
            
            # CO2 utilization (example calculation)
            kg_co2_value = utility.kg_co2 if utility.kg_co2 is not None else Decimal('0')
            if self.good_products_pack and kg_co2_value > 0:
                # Example: 0.1kg per pack
                expected_co2 = Decimal(self.good_products_pack) * Decimal('0.1')
                report.co2_utilization_percentage = (
                    (expected_co2 / kg_co2_value) * Decimal('100')
                ).quantize(Decimal('0.01'))
        
        report.save()
        return report

class PackagingMaterial(models.Model):
    """Packaging materials used in a production run"""
    production_run = models.OneToOneField(ProductionRun, on_delete=models.CASCADE, related_name='packaging_material')
    
    # PET lien specific fields
    qty_preform_used = models.PositiveIntegerField(blank=True, null=True)
    qty_cap_used = models.PositiveIntegerField(blank=True, null=True)
    qty_product_reject = models.PositiveIntegerField(blank=True, null=True)
    qty_preform_reject = models.PositiveIntegerField(blank=True, null=True)
    qty_bottle_reject = models.PositiveIntegerField(blank=True, null=True)
    qty_cap_reject = models.PositiveIntegerField(blank=True, null=True)

    # Can line specific fields
    qty_can_used = models.PositiveIntegerField(blank=True, null=True)
    qty_empty_can_reject = models.PositiveIntegerField(blank=True, null=True)
    qty_can_cover_used = models.PositiveIntegerField(blank=True, null=True)
    qty_can_cover_reject = models.PositiveIntegerField(blank=True, null=True)
    qty_carton_used = models.PositiveIntegerField(blank=True, null=True)
    qty_carton_reject = models.PositiveIntegerField(blank=True, null=True)
    qty_filled_can_reject = models.PositiveIntegerField(blank=True, null=True)
    
    # Common packaging materials
    label_reject_g = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    shrink_wrap_kg = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    stretch_wrap_g = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)


class Utility(models.Model):
    """Utility consumption for a production run"""
    production_run = models.OneToOneField(ProductionRun, on_delete=models.CASCADE, related_name='utility')
    kg_co2 = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    boiler_fuel_l = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    generator_fuel_l = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    edg_power_consumption = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

class StopEvent(models.Model):
    """Downtime events during production"""
    production_run = models.ForeignKey(ProductionRun, on_delete=models.CASCADE, related_name='stop_events')
    
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE)
    code = models.ForeignKey(DowntimeCode, on_delete=models.CASCADE)
    reason = models.CharField(max_length=255, null=True, blank=True) #remark
    duration_minutes = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_planned = models.BooleanField(default=False) #if the downtime is planned or not (CIP,startup,shutdown,etc.)

    def __str__(self):
        return f"{self.machine.machine_name} - {self.code} ({self.duration_minutes}min)"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update total downtime in production run
        self.production_run.total_downtime_minutes = sum(
            # exclude planned downtime from total downtime
            self.production_run.stop_events.values_list('duration_minutes', flat=True).exclude(is_planned=True)
        )
        self.production_run.save()

class ProductionReport(models.Model):
    """Calculated metrics and final report"""
    production_run = models.OneToOneField(ProductionRun, on_delete=models.CASCADE, related_name='report')
    
    # Calculated fields
    syrup_yield_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    preform_yield_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    bottle_reject_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    label_reject_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    shrink_wrap_reject = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    shrink_wrap_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    co2_utilization_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # OEE Metrics
    availability = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    performance = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    quality = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    oee = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Metadata
    calculated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Report for {self.production_run.production_batch_number}"
    
    @property
    def oee_grade(self):
        """Return OEE grade based on industry standards"""
        if not self.oee:
            return "No Data"
        
        oee_value = float(self.oee)
        if oee_value >= 85:
            return "World Class"
        elif oee_value >= 70:
            return "Good"
        elif oee_value >= 50:
            return "Fair"
        else:
            return "Poor"


# ===== SIGNAL HANDLERS FOR AUTO-CALCULATIONS =====

@receiver(post_save, sender=ProductionRun)
def update_production_calculations(sender, instance, created, **kwargs):
    """Auto-update calculations when ProductionRun is saved"""
    if instance.is_completed:
        instance.update_calculations()

@receiver(post_save, sender=PackagingMaterial)
def update_packaging_calculations(sender, instance, created, **kwargs):
    """Update calculations when packaging material is saved"""
    instance.production_run.update_calculations()

@receiver(post_save, sender=Utility)
def update_utility_calculations(sender, instance, created, **kwargs):
    """Update calculations when utility data is saved"""
    instance.production_run.update_calculations()
