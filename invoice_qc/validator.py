"""
Validation module for invoice quality control.
Implements business rules and data quality checks.
"""

from typing import List, Set
from datetime import datetime
from .models import (
    Invoice, 
    ValidationError, 
    InvoiceValidationResult, 
    ValidationSummary,
    ValidationReport
)


class InvoiceValidator:
    """Validates invoices against defined business rules."""
    
    # Supported currencies
    KNOWN_CURRENCIES = {'EUR', 'USD', 'GBP', 'INR', 'JPY', 'CHF'}
    
    def __init__(self):
        """Initialize validator."""
        self.seen_invoices: Set[str] = set()
    
    def validate_batch(self, invoices: List[Invoice]) -> ValidationReport:
        """
        Validate a batch of invoices.
        
        Args:
            invoices: List of Invoice objects to validate
            
        Returns:
            ValidationReport with summary and individual results
        """
        results = []
        error_counts = {}
        
        # Reset duplicate tracking for new batch
        self.seen_invoices.clear()
        
        for invoice in invoices:
            result = self.validate_invoice(invoice)
            results.append(result)
            
            # Count errors
            for error in result.errors:
                error_key = f"{error.rule}:{error.message.split()[0]}"
                error_counts[error_key] = error_counts.get(error_key, 0) + 1
        
        # Calculate summary
        valid_count = sum(1 for r in results if r.is_valid)
        invalid_count = len(results) - valid_count
        
        summary = ValidationSummary(
            total_invoices=len(invoices),
            valid_invoices=valid_count,
            invalid_invoices=invalid_count,
            error_counts=error_counts
        )
        
        return ValidationReport(
            summary=summary,
            results=results
        )
    
    def validate_invoice(self, invoice: Invoice) -> InvoiceValidationResult:
        """
        Validate a single invoice against all rules.
        
        Args:
            invoice: Invoice object to validate
            
        Returns:
            InvoiceValidationResult with validation status and errors
        """
        errors = []
        
        # Completeness rules
        errors.extend(self._check_completeness(invoice))
        
        # Format/Type rules
        errors.extend(self._check_formats(invoice))
        
        # Business rules
        errors.extend(self._check_business_rules(invoice))
        
        # Anomaly/Duplicate rules
        errors.extend(self._check_anomalies(invoice))
        
        invoice_id = invoice.invoice_number or "UNKNOWN"
        
        return InvoiceValidationResult(
            invoice_id=invoice_id,
            source_file=invoice.source_file,
            is_valid=len(errors) == 0,
            errors=errors
        )
    
    def _check_completeness(self, invoice: Invoice) -> List[ValidationError]:
        """Check completeness rules."""
        errors = []
        
        # Rule 1: invoice_number required
        if not invoice.invoice_number or invoice.invoice_number.strip() == "":
            errors.append(ValidationError(
                rule="completeness",
                message="invoice_number is missing or empty",
                severity="error"
            ))
        
        # Rule 2: invoice_date required
        if not invoice.invoice_date or invoice.invoice_date.strip() == "":
            errors.append(ValidationError(
                rule="completeness",
                message="invoice_date is missing or empty",
                severity="error"
            ))
        
        # Rule 3: parties required
        if not invoice.buyer_name or invoice.buyer_name.strip() == "":
            errors.append(ValidationError(
                rule="completeness",
                message="buyer_name is missing or empty",
                severity="error"
            ))
        
        if not invoice.seller_name or invoice.seller_name.strip() == "":
            errors.append(ValidationError(
                rule="completeness",
                message="seller_name is missing or empty",
                severity="error"
            ))
        
        # Rule 4: currency required
        if not invoice.currency or invoice.currency.strip() == "":
            errors.append(ValidationError(
                rule="completeness",
                message="currency is missing or empty",
                severity="error"
            ))
        
        return errors
    
    def _check_formats(self, invoice: Invoice) -> List[ValidationError]:
        """Check format and type rules."""
        errors = []
        
        # Rule 5: Date format validation
        for date_field in ['invoice_date', 'due_date', 'delivery_date']:
            date_value = getattr(invoice, date_field, None)
            if date_value and date_value not in ['sofort', 'ASAP']:
                if not self._is_valid_date(date_value):
                    errors.append(ValidationError(
                        rule="format",
                        message=f"{date_field} has invalid format: {date_value}",
                        severity="error"
                    ))
        
        # Rule 6: Currency in known set
        if invoice.currency and invoice.currency not in self.KNOWN_CURRENCIES:
            errors.append(ValidationError(
                rule="format",
                message=f"currency '{invoice.currency}' not in known set {self.KNOWN_CURRENCIES}",
                severity="warning"
            ))
        
        # Rule 7: Amounts non-negative
        for amount_field in ['net_total', 'tax_amount', 'gross_total']:
            amount_value = getattr(invoice, amount_field, None)
            if amount_value is not None and amount_value < 0:
                errors.append(ValidationError(
                    rule="format",
                    message=f"{amount_field} is negative: {amount_value}",
                    severity="error"
                ))
        
        return errors
    
    def _check_business_rules(self, invoice: Invoice) -> List[ValidationError]:
        """Check business logic rules."""
        errors = []
        
        # Rule 8: Line items sum matches net total
        if invoice.line_items and invoice.net_total is not None:
            line_items_sum = sum(item.line_total for item in invoice.line_items)
            tolerance = invoice.net_total * 0.01  # 1% tolerance
            
            if abs(line_items_sum - invoice.net_total) > tolerance:
                errors.append(ValidationError(
                    rule="business_rule",
                    message=f"line_items sum ({line_items_sum:.2f}) does not match net_total ({invoice.net_total:.2f})",
                    severity="error"
                ))
        
        # Rule 9: Tax calculation validation
        if all([invoice.net_total is not None, 
                invoice.tax_amount is not None, 
                invoice.gross_total is not None]):
            expected_gross = invoice.net_total + invoice.tax_amount
            tolerance = 0.02  # Allow 2 cent rounding difference
            
            if abs(expected_gross - invoice.gross_total) > tolerance:
                errors.append(ValidationError(
                    rule="business_rule",
                    message=f"tax calculation mismatch: net ({invoice.net_total:.2f}) + tax ({invoice.tax_amount:.2f}) != gross ({invoice.gross_total:.2f})",
                    severity="error"
                ))
        
        # Rule 10: Due date logical validation
        if invoice.invoice_date and invoice.due_date:
            if self._is_valid_date(invoice.invoice_date) and self._is_valid_date(invoice.due_date):
                try:
                    inv_date = datetime.fromisoformat(invoice.invoice_date)
                    due_date = datetime.fromisoformat(invoice.due_date)
                    
                    if due_date < inv_date:
                        errors.append(ValidationError(
                            rule="business_rule",
                            message=f"due_date ({invoice.due_date}) is before invoice_date ({invoice.invoice_date})",
                            severity="error"
                        ))
                except:
                    pass  # Date parsing error already caught in format checks
        
        return errors
    
    def _check_anomalies(self, invoice: Invoice) -> List[ValidationError]:
        """Check for anomalies and duplicates."""
        errors = []
        
        # Rule 11: No duplicate invoices
        if invoice.invoice_number and invoice.seller_name and invoice.invoice_date:
            invoice_key = f"{invoice.invoice_number}|{invoice.seller_name}|{invoice.invoice_date}"
            
            if invoice_key in self.seen_invoices:
                errors.append(ValidationError(
                    rule="duplicate",
                    message=f"duplicate invoice detected: {invoice.invoice_number}",
                    severity="error"
                ))
            else:
                self.seen_invoices.add(invoice_key)
        
        # Rule 12: Totals should not be zero
        if invoice.gross_total is not None and invoice.gross_total == 0:
            errors.append(ValidationError(
                rule="anomaly",
                message="gross_total is zero, likely extraction error",
                severity="warning"
            ))
        
        return errors
    
    def _is_valid_date(self, date_str: str) -> bool:
        """Check if a date string is in valid ISO format."""
        if not date_str:
            return False
        
        try:
            # Check ISO format YYYY-MM-DD
            if len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
                datetime.fromisoformat(date_str)
                return True
            return False
        except:
            return False


def validate_invoices(invoices: List[Invoice]) -> ValidationReport:
    """
    Convenience function to validate a list of invoices.
    
    Args:
        invoices: List of Invoice objects
        
    Returns:
        ValidationReport with summary and results
    """
    validator = InvoiceValidator()
    return validator.validate_batch(invoices)