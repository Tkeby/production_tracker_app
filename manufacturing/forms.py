from django import forms
from django.utils import timezone
from datetime import date
from .models import (
    ProductionRun, PackagingMaterial, Utility, StopEvent,
    ProductionLine, Product, PackageSize, Shift
)

class ProductionRunForm(forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set default values for new instances
        if not self.instance.pk:  # Only for new instances
            self.initial['date'] = date.today()
            self.initial['production_start'] = timezone.now()
            # Don't set production_end default - let it be empty for new runs
        
        # Apply DaisyUI classes and HTMX attributes to existing widgets
        # This preserves existing values while adding styling and functionality
        
        
        # Production Batch Number - Auto-generated, readonly
        if 'production_batch_number' in self.fields:
            self.fields['production_batch_number'].widget.attrs.update({
                'class': 'input input-bordered w-full bg-base-200',
                'readonly': True,
                'placeholder': 'Auto-generated from selected fields'
            })
        
        # Date field
        if 'date' in self.fields:
            widget_attrs = {
                'type': 'date',
                'class': 'input input-bordered w-full',
                'hx-get': '/manufacturing/htmx/generate-batch-number/',
                'hx-target': '#batch-number-container',
                'hx-trigger': 'change',
                'hx-include': '[name="product"], [name="package_size"], [name="shift"], [name="date"], [name="production_line"]'
            }
            
            # Set value based on instance or default
            if self.instance and self.instance.pk and self.instance.date:
                widget_attrs['value'] = self.instance.date.strftime('%Y-%m-%d')
            elif not self.instance.pk:
                widget_attrs['value'] = date.today().strftime('%Y-%m-%d')
                
            self.fields['date'].widget = forms.DateInput(attrs=widget_attrs)
        
        # Production Line
        if 'production_line' in self.fields:
            # First, set up packaging fields HTMX
            packaging_attrs = {
                'class': 'select select-bordered w-full',
                'hx-get': '/manufacturing/htmx/packaging-fields/',
                'hx-target': '#packaging-fields-container',
                'hx-trigger': 'change',
                'hx-swap': 'outerHTML'
            }
            # Add production_run_id for updates to preserve existing data
            if self.instance and self.instance.pk:
                packaging_attrs['hx-include'] = '[name="production_line"], [name="production_run_id"]'
            
            self.fields['production_line'].widget.attrs.update(packaging_attrs)
        
        # Product
        if 'product' in self.fields:
            self.fields['product'].widget.attrs.update({
                'class': 'select select-bordered w-full',
                'hx-get': '/manufacturing/htmx/generate-batch-number/',
                'hx-target': '#batch-number-container',
                'hx-trigger': 'change',
                'hx-include': '[name="product"], [name="package_size"], [name="shift"], [name="date"], [name="production_line"]'
            })
        
        # Package Size
        if 'package_size' in self.fields:
            self.fields['package_size'].widget.attrs.update({
                'class': 'select select-bordered w-full',
                'hx-get': '/manufacturing/htmx/generate-batch-number/',
                'hx-target': '#batch-number-container',
                'hx-trigger': 'change',
                'hx-include': '[name="product"], [name="package_size"], [name="shift"], [name="date"], [name="production_line"]'
            })
        
        # Shift
        if 'shift' in self.fields:
            self.fields['shift'].widget.attrs.update({
                'class': 'select select-bordered w-full',
                'hx-get': '/manufacturing/htmx/generate-batch-number/',
                'hx-target': '#batch-number-container',
                'hx-trigger': 'change',
                'hx-include': '[name="product"], [name="package_size"], [name="shift"], [name="date"], [name="production_line"]'
            })
        
        # Production Start
        if 'production_start' in self.fields:
            widget_attrs = {
                'type': 'datetime-local',
                'class': 'input input-bordered w-full',
                'step': '60'  # Step in seconds (60 = 1 minute)
            }
            
            # Set value based on instance or default
            if self.instance and self.instance.pk and self.instance.production_start:
                widget_attrs['value'] = self.instance.production_start.strftime('%Y-%m-%dT%H:%M')
            elif not self.instance.pk:
                widget_attrs['value'] = timezone.now().strftime('%Y-%m-%dT%H:%M')
                
            self.fields['production_start'].widget = forms.DateTimeInput(attrs=widget_attrs)
        
        # Production End
        if 'production_end' in self.fields:
            widget_attrs = {
                'type': 'datetime-local',
                'class': 'input input-bordered w-full',
                'step': '60'  # Step in seconds (60 = 1 minute)
            }
            
            # Set value only if instance has production_end
            if self.instance and self.instance.pk and self.instance.production_end:
                widget_attrs['value'] = self.instance.production_end.strftime('%Y-%m-%dT%H:%M')
            # Don't set default value for production_end - should be empty for new runs
                
            self.fields['production_end'].widget = forms.DateTimeInput(attrs=widget_attrs)
        
        # Filler Output
        if 'filler_output' in self.fields:
            self.fields['filler_output'].widget.attrs.update({
                'class': 'input input-bordered w-full',
                'step': '0.01',
                'placeholder': '0.00'
            })
        
        # Final Syrup Volume
        if 'final_syrup_volume' in self.fields:
            self.fields['final_syrup_volume'].widget.attrs.update({
                'class': 'input input-bordered join-item flex-1',
                'step': '0.01',
                'placeholder': '0.00'
            })
        
        # Mixing Ratio
        if 'mixing_ratio' in self.fields:
            self.fields['mixing_ratio'].widget.attrs.update({
                'class': 'input input-bordered w-full',
                'placeholder': 'e.g., 1:5'
            })
        
        # Good Products Pack
        if 'good_products_pack' in self.fields:
            self.fields['good_products_pack'].widget.attrs.update({
                'class': 'input input-bordered join-item flex-1',
                'placeholder': '0'
            })
                
        # Filter querysets and handle field states based on context
        if hasattr(self, 'instance') and self.instance.pk:
            # For updates, disable key identifying fields to maintain data integrity
            readonly_fields = ['date', 'production_line', 'product', 'package_size', 'shift']
            
            for field_name in readonly_fields:
                if field_name in self.fields:
                    # Make field disabled and add visual styling
                    self.fields[field_name].disabled = True
                    self.fields[field_name].widget.attrs.update({
                        'class': self.fields[field_name].widget.attrs.get('class', '') + ' cursor-not-allowed opacity-80 bg-base-200',
                        'title': 'This field cannot be changed during updates for data integrity'
                    })
                    # Remove HTMX attributes from disabled fields
                    if 'hx-get' in self.fields[field_name].widget.attrs:
                        del self.fields[field_name].widget.attrs['hx-get']
                    if 'hx-target' in self.fields[field_name].widget.attrs:
                        del self.fields[field_name].widget.attrs['hx-target']
                    if 'hx-trigger' in self.fields[field_name].widget.attrs:
                        del self.fields[field_name].widget.attrs['hx-trigger']
                    if 'hx-include' in self.fields[field_name].widget.attrs:
                        del self.fields[field_name].widget.attrs['hx-include']
        else:
            # For new forms, filter active items only
            self.fields['production_line'].queryset = ProductionLine.objects.filter(is_active=True)
            self.fields['product'].queryset = Product.objects.all()
            self.fields['package_size'].queryset = PackageSize.objects.all()
            self.fields['shift'].queryset = Shift.objects.all()
            
    def clean(self):
        cleaned_data = super().clean()
        
        # Auto-generate batch number if all required fields are present
        product = cleaned_data.get('product')
        package_size = cleaned_data.get('package_size') 
        shift = cleaned_data.get('shift')
        date = cleaned_data.get('date')
        
        production_line = cleaned_data.get('production_line')
        
        if all([product, package_size, shift, date, production_line]):
            # Generate batch number if not editing existing instance
            if not (self.instance and self.instance.pk):
                batch_number = ProductionRun.generate_batch_number(
                    product, package_size, shift, date, production_line
                )
                cleaned_data['production_batch_number'] = batch_number
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user and not instance.shift_teamleader_id:
            instance.shift_teamleader = self.user
        if commit:
            instance.save()
        return instance
    
    class Meta:
        model = ProductionRun
        fields = [
            'production_batch_number', 'date',
            'production_line', 'product', 'package_size', 'shift',
            'production_start', 'production_end', 'filler_output', 'final_syrup_volume',
            'mixing_ratio', 'good_products_pack'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'production_start': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'production_end': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class PackagingMaterialForm(forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        self.production_line = kwargs.pop('production_line', None)
        super().__init__(*args, **kwargs)
        
        # Apply DaisyUI classes to all fields
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.NumberInput):
                field.widget.attrs.update({
                    'class': 'input input-bordered w-full',
                    'step': '0.01' if field_name.endswith('_g') or field_name.endswith('_kg') else '1'
                })
            elif isinstance(field.widget, forms.TextInput):
                field.widget.attrs.update({'class': 'input input-bordered w-full'})
        
        # Conditionally show/hide fields based on production line
        self._setup_conditional_fields()
    
    def _setup_conditional_fields(self):
        """Setup conditional fields based on production line type"""
        if not self.production_line:
            return
            
        line_name = str(self.production_line.name).upper() if hasattr(self.production_line, 'name') else str(self.production_line).upper()
        is_can_line = 'CAN' in line_name
        
        # PET line specific fields
        pet_fields = [
            'qty_preform_used', 'qty_cap_used', 'qty_preform_reject', 
            'qty_bottle_reject', 'qty_cap_reject', 'label_reject_g'
        ]
        
        # Can line specific fields  
        can_fields = [
            'qty_can_used', 'qty_empty_can_reject', 'qty_can_cover_used',
            'qty_can_cover_reject', 'qty_carton_used', 'qty_carton_reject', 
            'qty_filled_can_reject'
        ]
        
        if is_can_line:
            # Hide PET fields for CAN line
            for field in pet_fields:
                if field in self.fields:
                    self.fields[field].widget = forms.HiddenInput()
                    self.fields[field].required = False
        else:
            # Hide CAN fields for other lines  
            for field in can_fields:
                if field in self.fields:
                    self.fields[field].widget = forms.HiddenInput()
                    self.fields[field].required = False
    
    @property
    def pet_fields(self):
        """Return PET line specific fields"""
        return [
            'qty_preform_used', 'qty_cap_used', 'qty_product_reject',
            'qty_preform_reject', 'qty_bottle_reject', 'qty_cap_reject', 'label_reject_g'
        ]
    
    @property 
    def can_fields(self):
        """Return CAN line specific fields"""
        return [
            'qty_can_used', 'qty_empty_can_reject', 'qty_can_cover_used',
            'qty_can_cover_reject', 'qty_carton_used', 'qty_carton_reject',
            'qty_filled_can_reject'
        ]
    
    @property
    def common_fields(self):
        """Return common packaging fields"""
        return [ 'shrink_wrap_kg', 'stretch_wrap_g']
    
    class Meta:
        model = PackagingMaterial
        exclude = ['production_run']

class UtilityForm(forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Apply DaisyUI classes to all fields
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.NumberInput):
                field.widget.attrs.update({
                    'class': 'input input-bordered w-full',
                    'step': '0.01'
                })
            elif isinstance(field.widget, forms.TextInput):
                field.widget.attrs.update({'class': 'input input-bordered w-full'})
    
    class Meta:
        model = Utility
        exclude = ['production_run']

class StopEventForm(forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Apply DaisyUI classes
        self.fields['machine'].widget.attrs.update({'class': 'select select-bordered w-full'})
        self.fields['code'].widget.attrs.update({'class': 'select select-bordered w-full'})
        self.fields['reason'].widget.attrs.update({'class': 'textarea textarea-bordered w-full'})
        self.fields['duration_minutes'].widget.attrs.update({
            'class': 'input input-bordered w-full',
            'placeholder': 'Minutes'
        })
        self.fields['is_planned'].widget.attrs.update({
            'class': 'checkbox checkbox-primary checkbox-lg'
        })
    
    class Meta:
        model = StopEvent
        exclude = ['production_run', 'timestamp']
