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
        return f"{self.name} ({self.product_code})"

class PackageSize(models.Model):
    PACKAGE_TYPES = [
        ('PET', 'PET Bottle'),
        ('CAN', 'Can'),
    ]
    
    size = models.CharField(max_length=50)  # e.g., "500ml", "1L"
    package_type = models.CharField(max_length=10, choices=PACKAGE_TYPES)
    volume_ml = models.PositiveIntegerField(help_text="Volume in milliliters",default=500)
    
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

    def __str__(self):
        return f"{self.machine_name} ({self.machine_code})"
    
    class Meta:
        verbose_name = "Machine"
        verbose_name_plural = "Machines"
        unique_together = ['production_line', 'machine_name']

class DowntimeCode(models.Model):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE)
    code = models.CharField(max_length=100, unique=True)
    reason = models.TextField(blank=True)

    def __str__(self):
        return f"{self.code} - {self.reason}"

class ManufacturingOrder(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]
    order_number = models.CharField(max_length=100, unique=True)
    order_date = models.DateField()
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    package_size = models.ForeignKey(PackageSize, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(help_text="Quantity of the product to be manufactured in packs")
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.order_number} - {self.product.name}"
    
    class Meta:
        verbose_name = "Manufacturing Order"
        verbose_name_plural = "Manufacturing Orders"

class ProductionRun(models.Model):
    """Main model representing a single production run"""
    # Basic Information
    order_number = models.ForeignKey(ManufacturingOrder, on_delete=models.CASCADE)
    production_batch_number = models.CharField(max_length=100)
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
    mixing_ratio = models.CharField(max_length=50)
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
    
    # ===== CALCULATION METHODS =====
    
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
    
    def calculate_availability(self):
        """Calculate availability = (Planned Production Time - Downtime) / Planned Production Time"""
        planned_time = self.planned_production_time_minutes
        if planned_time <= 0:
            return Decimal('0.00')
        
        actual_runtime = planned_time - self.total_downtime_minutes
        return Decimal(actual_runtime / planned_time * 100).quantize(Decimal('0.01'))
    
    def calculate_performance(self):
        """Calculate performance = (Actual Output / Rated Output) * 100"""
        if not hasattr(self, 'production_line') or self.production_duration_minutes <= 0:
            return Decimal('0.00')
        
        # Get the main machine for this production line (first active machine)
        main_machine = self.production_line.machine_set.filter(is_active=True).first()
        if not main_machine:
            return Decimal('0.00')
        
        production_hours = Decimal(self.production_duration_minutes) / Decimal('60')
        theoretical_output = main_machine.rated_output * production_hours
        
        if theoretical_output <= 0:
            return Decimal('0.00')
        
        performance = (Decimal(self.good_products_pack * 12) / theoretical_output * 100)
        return performance.quantize(Decimal('0.01'))
    
    def calculate_quality(self):
        """Calculate quality = Good Products / Total Products Produced"""
        if not hasattr(self, 'packaging_material'):
            return Decimal('0.00')
        
        packaging = self.packaging_material
        total_products = (self.good_products_pack + 
                         packaging.qty_product_reject + 
                         packaging.qty_bottle_reject)
        
        if total_products <= 0:
            return Decimal('0.00')
        
        quality = (Decimal(self.good_products_pack) / Decimal(total_products) * 100)
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
        expected_syrup_l = (Decimal(self.good_products_pack) * 
                           Decimal(self.package_size.volume_ml) * 
                           self.product.standard_syrup_ratio) / 1000
        
        if expected_syrup_l <= 0:
            return Decimal('0.00')
        
        yield_percentage = (self.final_syrup_volume / expected_syrup_l * 100)
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
            total_preforms = packaging.qty_preform_used + packaging.qty_preform_reject
            if total_preforms > 0:
                report.preform_yield_percentage = Decimal(
                    (packaging.qty_preform_used / total_preforms) * 100
                ).quantize(Decimal('0.01'))
            
            # Bottle reject percentage
            total_bottles = self.good_products_pack + packaging.qty_bottle_reject
            if total_bottles > 0:
                report.bottle_reject_percentage = Decimal(
                    (packaging.qty_bottle_reject / total_bottles) * 100
                ).quantize(Decimal('0.01'))
        
        # Calculate utility metrics if utility data exists
        if hasattr(self, 'utility'):
            utility = self.utility
            
            # CO2 utilization (example calculation)
            if self.good_products_pack > 0 and utility.kg_co2 > 0:
                expected_co2 = Decimal(self.good_products_pack) * Decimal('0.1')  # Example: 0.1kg per pack
                report.co2_utilization_percentage = Decimal(
                    (expected_co2 / utility.kg_co2) * 100
                ).quantize(Decimal('0.01'))
        
        report.save()
        return report

class PackagingMaterial(models.Model):
    """Packaging materials used in a production run"""
    production_run = models.OneToOneField(ProductionRun, on_delete=models.CASCADE, related_name='packaging_material')
    
    qty_preform_used = models.PositiveIntegerField(blank=True, null=True)
    qty_cap_used = models.PositiveIntegerField(blank=True, null=True)
    qty_product_reject = models.PositiveIntegerField(blank=True, null=True)
    qty_preform_reject = models.PositiveIntegerField(blank=True, null=True)
    qty_bottle_reject = models.PositiveIntegerField(blank=True, null=True)
    qty_cap_reject = models.PositiveIntegerField(blank=True, null=True)
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
    reason = models.TextField()
    duration_minutes = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.machine.machine_name} - {self.code} ({self.duration_minutes}min)"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update total downtime in production run
        self.production_run.total_downtime_minutes = sum(
            self.production_run.stop_events.values_list('duration_minutes', flat=True)
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
