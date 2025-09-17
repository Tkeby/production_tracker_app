from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from .models import (
    ProductionRun, ProductionReport, StopEvent,
    ProductionLine, Product, PackageSize, Shift, Machine, DowntimeCode
)
from .forms import ProductionRunForm, PackagingMaterialForm, UtilityForm, StopEventForm

class DashboardView(LoginRequiredMixin, ListView):
    model = ProductionRun
    template_name = 'manufacturing/dashboard.html'
    context_object_name = 'production_runs'
    
    def get_queryset(self):
        return ProductionRun.objects.filter(
            shift_teamleader=self.request.user,
            is_completed=False
        ).order_by('-date', '-production_start')

class CreateProductionRunView(LoginRequiredMixin, CreateView):
    model = ProductionRun
    form_class = ProductionRunForm
    template_name = 'manufacturing/create_production_run.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        production_line = None
        
        if self.request.POST:
            # Try to get production line from POST data
            production_line_id = self.request.POST.get('production_line')
            if production_line_id:
                try:
                    production_line = ProductionLine.objects.get(id=production_line_id)
                except ProductionLine.DoesNotExist:
                    pass
            
            context['packaging_form'] = PackagingMaterialForm(
                self.request.POST, 
                production_line=production_line
            )
            context['utility_form'] = UtilityForm(self.request.POST)
        else:
            context['packaging_form'] = PackagingMaterialForm(production_line=production_line)
            context['utility_form'] = UtilityForm()
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        packaging_form = context['packaging_form']
        utility_form = context['utility_form']
        
        # Check if all forms are valid
        if form.is_valid() and packaging_form.is_valid() and utility_form.is_valid():
            # Save the main production run first
            self.object = form.save()
            
            # Save related models with the production run instance
            packaging = packaging_form.save(commit=False)
            packaging.production_run = self.object
            packaging.save()
            
            utility = utility_form.save(commit=False)
            utility.production_run = self.object
            utility.save()
            
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))
    
    def get_success_url(self):
        return reverse_lazy('manufacturing:production_run_detail', kwargs={'pk': self.object.pk})

class ProductionRunDetailView(LoginRequiredMixin, DetailView):
    model = ProductionRun
    template_name = 'manufacturing/production_run_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['packaging_form'] = PackagingMaterialForm()
        context['utility_form'] = UtilityForm()
        return context

class UpdateProductionRunView(LoginRequiredMixin, UpdateView):
    model = ProductionRun
    form_class = ProductionRunForm
    template_name = 'manufacturing/update_production_run.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_queryset(self):
        return ProductionRun.objects.filter(shift_teamleader=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Debug: Print the object to console
        if self.object:
            print(f"DEBUG: Loading update form for ProductionRun {self.object.pk}")
            print(f"  - Batch: {self.object.production_batch_number}")
            print(f"  - Date: {self.object.date}")
            print(f"  - Start: {self.object.production_start}")
            print(f"  - End: {self.object.production_end}")
            print(f"  - Product: {self.object.product}")
            print(f"  - Line: {self.object.production_line}")
            print(f"  - Package: {self.object.package_size}")
        
        # Get or create related instances for editing
        try:
            packaging_instance = self.object.packaging_material
        except:
            packaging_instance = None
            
        try:
            utility_instance = self.object.utility
        except:
            utility_instance = None
        
        # Get production line for conditional field display
        production_line = None
        if self.request.POST:
            # Try to get production line from POST data
            production_line_id = self.request.POST.get('production_line')
            if production_line_id:
                try:
                    production_line = ProductionLine.objects.get(id=production_line_id)
                except ProductionLine.DoesNotExist:
                    pass
        else:
            # Get from current object
            production_line = self.object.production_line if self.object else None

        if self.request.POST:
            context['packaging_form'] = PackagingMaterialForm(
                self.request.POST, 
                instance=packaging_instance,
                production_line=production_line
            )
            context['utility_form'] = UtilityForm(self.request.POST, instance=utility_instance)
        else:
            context['packaging_form'] = PackagingMaterialForm(
                instance=packaging_instance,
                production_line=production_line
            )
            context['utility_form'] = UtilityForm(instance=utility_instance)
        
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        packaging_form = context['packaging_form']
        utility_form = context['utility_form']
        
        # Check if all forms are valid
        if form.is_valid() and packaging_form.is_valid() and utility_form.is_valid():
            # Save the main production run first
            self.object = form.save()
            
            # Save related models with the production run instance
            packaging = packaging_form.save(commit=False)
            packaging.production_run = self.object
            packaging.save()
            
            utility = utility_form.save(commit=False)
            utility.production_run = self.object
            utility.save()
            
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))
    
    def get_success_url(self):
        return reverse_lazy('manufacturing:production_run_detail', kwargs={'pk': self.object.pk})

class ReportsListView(LoginRequiredMixin, ListView):
    model = ProductionReport
    template_name = 'manufacturing/reports_list.html'
    context_object_name = 'reports'
    paginate_by = 20
    
    def get_queryset(self):
        return ProductionReport.objects.filter(
            production_run__shift_teamleader=self.request.user
        ).order_by('-production_run__date')

class FinalizeProductionRunView(LoginRequiredMixin, View):
    def post(self, request, pk):
        production_run = get_object_or_404(ProductionRun, pk=pk)
        
        if production_run.shift_teamleader != request.user:
            messages.error(request, "You can only finalize your own production runs.")
            return redirect('manufacturing:dashboard')
        
        try:
            # Update calculations before finalizing
            production_run.production_end = timezone.now() if not production_run.production_end else production_run.production_end
            production_run.is_completed = True
            production_run.save()
            
            # This will trigger the signal to update calculations
            report = production_run.update_calculations()
            messages.success(request, "Production run finalized successfully!")
            return redirect('manufacturing:production_run_detail', pk=pk)
        except Exception as e:
            messages.error(request, f"Error finalizing production run: {str(e)}")
            return redirect('manufacturing:production_run_detail', pk=pk)

class CreateStopEventView(LoginRequiredMixin, CreateView):
    model = StopEvent
    form_class = StopEventForm
    template_name = 'manufacturing/create_stop_event.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.production_run = get_object_or_404(ProductionRun, pk=kwargs['production_run_pk'])
        
        # Check if user has permission to add stop events to this production run
        if self.production_run.shift_teamleader != request.user:
            messages.error(request, "You can only add stop events to your own production runs.")
            return redirect('manufacturing:dashboard')
            
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['production_run'] = self.production_run
        
        # Filter machines to only show those from the production run's line
        machines = Machine.objects.filter(
            production_line=self.production_run.production_line,
            is_active=True
        )
        context['machines'] = machines
        
        return context
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        
        # Filter machines to only show those from the production run's line
        form.fields['machine'].queryset = Machine.objects.filter(
            production_line=self.production_run.production_line,
            is_active=True
        )
        
        # Filter codes to show all initially (will be filtered by HTMX)
        form.fields['code'].queryset = DowntimeCode.objects.all()
        
        # Add HTMX attributes for dynamic filtering
        form.fields['machine'].widget.attrs.update({
            'hx-get': reverse_lazy('manufacturing:htmx_machine_codes'),
            'hx-target': '#id_code',
            'hx-trigger': 'change'
        })
        
        return form
    
    def form_valid(self, form):
        form.instance.production_run = self.production_run
        messages.success(self.request, 'Stop event added successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('manufacturing:production_run_detail', kwargs={'pk': self.production_run.pk})




def htmx_product_packages(request):
    """Get package sizes available for a product"""
    product_id = request.GET.get('product')
    packages = PackageSize.objects.all()
    
    if product_id:
        try:
            product = Product.objects.get(id=product_id)
            # You can filter packages based on product if needed
            # packages = PackageSize.objects.filter(product=product)
        except Product.DoesNotExist:
            pass
    
    html = render_to_string('manufacturing/htmx/package_options.html', {
        'packages': packages
    })
    return HttpResponse(html)

def htmx_machine_codes(request):
    """Get downtime codes for a specific machine"""
    machine_id = request.GET.get('machine')
    codes = []
    
    if machine_id:
        try:
            from .models import Machine, DowntimeCode
            machine = Machine.objects.get(id=machine_id)
            codes = DowntimeCode.objects.filter(machine=machine)
        except:
            pass
    
    html = render_to_string('manufacturing/htmx/downtime_codes.html', {
        'codes': codes
    })
    return HttpResponse(html)

def htmx_packaging_fields(request):
    """Get packaging fields based on production line type"""
    production_line_id = request.GET.get('production_line')
    production_run_id = request.GET.get('production_run_id') or request.POST.get('production_run_id')  # For updates
    production_line = None
    packaging_instance = None
    
    if production_line_id:
        try:
            production_line = ProductionLine.objects.get(id=production_line_id)
        except ProductionLine.DoesNotExist:
            pass
    
    # Get existing packaging data if updating
    if production_run_id:
        try:
            production_run = ProductionRun.objects.get(id=production_run_id)
            try:
                packaging_instance = production_run.packaging_material
            except:
                packaging_instance = None
        except ProductionRun.DoesNotExist:
            pass
    
    # Create packaging form with the selected production line and instance
    packaging_form = PackagingMaterialForm(
        production_line=production_line,
        instance=packaging_instance
    )
    
    html = render_to_string('manufacturing/htmx/packaging_fields.html', {
        'packaging_form': packaging_form,
        'production_line': production_line
    })
    return HttpResponse(html)

def htmx_generate_batch_number(request):
    """Generate batch number based on selected form fields"""
    from datetime import datetime
    from .models import Product, PackageSize, Shift
    
    # Get form parameters
    product_id = request.GET.get('product')
    package_size_id = request.GET.get('package_size') 
    shift_id = request.GET.get('shift')
    date_str = request.GET.get('date')
    
    batch_number = ""
    
    try:
        # Parse components
        product = Product.objects.get(id=product_id) if product_id else None
        package_size = PackageSize.objects.get(id=package_size_id) if package_size_id else None
        shift = Shift.objects.get(id=shift_id) if shift_id else None
        
        # Parse date
        date_obj = None
        if date_str:
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # Generate batch number if all components are available
        if all([product, package_size, shift, date_obj]):
            batch_number = ProductionRun.generate_batch_number(
                product, package_size, shift, date_obj
            )
            
    except (Product.DoesNotExist, PackageSize.DoesNotExist, Shift.DoesNotExist):
        pass
    
    html = render_to_string('manufacturing/htmx/batch_number.html', {
        'batch_number': batch_number
    })
    return HttpResponse(html)
