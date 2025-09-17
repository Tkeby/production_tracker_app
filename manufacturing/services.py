from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from .models import ProductionRun, ProductionReport, ProductionLine


class ProductionCalculationService:
    """Moved to reports.services.py"""
    
    pass