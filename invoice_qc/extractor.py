"""
PDF extraction module for invoices.
Extracts structured data from PDF invoices using pdfplumber and regex.
"""

import re
import pdfplumber
from pathlib import Path
from typing import List, Optional, Dict, Any
from .models import Invoice, LineItem


class InvoiceExtractor:
    """Extracts structured invoice data from PDF files."""
    
    # Regex patterns for German invoices
    PATTERNS = {
        'invoice_number': r'(?:Bestellung|AUFNR)\s*(\w+)',
        'order_reference': r'im Auftrag von\s*(\d+)',
        'customer_number': r'Unsere Kundennummer[\s\n]+(\d+)',
        'invoice_date': r'vom\s*(\d{2}\.\d{2}\.\d{4})',
        'tax_rate': r'MwSt\.\s*(\d+[,.]?\d*)%',
        'net_total': r'Gesamtwert\s+EUR\s+(\d+[,.]?\d*)',
        'tax_amount': r'MwSt\.\s+\d+[,.]?\d*%\s+EUR\s+(\d+[,.]?\d*)',
        'gross_total': r'Gesamtwert inkl\. MwSt\.\s+EUR\s+(\d+[,.]?\d*)',
        'payment_terms': r'Zahlungsbedingungen[\s\n]+([^\n]+)',
        'delivery_date': r'Gewünschtes Lieferdatum[\s\n]+([^\n]+)',
    }
    
    def __init__(self):
        """Initialize the extractor."""
        pass
    
    def extract_from_directory(self, pdf_dir: str) -> List[Invoice]:
        """
        Extract invoices from all PDFs in a directory.
        
        Args:
            pdf_dir: Path to directory containing PDF files
            
        Returns:
            List of Invoice objects
        """
        pdf_path = Path(pdf_dir)
        invoices = []
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"Directory not found: {pdf_dir}")
        
        pdf_files = list(pdf_path.glob("*.pdf"))
        
        if not pdf_files:
            print(f"Warning: No PDF files found in {pdf_dir}")
            return invoices
        
        for pdf_file in pdf_files:
            try:
                invoice = self.extract_from_pdf(str(pdf_file))
                invoice.source_file = pdf_file.name
                invoices.append(invoice)
                print(f"✓ Extracted: {pdf_file.name}")
            except Exception as e:
                print(f"✗ Failed to extract {pdf_file.name}: {e}")
        
        return invoices
    
    def extract_from_pdf(self, pdf_path: str) -> Invoice:
        """
        Extract invoice data from a single PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Invoice object with extracted data
        """
        with pdfplumber.open(pdf_path) as pdf:
            # Extract text from all pages
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
            
            # Extract structured data
            invoice_data = self._extract_fields(text)
            
            # Extract line items
            line_items = self._extract_line_items(text)
            invoice_data['line_items'] = line_items
            
            return Invoice(**invoice_data)
    
    def _extract_fields(self, text: str) -> Dict[str, Any]:
        """Extract individual fields using regex patterns."""
        data = {}
        
        # Extract using patterns
        for field, pattern in self.PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1).strip()
                
                # Convert numeric fields
                if field in ['net_total', 'tax_amount', 'gross_total', 'tax_rate']:
                    value = self._parse_german_number(value)
                
                data[field] = value
        
        # Extract buyer information
        data['buyer_name'] = self._extract_buyer_name(text)
        data['buyer_address'] = self._extract_buyer_address(text)
        
        # Extract seller information
        data['seller_name'] = self._extract_seller_name(text)
        data['seller_address'] = self._extract_seller_address(text)
        
        # Set currency (all samples are EUR)
        data['currency'] = 'EUR'
        
        # Convert date format from DD.MM.YYYY to YYYY-MM-DD
        if 'invoice_date' in data:
            data['invoice_date'] = self._convert_date(data['invoice_date'])
        
        # Due date can be calculated from payment terms if needed
        # For now, setting it same as invoice_date as per samples
        if 'invoice_date' in data:
            data['due_date'] = data['invoice_date']
        
        return data
    
    def _extract_line_items(self, text: str) -> List[LineItem]:
        """Extract line items from the invoice text."""
        line_items = []
        
        # Pattern to find line item rows
        # Looking for: Pos. number, description, price, quantity, unit, total
        lines = text.split('\n')
        
        pos_counter = 1
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for position number at start of line or item number pattern
            if re.match(r'^\d+\s+\d+\s+VE', line) or re.match(r'^\d+\s+[A-Z]', line):
                try:
                    item_data = self._parse_line_item(line, lines[i:min(i+10, len(lines))], pos_counter)
                    if item_data:
                        line_items.append(item_data)
                        pos_counter += 1
                except Exception as e:
                    # Skip malformed line items
                    pass
            
            i += 1
        
        return line_items
    
    def _parse_line_item(self, line: str, context_lines: List[str], position: int) -> Optional[LineItem]:
        """Parse a single line item from text."""
        # Look for quantity, unit, and price patterns
        # Sample: "1 4 VE  1 VE=20 Stück  64,00 16,0000 pro 1 VE"
        
        # Try to extract components
        quantity_match = re.search(r'(\d+)\s+VE', line)
        price_match = re.search(r'(\d+[,.]?\d*)\s+pro\s+1\s+VE', line)
        total_match = re.search(r'(\d+[,.]?\d*)\s*$', line.split('EUR')[-1] if 'EUR' in line else line)
        
        if not quantity_match:
            return None
        
        quantity = float(quantity_match.group(1))
        
        # Extract description from context
        description = self._extract_description_from_context(context_lines)
        
        # Extract article number
        article_match = re.search(r'Lief\.Art\.Nr:\s*(\S+)', '\n'.join(context_lines[:5]))
        article_number = article_match.group(1) if article_match else None
        
        # Extract prices
        unit_price = 0.0
        line_total = 0.0
        
        if price_match:
            unit_price = self._parse_german_number(price_match.group(1))
        
        # Try to find the line total (typically appears as "64,00" after quantity)
        amount_matches = re.findall(r'(\d+[,.]?\d*)', line)
        if len(amount_matches) >= 2:
            # Usually the second or third number is the line total
            for amt in reversed(amount_matches):
                try:
                    potential_total = self._parse_german_number(amt)
                    if potential_total >= quantity * unit_price * 0.9:  # Allow some tolerance
                        line_total = potential_total
                        break
                except:
                    pass
        
        # If we couldn't find line total, calculate it
        if line_total == 0.0 and unit_price > 0:
            line_total = quantity * unit_price
        
        return LineItem(
            position=position,
            description=description or "Unknown item",
            article_number=article_number,
            quantity=quantity,
            unit="VE",
            unit_price=unit_price,
            line_total=line_total
        )
    
    def _extract_description_from_context(self, lines: List[str]) -> Optional[str]:
        """Extract item description from surrounding context lines."""
        # Look for description in next few lines after "Interne Mat.Nr"
        for line in lines[:8]:
            # Skip lines with numbers only or specific patterns
            if re.search(r'Lief\.Art\.Nr|Interne Mat\.Nr|Kostenstelle', line):
                continue
            
            # Look for descriptive text
            desc_match = re.search(r'^([A-ZÄÖÜa-zäöüß\s\-\[\]/]+)$', line.strip())
            if desc_match and len(desc_match.group(1)) > 3:
                desc = desc_match.group(1).strip()
                # Filter out common non-description patterns
                if not re.match(r'^\d+$', desc) and 'Bestellung' not in desc:
                    return desc
        
        return None
    
    def _extract_buyer_name(self, text: str) -> Optional[str]:
        """Extract buyer company name."""
        # Look for company name pattern after "Kundenanschrift" or before address
        match = re.search(r'Kundenanschrift[\s\n]+([^\n]+)', text)
        if not match:
            # Alternative: look for company pattern with common suffixes
            match = re.search(r'([\w\s]+(?:GmbH|AG|Unternehmen|Corporation))', text)
        
        return match.group(1).strip() if match else None
    
    def _extract_buyer_address(self, text: str) -> Optional[str]:
        """Extract buyer full address."""
        # Look for address pattern with street, postal code, city
        match = re.search(r'([A-ZÄÖÜa-zäöüß\-\.]+str\.?\s+\d+[^,]*,\s*[^,]+,\s*\w+\s+\d{5}[^\n]*)', text)
        if match:
            return match.group(1).strip()
        
        # Alternative pattern
        match = re.search(r'([\w\-\.]+str\.?\s+\d+[^\n]+Deutschland)', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        return None
    
    def _extract_seller_name(self, text: str) -> Optional[str]:
        """Extract seller company name."""
        # Look for "Corporation" pattern or after specific markers
        match = re.search(r'([A-Z]{3,}\s+Corporation)', text)
        if match:
            return match.group(1).strip()
        
        # Look after fax number line
        match = re.search(r'Ihre Faxnummer:[^\n]+\n([^\n]+)', text)
        if match:
            potential_seller = match.group(1).strip()
            if len(potential_seller) > 5 and not potential_seller.isdigit():
                return potential_seller
        
        return None
    
    def _extract_seller_address(self, text: str) -> Optional[str]:
        """Extract seller address."""
        # Often appears near the end or after seller name
        # Look for street + postal code pattern
        seller_name = self._extract_seller_name(text)
        if seller_name:
            # Find text after seller name
            idx = text.find(seller_name)
            if idx != -1:
                remaining = text[idx + len(seller_name):idx + len(seller_name) + 200]
                match = re.search(r'([A-ZÄÖÜa-zäöüß\s]+\d+[^\n]{10,80})', remaining)
                if match:
                    addr = match.group(1).strip()
                    # Clean up
                    addr = re.sub(r'\s+', ' ', addr)
                    return addr
        
        return None
    
    def _parse_german_number(self, value: str) -> float:
        """Convert German number format (1.234,56) to float."""
        if not value:
            return 0.0
        
        # Remove thousands separator and replace comma with dot
        value = value.replace('.', '').replace(',', '.')
        
        try:
            return float(value)
        except ValueError:
            return 0.0
    
    def _convert_date(self, date_str: str) -> str:
        """Convert DD.MM.YYYY to YYYY-MM-DD."""
        try:
            if '.' in date_str:
                day, month, year = date_str.split('.')
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            return date_str
        except:
            return date_str


# Convenience function
def extract_invoices(pdf_dir: str) -> List[Invoice]:
    """
    Extract invoices from a directory of PDFs.
    
    Args:
        pdf_dir: Path to directory containing PDF files
        
    Returns:
        List of Invoice objects
    """
    extractor = InvoiceExtractor()
    return extractor.extract_from_directory(pdf_dir)