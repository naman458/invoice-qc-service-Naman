# Invoice QC Service

## Overview
This is an Invoice Extraction & Quality Control Service that processes PDF invoices, extracts structured data, validates against business rules, and provides both CLI and API interfaces.

**Completed Components:**
- ✅ PDF Extraction Module
- ✅ Validation Core with comprehensive rules
- ✅ CLI Interface (extract, validate, full-run)
- ✅ FastAPI HTTP API
- ✅ (Bonus) Web-based QC Console

---

## Schema & Validation Design

### Invoice Schema Fields

| Field | Type | Description |
|-------|------|-------------|
| `invoice_number` | string | Primary identifier (e.g., AUFNR34343) |
| `customer_number` | string | Customer ID in seller's system |
| `order_reference` | string | External order reference number |
| `buyer_name` | string | Name of the purchasing company |
| `buyer_address` | string | Full address of buyer |
| `seller_name` | string | Name of the selling company |
| `seller_address` | string | Full address of seller |
| `invoice_date` | string | Date of invoice (ISO format YYYY-MM-DD) |
| `due_date` | string | Payment due date (ISO format) |
| `delivery_date` | string | Requested delivery date |
| `currency` | string | Currency code (EUR, USD, etc.) |
| `net_total` | float | Total before tax |
| `tax_rate` | float | Tax percentage (e.g., 19.0 for 19%) |
| `tax_amount` | float | Calculated tax amount |
| `gross_total` | float | Total including tax |
| `payment_terms` | string | Payment terms description |
| `line_items` | array | List of line items (see below) |

**Line Item Structure:**
- `position`: Position number
- `description`: Item description
- `article_number`: Product/article ID
- `quantity`: Quantity ordered
- `unit`: Unit of measurement
- `unit_price`: Price per unit
- `line_total`: Total for this line

### Validation Rules

#### Completeness Rules (4 rules)
1. **invoice_number_required**: Every invoice must have a non-empty invoice number
   - *Rationale*: Essential for tracking and referencing invoices
   
2. **invoice_date_required**: Invoice date must be present
   - *Rationale*: Required for aging, reporting, and payment processing
   
3. **parties_required**: Both buyer_name and seller_name must not be empty
   - *Rationale*: Need to know who is transacting
   
4. **currency_required**: Currency field must be present
   - *Rationale*: Essential for financial processing and multi-currency systems

#### Format/Type Rules (3 rules)
5. **date_format_valid**: All dates must be parseable and in valid format
   - *Rationale*: Prevents downstream errors in date calculations
   
6. **currency_in_known_set**: Currency must be one of: EUR, USD, GBP, INR, JPY, CHF
   - *Rationale*: Limits to commonly supported currencies, prevents typos
   
7. **amounts_non_negative**: All monetary amounts must be >= 0
   - *Rationale*: Negative totals indicate data extraction errors

#### Business Rules (3 rules)
8. **line_items_sum_match**: Sum of line_items should equal net_total (±1% tolerance)
   - *Rationale*: Ensures arithmetic integrity, catches extraction errors
   
9. **tax_calculation_valid**: net_total + tax_amount should equal gross_total (±0.02 tolerance)
   - *Rationale*: Verifies tax was calculated correctly
   
10. **due_date_logical**: If due_date exists, it must be on or after invoice_date
    - *Rationale*: Payment can't be due before invoice is issued

#### Anomaly/Duplicate Rules (2 rules)
11. **no_duplicate_invoices**: No duplicate invoice_number + seller_name + invoice_date combinations
    - *Rationale*: Prevents processing same invoice twice
    
12. **totals_not_zero**: gross_total should not be zero
    - *Rationale*: Zero-value invoices are likely extraction failures

---

## Architecture

### Folder Structure
```
invoice-qc-service/
├── invoice_qc/
│   ├── __init__.py
│   ├── extractor.py          # PDF extraction logic
│   ├── validator.py          # Validation rules engine
│   ├── cli.py                # CLI interface
│   ├── models.py             # Pydantic data models
│   └── config.py             # Configuration
├── api/
│   ├── __init__.py
│   ├── main.py               # FastAPI application
│   └── routes.py             # API endpoints
├── frontend/                  # (Bonus) Web UI
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── tests/
│   ├── test_extractor.py
│   └── test_validator.py
├── pdfs/                      # Sample invoice PDFs
├── requirements.txt
├── README.md
└── .env.example
```

### Data Flow Diagram
```
┌─────────────┐
│  PDF Files  │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  Extractor Module   │  ← Uses pdfplumber + regex
│  (extractor.py)     │    to parse text
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  Structured JSON    │  ← Invoice objects with
│  (Invoice model)    │    all extracted fields
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  Validator Module   │  ← Applies 12 validation
│  (validator.py)     │    rules
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  Validation Results │  ← Per-invoice + summary
│  (JSON Report)      │    report
└──────┬──────────────┘
       │
       ├──────────────────┬──────────────────┐
       ▼                  ▼                  ▼
┌─────────────┐    ┌──────────┐    ┌──────────────┐
│     CLI     │    │ REST API │    │   Web UI     │
│   Output    │    │ Response │    │  (Browser)   │
└─────────────┘    └──────────┘    └──────────────┘
```

### Component Details

**Extractor Pipeline:**
1. Read PDF with pdfplumber
2. Extract raw text
3. Apply regex patterns to find fields (invoice number, dates, amounts)
4. Parse line items from table-like structures
5. Return structured Invoice object

**Validation Core:**
- Rule-based system with extensible architecture
- Each rule is a function that checks one constraint
- Collects all violations per invoice
- Generates summary statistics

**CLI:**
- Three modes: extract, validate, full-run
- Uses argparse for command-line arguments
- Outputs JSON files and human-readable summaries

**API:**
- FastAPI with automatic OpenAPI docs
- Endpoints: /health, /validate-json, /extract-and-validate
- Returns structured JSON responses

**Frontend (Bonus):**
- Single-page app with vanilla JS
- Upload PDFs or paste JSON
- Displays validation results in table format
- Filter by valid/invalid status

---

## Setup & Installation

### Prerequisites
- Python 3.9 or higher
- pip (Python package manager)

### Installation Steps

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd invoice-qc-service
```

2. **Create virtual environment**
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Mac/Linux:
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

### Dependencies
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pdfplumber==0.10.3
python-multipart==0.0.6
```

---

## Usage

### CLI Usage

**1. Extract only (PDF → JSON)**
```bash
python -m invoice_qc.cli extract \
  --pdf-dir pdfs \
  --output extracted_invoices.json
```

**2. Validate only (JSON → Validation Report)**
```bash
python -m invoice_qc.cli validate \
  --input extracted_invoices.json \
  --report validation_report.json
```

**3. Full pipeline (PDF → Extract → Validate)**
```bash
python -m invoice_qc.cli full-run \
  --pdf-dir pdfs \
  --report validation_report.json
```

**Example Output:**
```
=== Invoice QC Summary ===
Total invoices: 3
Valid invoices: 2
Invalid invoices: 1

Top errors:
  - missing_field:buyer_address (1 occurrences)
  - business_rule:line_items_sum_mismatch (1 occurrences)

Report saved to: validation_report.json
```

### API Usage

**1. Start the API server**
```bash
uvicorn api.main:app --reload --port 8000
```

**2. Check health**
```bash
curl http://localhost:8000/health
```

**3. Validate JSON invoices**
```bash
curl -X POST http://localhost:8000/validate-json \
  -H "Content-Type: application/json" \
  -d @extracted_invoices.json
```

**4. Extract and validate PDFs**
```bash
curl -X POST http://localhost:8000/extract-and-validate \
  -F "files=@pdfs/sample_pdf_1.pdf" \
  -F "files=@pdfs/sample_pdf_2.pdf"
```

**5. Interactive API Documentation**
Visit: `http://localhost:8000/docs`

### Frontend Usage (Bonus)

1. **Start API server** (if not running)
```bash
uvicorn api.main:app --reload --port 8000
```

2. **Open frontend**
```bash
# Simple HTTP server
python -m http.server 8080 --directory frontend

# Then visit: http://localhost:8080
```

3. **Using the QC Console**
   - Upload PDF files or paste JSON
   - Click "Process & Validate"
   - View results in the table
   - Filter by valid/invalid status
   - Click on invoices to see detailed errors

---

## AI Usage Notes

### Tools Used
- **ChatGPT-4** (Claude): For architecture design, code generation, and debugging
- **GitHub Copilot**: For autocomplete and boilerplate code

### Specific Usage

1. **Regex Pattern Generation** (GPT-4)
   - Used for: Creating patterns to extract invoice numbers, dates, and amounts from German text
   - Example: Pattern for "Bestellung AUFNR\d+" to capture order numbers

2. **FastAPI Boilerplate** (Copilot)
   - Used for: Setting up FastAPI app structure, CORS middleware, endpoint decorators
   - Saved time on repetitive API setup

3. **Pydantic Model Design** (GPT-4)
   - Used for: Designing Invoice and LineItem models with proper validation
   - Added custom validators for date parsing and amount calculations

4. **PDF Parsing Logic** (GPT-4 + Trial & Error)
   - Initial AI suggestion: Use PyPDF2
   - **AI was wrong**: PyPDF2 struggled with the table structure in these PDFs
   - **My solution**: Switched to pdfplumber which better preserves text positioning
   - Also added custom heuristics for detecting line items based on EUR prices

5. **Validation Logic** (Co-designed with GPT-4)
   - AI provided initial rule suggestions
   - **AI was incomplete**: Suggested exact match for totals without tolerance
   - **My improvement**: Added ±1% tolerance for line items and ±0.02 for tax to handle rounding

6. **Error Handling** (Copilot suggestions + manual refinement)
   - Copilot suggested basic try-catch blocks
   - I added specific error messages and logging

### AI Chat Exports
See `/ai-notes/` folder for:
- `01-schema-design-chat.pdf` - Discussion on invoice schema
- `02-regex-patterns.txt` - Regex development for extraction
- `03-fastapi-setup.txt` - API endpoint design
- `04-validation-rules.pdf` - Business rules brainstorming

---

## Assumptions & Limitations

### Assumptions
1. **Language**: All invoices are in German (patterns are German-specific)
2. **Format**: Invoices follow similar structure (PDF text-based, not scanned images)
3. **Currency**: Primarily EUR, but schema supports others
4. **Date Format**: German format (DD.MM.YYYY) in PDFs, converted to ISO
5. **Tax Rate**: 19% VAT is standard (MwSt. 19,00%)

### Known Limitations
1. **OCR**: Does not handle scanned/image PDFs (would need Tesseract or cloud OCR)
2. **Multi-page**: Not tested with multi-page invoices
3. **Complex Tables**: May struggle with nested tables or merged cells
4. **Language**: Only German patterns implemented; would need i18n for other languages
5. **Duplicate Detection**: Only checks within current batch, not against historical database
6. **Scalability**: Processes sequentially; large batches would benefit from parallel processing

### Simplified Due to Time
- No database integration (uses in-memory comparison for duplicates)
- Basic frontend without advanced features (sorting, export, etc.)
- No authentication/authorization
- No persistent storage of results
- No email notifications or webhooks

### Edge Cases That Might Break
1. Invoices with multiple tax rates
2. Invoices with discounts or credits
3. Non-standard date formats
4. Multiple currencies in same invoice
5. Invoices without clear line item sections

---

## How This Could Integrate Into a Larger System

### Integration Points

1. **Upstream Integration**
   ```
   Document Scanner → OCR Service → Invoice QC API
   Email Inbox → Attachment Extractor → Invoice QC API
   Supplier Portal → PDF Generator → Invoice QC API
   ```

2. **API Integration Pattern**
   ```python
   # Other services call our API
   response = requests.post(
       "https://invoice-qc.company.com/api/extract-and-validate",
       files={"files": pdf_content}
   )
   
   if response.json()["summary"]["invalid_invoices"] > 0:
       # Route to manual review queue
       send_to_review_queue(response.json())
   else:
       # Auto-approve and send to accounting
       push_to_erp_system(response.json()["invoices"])
   ```

3. **Queue/Event-Driven Architecture**
   - Listen to message queue (RabbitMQ, Kafka) for new invoice events
   - Process asynchronously
   - Publish results to another queue for downstream consumers
   
   ```
   [S3 Upload] → [Lambda/Worker] → [Invoice QC API] → [Results Queue] → [ERP System]
   ```

4. **Webhook Integration**
   - Configure webhooks in our API to notify external systems
   - Send validation results to configured endpoints
   - Supports both success and failure callbacks

5. **Dashboard Integration**
   - Embed the QC Console as iframe in existing admin panel
   - Or: Use our API to build custom dashboards
   - Real-time stats via WebSocket endpoints (future enhancement)

### Containerization (Docker)

**Dockerfile**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yml**
```yaml
version: '3.8'
services:
  invoice-qc-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
    volumes:
      - ./pdfs:/app/pdfs
```

**Deployment**
```bash
docker build -t invoice-qc-service .
docker run -p 8000:8000 invoice-qc-service
```

### Future Enhancements for Production
- Add Redis for caching extracted invoices
- PostgreSQL for storing validation history
- Celery for async task processing
- Prometheus metrics for monitoring
- Rate limiting and API keys
- Audit logging for compliance

---

## Video Demo

**Link**: [Google Drive Video](https://drive.google.com/your-video-link)
*(Make sure sharing is set to "Anyone with the link")*

**Contents** (15 minutes):
- 0:00 - Overview and problem statement
- 2:00 - Schema and validation rules walkthrough
- 5:00 - Code structure explanation
- 8:00 - CLI demo with sample PDFs
- 11:00 - API demo with Postman/curl
- 13:00 - Web UI demonstration
- 15:00 - Integration possibilities

---

## Testing

Run tests with pytest:
```bash
pytest tests/ -v
```

---

## License

MIT License - Feel free to use for educational purposes.

---

## Contact

[Your Name] - [Your Email]

GitHub: [@yourusername](https://github.com/yourusername)