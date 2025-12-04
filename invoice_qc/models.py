"""
Data models for invoice extraction and validation.
Uses Pydantic for data validation and serialization.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class LineItem(BaseModel):
    """Represents a single line item in an invoice."""
    position: int = Field(description="Line position number")
    description: str = Field(description="Item description")
    article_number: Optional[str] = Field(default=None, description="Product/article ID")
    quantity: float = Field(description="Quantity ordered")
    unit: str = Field(default="VE", description="Unit of measurement")
    unit_price: float = Field(description="Price per unit")
    line_total: float = Field(description="Total for this line")

    class Config:
        json_schema_extra = {
            "example": {
                "position": 1,
                "description": "USB-Maus",
                "article_number": "000252944C",
                "quantity": 4.0,
                "unit": "VE",
                "unit_price": 16.0,
                "line_total": 64.0
            }
        }


class Invoice(BaseModel):
    """Represents a complete invoice with all extracted fields."""
    
    # Identifiers
    invoice_number: Optional[str] = Field(default=None, description="Primary invoice identifier")
    customer_number: Optional[str] = Field(default=None, description="Customer ID")
    order_reference: Optional[str] = Field(default=None, description="External order reference")
    
    # Parties
    buyer_name: Optional[str] = Field(default=None, description="Buyer company name")
    buyer_address: Optional[str] = Field(default=None, description="Buyer full address")
    seller_name: Optional[str] = Field(default=None, description="Seller company name")
    seller_address: Optional[str] = Field(default=None, description="Seller full address")
    
    # Dates
    invoice_date: Optional[str] = Field(default=None, description="Invoice date (ISO format)")
    due_date: Optional[str] = Field(default=None, description="Payment due date (ISO format)")
    delivery_date: Optional[str] = Field(default=None, description="Requested delivery date")
    
    # Financial
    currency: Optional[str] = Field(default="EUR", description="Currency code")
    net_total: Optional[float] = Field(default=None, description="Total before tax")
    tax_rate: Optional[float] = Field(default=None, description="Tax percentage")
    tax_amount: Optional[float] = Field(default=None, description="Tax amount")
    gross_total: Optional[float] = Field(default=None, description="Total including tax")
    
    # Payment
    payment_terms: Optional[str] = Field(default=None, description="Payment terms")
    
    # Line items
    line_items: List[LineItem] = Field(default_factory=list, description="List of line items")
    
    # Metadata
    source_file: Optional[str] = Field(default=None, description="Original PDF filename")

    @field_validator('invoice_date', 'due_date', 'delivery_date')
    @classmethod
    def validate_date_format(cls, v):
        """Ensure dates are in ISO format or None."""
        if v is None:
            return v
        # If already in ISO format, return as-is
        if isinstance(v, str) and len(v) == 10 and v[4] == '-' and v[7] == '-':
            return v
        # Try to parse and convert to ISO
        try:
            # Handle German format DD.MM.YYYY
            if '.' in v:
                parts = v.split('.')
                if len(parts) == 3:
                    day, month, year = parts
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            return v
        except:
            return v

    class Config:
        json_schema_extra = {
            "example": {
                "invoice_number": "AUFNR34343",
                "customer_number": "7654321",
                "order_reference": "3498578433",
                "buyer_name": "Beispielname Unternehmen",
                "buyer_address": "Albertus-Magnus-Str. 8, Matternfeld, SL 44624, Deutschland",
                "seller_name": "ABC Corporation",
                "seller_address": "Industriestraße 3, 12345 Köln",
                "invoice_date": "2024-05-22",
                "due_date": "2024-05-22",
                "delivery_date": "sofort",
                "currency": "EUR",
                "net_total": 64.0,
                "tax_rate": 19.0,
                "tax_amount": 12.16,
                "gross_total": 76.16,
                "payment_terms": "0 Tage 2,0% Skonto",
                "line_items": [
                    {
                        "position": 1,
                        "description": "Sterilisationsmittel",
                        "article_number": "000253655G",
                        "quantity": 4.0,
                        "unit": "VE",
                        "unit_price": 16.0,
                        "line_total": 64.0
                    }
                ]
            }
        }


class ValidationError(BaseModel):
    """Represents a single validation error."""
    rule: str = Field(description="Rule that failed")
    message: str = Field(description="Human-readable error message")
    severity: str = Field(default="error", description="error, warning, or info")


class InvoiceValidationResult(BaseModel):
    """Validation result for a single invoice."""
    invoice_id: str = Field(description="Invoice identifier")
    source_file: Optional[str] = Field(default=None, description="Original PDF filename")
    is_valid: bool = Field(description="Whether invoice passed all validations")
    errors: List[ValidationError] = Field(default_factory=list, description="List of validation errors")
    
    class Config:
        json_schema_extra = {
            "example": {
                "invoice_id": "AUFNR34343",
                "source_file": "sample_pdf_1.pdf",
                "is_valid": False,
                "errors": [
                    {
                        "rule": "missing_field",
                        "message": "buyer_address is missing or empty",
                        "severity": "error"
                    }
                ]
            }
        }


class ValidationSummary(BaseModel):
    """Summary statistics for batch validation."""
    total_invoices: int = Field(description="Total number of invoices processed")
    valid_invoices: int = Field(description="Number of valid invoices")
    invalid_invoices: int = Field(description="Number of invalid invoices")
    error_counts: dict = Field(default_factory=dict, description="Count of each error type")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_invoices": 3,
                "valid_invoices": 2,
                "invalid_invoices": 1,
                "error_counts": {
                    "missing_field:buyer_address": 1,
                    "business_rule:totals_mismatch": 1
                }
            }
        }


class ValidationReport(BaseModel):
    """Complete validation report with summary and individual results."""
    summary: ValidationSummary
    results: List[InvoiceValidationResult]
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    class Config:
        json_schema_extra = {
            "example": {
                "summary": {
                    "total_invoices": 3,
                    "valid_invoices": 2,
                    "invalid_invoices": 1,
                    "error_counts": {"missing_field:buyer_address": 1}
                },
                "results": [],
                "timestamp": "2024-01-10T10:30:00"
            }
        }