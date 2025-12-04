# invoice_qc/__init__.py
"""
Invoice QC Service - Extract and validate invoice data from PDFs.
"""

__version__ = "1.0.0"

from .extractor import extract_invoices, InvoiceExtractor
from .validator import validate_invoices, InvoiceValidator
from .models import (
    Invoice,
    LineItem,
    ValidationReport,
    ValidationSummary,
    InvoiceValidationResult,
    ValidationError
)

__all__ = [
    'extract_invoices',
    'InvoiceExtractor',
    'validate_invoices',
    'InvoiceValidator',
    'Invoice',
    'LineItem',
    'ValidationReport',
    'ValidationSummary',
    'InvoiceValidationResult',
    'ValidationError',
]

