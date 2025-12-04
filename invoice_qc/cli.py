"""
Command-line interface for Invoice QC Service.
Provides extract, validate, and full-run commands.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List

from .extractor import extract_invoices
from .validator import validate_invoices
from .models import Invoice, ValidationReport


def extract_command(args):
    """Extract invoices from PDFs and save to JSON."""
    print(f"📄 Extracting invoices from: {args.pdf_dir}")
    print("-" * 50)
    
    try:
        # Extract invoices
        invoices = extract_invoices(args.pdf_dir)
        
        if not invoices:
            print("\n⚠️  No invoices extracted. Check if PDF directory contains valid files.")
            return 1
        
        print(f"\n✅ Successfully extracted {len(invoices)} invoice(s)")
        
        # Save to JSON
        output_data = [invoice.model_dump() for invoice in invoices]
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved to: {args.output}")
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during extraction: {e}")
        return 1


def validate_command(args):
    """Validate invoices from JSON and generate report."""
    print(f"🔍 Validating invoices from: {args.input}")
    print("-" * 50)
    
    try:
        # Load invoices from JSON
        with open(args.input, 'r', encoding='utf-8') as f:
            invoice_data = json.load(f)
        
        invoices = [Invoice(**inv) for inv in invoice_data]
        
        # Validate
        report = validate_invoices(invoices)
        
        # Print summary to console
        print_validation_summary(report)
        
        # Save report to JSON
        with open(args.report, 'w', encoding='utf-8') as f:
            json.dump(report.model_dump(), f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Full report saved to: {args.report}")
        
        # Exit with error code if any invalid invoices
        return 1 if report.summary.invalid_invoices > 0 else 0
        
    except FileNotFoundError:
        print(f"\n❌ Error: Input file not found: {args.input}")
        return 1
    except json.JSONDecodeError:
        print(f"\n❌ Error: Invalid JSON in input file")
        return 1
    except Exception as e:
        print(f"\n❌ Error during validation: {e}")
        return 1


def full_run_command(args):
    """Extract from PDFs and validate in one go."""
    print("🚀 Running full pipeline: Extract → Validate")
    print("=" * 50)
    
    try:
        # Step 1: Extract
        print("\n📄 STEP 1: Extraction")
        print("-" * 50)
        invoices = extract_invoices(args.pdf_dir)
        
        if not invoices:
            print("\n⚠️  No invoices extracted. Exiting.")
            return 1
        
        print(f"\n✅ Extracted {len(invoices)} invoice(s)")
        
        # Step 2: Validate
        print("\n🔍 STEP 2: Validation")
        print("-" * 50)
        report = validate_invoices(invoices)
        
        # Print summary
        print_validation_summary(report)
        
        # Save report
        with open(args.report, 'w', encoding='utf-8') as f:
            json.dump(report.model_dump(), f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Report saved to: {args.report}")
        
        # Optionally save extracted invoices too
        if hasattr(args, 'save_extracted') and args.save_extracted:
            extracted_file = args.report.replace('.json', '_extracted.json')
            output_data = [invoice.model_dump() for invoice in invoices]
            with open(extracted_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            print(f"💾 Extracted data saved to: {extracted_file}")
        
        return 1 if report.summary.invalid_invoices > 0 else 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


def print_validation_summary(report: ValidationReport):
    """Print a human-readable validation summary."""
    summary = report.summary
    
    print(f"\n{'=' * 50}")
    print("📊 VALIDATION SUMMARY")
    print("=" * 50)
    print(f"Total invoices:   {summary.total_invoices}")
    print(f"✅ Valid:         {summary.valid_invoices}")
    print(f"❌ Invalid:       {summary.invalid_invoices}")
    
    if summary.error_counts:
        print(f"\n📋 Error breakdown:")
        # Sort by count (descending)
        sorted_errors = sorted(
            summary.error_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        for error_type, count in sorted_errors[:10]:  # Top 10 errors
            print(f"  • {error_type}: {count}")
    
    # Show details of invalid invoices
    if report.summary.invalid_invoices > 0:
        print(f"\n⚠️  Invalid invoices:")
        for result in report.results:
            if not result.is_valid:
                print(f"\n  Invoice: {result.invoice_id}")
                if result.source_file:
                    print(f"  Source:  {result.source_file}")
                print(f"  Errors:")
                for error in result.errors:
                    print(f"    - [{error.rule}] {error.message}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Invoice QC Service - Extract and validate invoice PDFs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract only
  python -m invoice_qc.cli extract --pdf-dir pdfs --output invoices.json
  
  # Validate only
  python -m invoice_qc.cli validate --input invoices.json --report report.json
  
  # Full pipeline
  python -m invoice_qc.cli full-run --pdf-dir pdfs --report report.json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Extract command
    extract_parser = subparsers.add_parser(
        'extract',
        help='Extract structured data from PDF invoices'
    )
    extract_parser.add_argument(
        '--pdf-dir',
        required=True,
        help='Directory containing PDF invoice files'
    )
    extract_parser.add_argument(
        '--output',
        required=True,
        help='Output JSON file for extracted invoices'
    )
    
    # Validate command
    validate_parser = subparsers.add_parser(
        'validate',
        help='Validate invoice JSON against business rules'
    )
    validate_parser.add_argument(
        '--input',
        required=True,
        help='Input JSON file with invoice data'
    )
    validate_parser.add_argument(
        '--report',
        required=True,
        help='Output JSON file for validation report'
    )
    
    # Full-run command
    fullrun_parser = subparsers.add_parser(
        'full-run',
        help='Extract from PDFs and validate (end-to-end)'
    )
    fullrun_parser.add_argument(
        '--pdf-dir',
        required=True,
        help='Directory containing PDF invoice files'
    )
    fullrun_parser.add_argument(
        '--report',
        required=True,
        help='Output JSON file for validation report'
    )
    fullrun_parser.add_argument(
        '--save-extracted',
        action='store_true',
        help='Also save extracted invoice JSON'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Route to appropriate command handler
    if args.command == 'extract':
        return extract_command(args)
    elif args.command == 'validate':
        return validate_command(args)
    elif args.command == 'full-run':
        return full_run_command(args)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())