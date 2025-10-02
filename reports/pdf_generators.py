# reports/pdf_generators.py
import asyncio
from playwright.async_api import async_playwright
from django.template.loader import render_to_string
from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse
import tempfile
import os
import logging

logger = logging.getLogger(__name__)

# Try importing WeasyPrint as fallback
try:
    import weasyprint
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    logger.warning("WeasyPrint not available - PDF fallback disabled")

class ReportPDFGenerator:
    @staticmethod
    async def generate_pdf_from_html(html_content: str, css_files: list = None) -> bytes:
        async with async_playwright() as p:
            # Production-optimized browser launch
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox', 
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--no-first-run',
                    '--no-zygote',
                    '--single-process',
                    '--disable-extensions',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding'
                ]
            )
            page = await browser.new_page()
            
            # Set page size and margins
            await page.set_viewport_size({"width": 1200, "height": 800})
            
            # Set longer timeout for production
            page.set_default_timeout(30000)  # 30 seconds
            
            # Load HTML content with better error handling
            try:
                await page.set_content(html_content, wait_until="domcontentloaded", timeout=15000)
            except Exception:
                # Fallback if networkidle fails
                await page.set_content(html_content, wait_until="domcontentloaded")
            
            # Wait for charts to load with conditional check
            try:
                # Check if Chart.js is loaded before waiting
                await page.wait_for_function("typeof Chart !== 'undefined'", timeout=10000)
                await page.wait_for_timeout(3000)  # Wait for charts to render
            except Exception:
                # Continue without charts if they fail to load
                await page.wait_for_timeout(2000)
            
            # Generate PDF with error handling
            try:
                pdf_bytes = await page.pdf(
                    format='A4',
                    print_background=True,
                    margin={'top': '0.5in', 'bottom': '0.5in', 'left': '0.5in', 'right': '0.5in'},
                    landscape=True
                )
            finally:
                await browser.close()
            
            return pdf_bytes

    @staticmethod
    def generate_weekly_pdf(context_data: dict) -> bytes:
        try:
            # Create a PDF-optimized template
            html_content = render_to_string('reports/weekly_summary_pdf.html', context_data)
            return asyncio.run(WeeklyReportPDFGenerator.generate_pdf_from_html(html_content))
        except Exception as e:
            # Log the error and raise with more context
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"PDF generation failed: {str(e)}")
            raise Exception(f"PDF generation failed in production: {str(e)}")
            
    @staticmethod
    async def generate_pdf_with_timeout(html_content: str, timeout: int = 60) -> bytes:
        """Generate PDF with timeout handling for production"""
        try:
            return await asyncio.wait_for(
                WeeklyReportPDFGenerator.generate_pdf_from_html(html_content),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            raise Exception("PDF generation timed out - server may be overloaded")
    
    @staticmethod 
    def generate_fallback_pdf(context_data: dict) -> bytes:
        """Fallback PDF generator using WeasyPrint (no JavaScript support)"""
        if not WEASYPRINT_AVAILABLE:
            raise Exception("WeasyPrint fallback not available - please install weasyprint")
        
        try:
            # Use a simplified template without JavaScript
            html_content = render_to_string('reports/weekly_summary_pdf_simple.html', context_data)
            
            # Generate PDF using WeasyPrint
            pdf_doc = weasyprint.HTML(string=html_content)
            pdf_bytes = pdf_doc.write_pdf()
            
            return pdf_bytes
        except Exception as e:
            logger.error(f"WeasyPrint fallback failed: {str(e)}")
            raise Exception(f"PDF fallback generation failed: {str(e)}")
    
    @staticmethod
    def generate_weekly_pdf_with_fallback(context_data: dict) -> bytes:
        """Try Playwright first, then fallback to WeasyPrint"""
        try:
            # Try Playwright first (with charts and full styling)
            logger.info("Attempting PDF generation with Playwright...")
            return WeeklyReportPDFGenerator.generate_weekly_pdf(context_data)
        except Exception as e:
            logger.warning(f"Playwright failed: {str(e)}, trying WeasyPrint fallback...")
            
            # Fallback to WeasyPrint
            if WEASYPRINT_AVAILABLE:
                try:
                    return WeeklyReportPDFGenerator.generate_fallback_pdf(context_data)
                except Exception as fallback_error:
                    logger.error(f"Both PDF methods failed. Playwright: {str(e)}, WeasyPrint: {str(fallback_error)}")
                    raise Exception(f"PDF generation failed with both methods: {str(e)}")
            else:
                raise Exception(f"PDF generation failed and no fallback available: {str(e)}")