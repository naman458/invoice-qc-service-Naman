"""
FastAPI application for Invoice QC Service.
Provides REST API endpoints for invoice validation.
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List
import tempfile
import os
from pathlib import Path

from invoice_qc.models import Invoice, ValidationReport
from invoice_qc.extractor import InvoiceExtractor
from invoice_qc.validator import InvoiceValidator


# Create FastAPI app
app = FastAPI(
    title="Invoice QC Service",
    description="API for extracting and validating invoice data from PDFs",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
extractor = InvoiceExtractor()
validator = InvoiceValidator()


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Invoice QC Service",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "validate_json": "POST /validate-json",
            "extract_and_validate": "POST /extract-and-validate",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "Invoice QC Service",
        "version": "1.0.0"
    }


@app.post("/validate-json", response_model=ValidationReport)
async def validate_json(invoices: List[Invoice]):
    """
    Validate a list of invoice JSON objects.
    
    Args:
        invoices: List of Invoice objects in JSON format
        
    Returns:
        ValidationReport with summary and per-invoice results
        
    Example request body:
    ```json
    [
        {
            "invoice_number": "INV-001",
            "invoice_date": "2024-01-10",
            "buyer_name": "Example Corp",
            "seller_name": "ABC Ltd",
            "currency": "EUR",
            "net_total": 100.0,
            "tax_amount": 19.0,
            "gross_total": 119.0
        }
    ]
    ```
    """
    try:
        # Validate invoices
        report = validator.validate_batch(invoices)
        return report
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Validation error: {str(e)}"
        )


@app.post("/extract-and-validate")
async def extract_and_validate(files: List[UploadFile] = File(...)):
    """
    Extract data from uploaded PDFs and validate.
    
    Args:
        files: List of PDF files to process
        
    Returns:
        JSON with extracted invoices and validation report
        
    Example:
    ```bash
    curl -X POST http://localhost:8000/extract-and-validate \
      -F "files=@invoice1.pdf" \
      -F "files=@invoice2.pdf"
    ```
    """
    try:
        # Create temp directory for uploaded files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Save uploaded files
            saved_files = []
            for upload_file in files:
                if not upload_file.filename.endswith('.pdf'):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid file type: {upload_file.filename}. Only PDF files are supported."
                    )
                
                file_path = temp_path / upload_file.filename
                content = await upload_file.read()
                
                with open(file_path, 'wb') as f:
                    f.write(content)
                
                saved_files.append(file_path)
            
            if not saved_files:
                raise HTTPException(
                    status_code=400,
                    detail="No PDF files provided"
                )
            
            # Extract invoices
            invoices = []
            extraction_errors = []
            
            for file_path in saved_files:
                try:
                    invoice = extractor.extract_from_pdf(str(file_path))
                    invoice.source_file = file_path.name
                    invoices.append(invoice)
                except Exception as e:
                    extraction_errors.append({
                        "file": file_path.name,
                        "error": str(e)
                    })
            
            if not invoices and extraction_errors:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to extract any invoices. Errors: {extraction_errors}"
                )
            
            # Validate extracted invoices
            report = validator.validate_batch(invoices)
            
            # Prepare response
            response = {
                "extracted_invoices": [inv.model_dump() for inv in invoices],
                "validation_report": report.model_dump(),
                "extraction_errors": extraction_errors if extraction_errors else None
            }
            
            return JSONResponse(content=response)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Processing error: {str(e)}"
        )


@app.get("/api/info")
async def api_info():
    """Get information about the API and its capabilities."""
    return {
        "service": "Invoice QC Service API",
        "version": "1.0.0",
        "description": "Extract and validate invoice data from PDFs",
        "features": [
            "PDF text extraction",
            "Structured data parsing",
            "Business rule validation",
            "Duplicate detection",
            "Multi-file batch processing"
        ],
        "supported_languages": ["German (primary)"],
        "supported_currencies": ["EUR", "USD", "GBP", "INR", "JPY", "CHF"],
        "validation_rules": {
            "completeness": 4,
            "format": 3,
            "business_logic": 3,
            "anomaly_detection": 2
        }
    }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested endpoint does not exist",
            "available_endpoints": [
                "/",
                "/health",
                "/validate-json",
                "/extract-and-validate",
                "/api/info",
                "/docs"
            ]
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)