from django.shortcuts import render, get_object_or_404

from django.views import View
from django.shortcuts import redirect
from django.http import  HttpResponse

from django.contrib import messages

from datetime import  timedelta

from .pdf_generators import ReportPDFGenerator

from .services import ProductionCalculationService
from .mixins import ReportsPermissionMixin
from .forms import (
    DailySummaryForm, WeeklySummaryForm, 
)


class WeeklySummaryPDFView(ReportsPermissionMixin, View):
    """Generate PDF version of weekly summary"""
    
    def get(self, request, *args, **kwargs):
        # Reuse the same logic from WeeklySummaryView
        form = WeeklySummaryForm(request.GET or None)
        
        if not form.is_valid():
            messages.error(request, "Please provide valid filter parameters")
            return redirect('reports:weekly_summary')
        
        # Get the same context data
        week_start_date = form.cleaned_data['week_start_date']
        production_line = form.cleaned_data['production_line']
        week_end_date = week_start_date + timedelta(days=6)
        
        # Check if there's data for the date range
        summary = ProductionCalculationService.calculate_weekly_summary(
            week_start_date, production_line
        )
        
        if not summary:
            messages.error(request, "No production data found for the selected date range. Cannot generate PDF report.")
            return redirect('reports:weekly_summary')
        
        context = {
            'summary': summary,
            'product_trend': ProductionCalculationService.calculate_product_trend(
                week_start_date, week_end_date, production_line
            ),
            'product_summary': ProductionCalculationService.calculate_product_summary_by_line_product_package(
                week_start_date, week_end_date, production_line
            ),
            'form': form,
        }
        
        # Generate PDF with fallback support
        pdf_bytes = ReportPDFGenerator.generate_weekly_pdf_with_fallback(context)
        
        # Return PDF response
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"weekly_report_{week_start_date.strftime('%Y%m%d')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response


class ShiftSummaryPDFView(ReportsPermissionMixin, View):
    """Generate PDF version of shift summary"""
    
    def get(self, request, *args, **kwargs):
        # Reuse the same logic from DailySummaryView
        form = DailySummaryForm(request.GET or None)
        
        if not form.is_valid():
            messages.error(request, "Please provide valid filter parameters")
            return redirect('reports:daily_summary')
        
        # Get the same context data
        shift_date = form.cleaned_data['shift_date']
        production_line = form.cleaned_data['production_line']
        shift_type = form.cleaned_data['shift_type']
        
        context = {
            'summary': ProductionCalculationService.calculate_shift_summary(
                shift_date, production_line, shift_type
            ),
            'shift_date': shift_date,
            'selected_line': production_line,
            'selected_shift': shift_type,
            'form': form,
        }
        
        # Generate PDF with fallback support using ReportPDFGenerator
        # We'll create a shift-specific template but use the same PDF generator infrastructure
        pdf_bytes = self._generate_shift_pdf_with_fallback(context)
        
        # Return PDF response
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"shift_report_{shift_date.strftime('%Y%m%d')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    def _generate_shift_pdf_with_fallback(self, context_data: dict) -> bytes:
        """Generate shift PDF using the same infrastructure as weekly reports"""
        try:
            # Try Playwright first (with charts and full styling)
            return self._generate_shift_pdf(context_data)
        except Exception as e:
            # Log the error and raise with more context
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Shift PDF generation failed: {str(e)}")
            raise Exception(f"Shift PDF generation failed: {str(e)}")
    
    def _generate_shift_pdf(self, context_data: dict) -> bytes:
        """Generate shift PDF using Playwright"""
        try:
            from django.template.loader import render_to_string
            import asyncio
            # Create a PDF-optimized template
            html_content = render_to_string('reports/pdf/shift_summary_pdf.html', context_data)
            return asyncio.run(ReportPDFGenerator.generate_pdf_from_html(html_content))
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Shift PDF generation failed: {str(e)}")
            raise Exception(f"Shift PDF generation failed: {str(e)}")