# reports/pdf_generators.py
import asyncio
from playwright.async_api import async_playwright
from django.template.loader import render_to_string
from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse
import tempfile
import os

class WeeklyReportPDFGenerator:
    @staticmethod
    async def generate_pdf_from_html(html_content: str, css_files: list = None) -> bytes:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Set page size and margins
            await page.set_viewport_size({"width": 1200, "height": 800})
            
            # Load HTML content
            await page.set_content(html_content, wait_until="networkidle")
            
            # Wait for charts to load
            await page.wait_for_timeout(3000)  # Wait 3 seconds for Chart.js
            
            # Generate PDF
            pdf_bytes = await page.pdf(
                format='A4',
                print_background=True,
                margin={'top': '0.5in', 'bottom': '0.5in', 'left': '0.5in', 'right': '0.5in'},
                landscape=True  # Better for wide tables
            )
            
            await browser.close()
            return pdf_bytes

    @staticmethod
    def generate_weekly_pdf(context_data: dict) -> bytes:
        # Create a PDF-optimized template
        html_content = render_to_string('reports/weekly_summary_pdf.html', context_data)
        return asyncio.run(WeeklyReportPDFGenerator.generate_pdf_from_html(html_content))