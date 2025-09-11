from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from .models import (
    ProductionRun, ProductionReport, ManufacturingOrder, 
    ProductionLine, Product, PackageSize, Shift
)
from .forms import ProductionRunForm, PackagingMaterialForm, UtilityForm

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
        if self.request.POST:
            context['packaging_form'] = PackagingMaterialForm(self.request.POST)
            context['utility_form'] = UtilityForm(self.request.POST)
        else:
            context['packaging_form'] = PackagingMaterialForm()
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
            print(f"  - Order: {self.object.order_number}")
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
        
        if self.request.POST:
            context['packaging_form'] = PackagingMaterialForm(self.request.POST, instance=packaging_instance)
            context['utility_form'] = UtilityForm(self.request.POST, instance=utility_instance)
        else:
            context['packaging_form'] = PackagingMaterialForm(instance=packaging_instance)
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


# HTMX Views for Dynamic Form Updates
def htmx_product_info(request):
    """Update product and package size fields based on manufacturing order"""
    order_id = request.GET.get('order_number')
    
    # Debug logging
    print(f"DEBUG: HTMX product_info called with order_id: {order_id}")
    
    context = {
        'selected_product': None,
        'selected_package': None,
        'products': Product.objects.all(),
        'packages': PackageSize.objects.all(),
        'order_info': None
    }
    
    if order_id:
        try:
            order = ManufacturingOrder.objects.get(id=order_id)
            print(f"DEBUG: Found order: {order.order_number}, product: {order.product.name}, package: {order.package_size}")
            context.update({
                'selected_product': order.product,
                'selected_package': order.package_size,
                'order_info': {
                    'product_name': order.product.name,
                    'package_size': f"{order.package_size.size} {order.package_size.get_package_type_display()}",
                    'quantity': order.quantity
                }
            })
        except ManufacturingOrder.DoesNotExist:
            print(f"DEBUG: Manufacturing order with id {order_id} not found")
    else:
        print("DEBUG: No order_id provided")
    
    html = render_to_string('manufacturing/htmx/order_product_update.html', context)
    print(f"DEBUG: Returning HTML length: {len(html)}")
    return HttpResponse(html)


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
