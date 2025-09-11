from django import forms
from .models import (
    ProductionRun, PackagingMaterial, Utility, StopEvent,
    ManufacturingOrder, ProductionLine, Product, PackageSize, Shift
)

class ProductionRunForm(forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Apply DaisyUI classes and HTMX attributes to existing widgets
        # This preserves existing values while adding styling and functionality
        
        # Order Number field
        if 'order_number' in self.fields:
            self.fields['order_number'].widget.attrs.update({
                'class': 'select select-bordered w-full',
                'hx-get': '/manufacturing/htmx/product-info/',
                'hx-target': '#product-info',
                'hx-trigger': 'change',
                'hx-swap': 'innerHTML'
            })
        
        # Production Batch Number
        if 'production_batch_number' in self.fields:
            self.fields['production_batch_number'].widget.attrs.update({
                'class': 'input input-bordered w-full',
                'placeholder': 'Enter batch number'
            })
        
        # Date field
        if 'date' in self.fields:
            self.fields['date'].widget = forms.DateInput(attrs={
                'type': 'date',
                'class': 'input input-bordered w-full'
            })
            if self.instance and self.instance.pk and self.instance.date:
                self.fields['date'].widget.attrs['value'] = self.instance.date.strftime('%Y-%m-%d')
        
        # Production Line
        if 'production_line' in self.fields:
            self.fields['production_line'].widget.attrs.update({
                'class': 'select select-bordered w-full'
            })
        
        # Product
        if 'product' in self.fields:
            self.fields['product'].widget.attrs.update({
                'class': 'select select-bordered w-full',
                'hx-get': '/manufacturing/htmx/product-packages/',
                'hx-target': '#package-options',
                'hx-trigger': 'change',
                'hx-swap': 'innerHTML'
            })
        
        # Package Size
        if 'package_size' in self.fields:
            self.fields['package_size'].widget.attrs.update({
                'class': 'select select-bordered w-full'
            })
        
        # Shift
        if 'shift' in self.fields:
            self.fields['shift'].widget.attrs.update({
                'class': 'select select-bordered w-full'
            })
        
        # Production Start
        if 'production_start' in self.fields:
            self.fields['production_start'].widget = forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'input input-bordered w-full'
            })
            if self.instance and self.instance.pk and self.instance.production_start:
                self.fields['production_start'].widget.attrs['value'] = self.instance.production_start.strftime('%Y-%m-%dT%H:%M')
        
        # Production End
        if 'production_end' in self.fields:
            self.fields['production_end'].widget = forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'input input-bordered w-full'
            })
            if self.instance and self.instance.pk and self.instance.production_end:
                self.fields['production_end'].widget.attrs['value'] = self.instance.production_end.strftime('%Y-%m-%dT%H:%M')
        
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
                
        # Filter querysets based on context
        if hasattr(self, 'instance') and self.instance.pk:
            # For updates, keep all options
            pass
        else:
            # For new forms, filter active items only
            self.fields['order_number'].queryset = ManufacturingOrder.objects.filter(
                status__in=['Pending', 'In Progress']
            )
            self.fields['production_line'].queryset = ProductionLine.objects.filter(is_active=True)
            self.fields['product'].queryset = Product.objects.all()
            self.fields['package_size'].queryset = PackageSize.objects.all()
            self.fields['shift'].queryset = Shift.objects.all()
            
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
            'order_number', 'production_batch_number', 'date', 
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
    
    class Meta:
        model = StopEvent
        exclude = ['production_run', 'timestamp']
