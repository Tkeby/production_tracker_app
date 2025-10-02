from django import forms
from django.utils import timezone
from datetime import date, timedelta
from manufacturing.models import ProductionLine, Machine


class ReportFilterForm(forms.Form):
    """Base form for report filters"""
    
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'input input-bordered w-full'
        }),
        initial=lambda: date.today() - timedelta(days=7)
    )
    
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'input input-bordered w-full'
        }),
        initial=date.today
    )
    
    production_line = forms.ModelChoiceField(
        queryset=ProductionLine.objects.filter(is_active=True),
        required=False,
        empty_label="All Production Lines",
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'})
    )
    
    machine = forms.ModelChoiceField(
        queryset=Machine.objects.filter(is_active=True),
        required=False,
        empty_label="All Machines",
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Keep all machines initially - filtering will be handled by JavaScript/AJAX
        self.fields['machine'].queryset = Machine.objects.filter(is_active=True)
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        production_line = cleaned_data.get('production_line')
        machine = cleaned_data.get('machine')
        
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("Start date must be before end date.")
        
        # Validate that machine belongs to selected production line
        if production_line and machine and machine.production_line != production_line:
            raise forms.ValidationError("Selected machine must belong to the selected production line.")
        
        return cleaned_data


class DailySummaryForm(forms.Form):
    """Form for daily summary report"""
    
    SHIFT_CHOICES = [
        ('', 'All Shifts'),
        ('8H_SHIFT_1', '8H Shift 1'),
        ('8H_SHIFT_2', '8H Shift 2'),
        ('8H_SHIFT_3', '8H Shift 3'),
        ('12H_SHIFT_1', '12H Shift 1'),
        ('12H_SHIFT_2', '12H Shift 2'),
    ]
    
    shift_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'input input-bordered w-full'
        }),
        initial=date.today
    )
    
    production_line = forms.ModelChoiceField(
        queryset=ProductionLine.objects.filter(is_active=True),
        required=False,
        empty_label="All Production Lines",
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'})
    )
    
    shift_type = forms.ChoiceField(
        choices=SHIFT_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'})
    )





class WeeklySummaryForm(forms.Form):
    """Form for weekly summary report"""
    
    week_start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'input input-bordered w-full'
        }),
        initial=lambda: date.today() - timedelta(days=date.today().weekday())
    )
    
    production_line = forms.ModelChoiceField(
        queryset=ProductionLine.objects.filter(is_active=True),
        required=False,
        empty_label="All Production Lines",
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'})
    )


class DowntimeAnalysisForm(ReportFilterForm):
    """Form for downtime analysis with additional limit field"""
    
    limit = forms.IntegerField(
        initial=10,
        min_value=1,
        max_value=50,
        widget=forms.NumberInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Top N reasons'
        })
    )


class MachineUtilizationForm(ReportFilterForm):
    """Form for machine utilization - requires production line selection"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['production_line'].required = True
        self.fields['production_line'].empty_label = "Select Production Line"
