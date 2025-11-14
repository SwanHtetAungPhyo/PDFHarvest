# PDF Harvest 📚

A Python tool for harvesting academic papers via DOI, downloading open access PDFs, and searching them for specific content.

## 🌟 Features

- **Batch Processing**: Process DOIs in configurable batches with controlled concurrency for optimal performance
- **API Integration**: Automatic metadata fetching from Crossref and open access information from Unpaywall
- **Intelligent PDF Download**: 
  - Automatic redirect handling (301, 302, 303, 307, 308)
  - HTML landing page detection
  - Content-Type validation
  - PDF header verification
  - Protection against infinite redirect loops
- **Content Search**: Full-text search in PDFs with page-level results (case-insensitive)
- **Smart Caching**: Intelligent caching of API responses and search results for faster re-runs
- **Resilient Networking**: Retry logic with exponential backoff for transient errors (429, 500, 502, 503, 504)
- **Comprehensive Reporting**: Generate detailed Excel and CSV reports with all metadata and search results
- **Automated File Organization**: PDFs automatically sorted into folders based on search matches

## 🔧 Requirements

- Python 3.8 or higher
- Required packages:
  - `httpx>=0.24.0` - Modern HTTP client with async support
  - `pandas>=1.5.0` - Data manipulation and Excel export
  - `pyyaml>=6.0` - Configuration file parsing
  - `pypdf>=3.0.0` - PDF text extraction
  - `tqdm>=4.64.0` - Progress bars
  - `pydantic>=2.0.0` - Data validation
  - `openpyxl` - Excel file support

## 📦 Installation

### Option 1: From Source (Recommended for Development)

```bash
# Clone the repository
git clone https://github.com/SwanHtetAungPhyo/PDF_CRAWLER.git
cd PDF_CRAWLER

# Install in editable mode
pip install -e .
```

### Option 2: Install Dependencies Only

```bash
# Install required packages
pip install httpx pandas pyyaml pypdf tqdm pydantic openpyxl

# Install development dependencies (optional)
pip install pytest pytest-asyncio pytest-cov black isort mypy
```

### Option 3: Development Installation with All Tools

```bash
pip install -e ".[dev]"
```

## 🚀 Quick Start

1. **Create an Excel file** with DOIs (e.g., `my_dois.xlsx`):
   
   | doi |
   |-----|
   | 10.1371/journal.pone.0227849 |
   | 10.3390/s20051357 |
   | 10.1038/s41598-020-58831-9 |

2. **Create a configuration file** (`config.yaml`):

```yaml
input_excel: "my_dois.xlsx"
doi_column: "doi"
email: "your.email@university.edu"
strings: ["machine learning", "neural network"]
output_dir: "results"
```

3. **Run the harvester**:

```bash
# Using the module
python -m src.cli --config config.yaml

# Or if installed as package
pdfharvest --config config.yaml
```

4. **Check results** in the `results/` folder!

## 💻 Usage

### Command Line Interface

```bash
# Run with configuration file
python -m src.cli --config config.yaml

# If installed as package
pdfharvest --config config.yaml

# Show version
python -m src.cli --version

# Get help
python -m src.cli --help
```

### Python API

```python
import asyncio
from src.orchestrator import run

# Run the harvester
async def main():
    result_df = await run("config.yaml")
    print(f"✅ Processed {len(result_df)} DOIs")
    print(f"📄 Found {result_df['match_found'].sum()} PDFs with keywords")
    return result_df

# Execute
df = asyncio.run(main())
```

### Example Output

```
2025-11-10 10:30:45,123 | INFO | harvest | Starting batched DOI harvest
2025-11-10 10:30:45,456 | INFO | harvest | Loaded 5 DOIs
2025-11-10 10:30:46,789 | INFO | harvest | Batch 1: preparing 5 DOIs
Stage 1: prepare+download: 100%|████████████████| 5/5 [00:04<00:00, 1.19it/s]
2025-11-10 10:30:50,123 | INFO | harvest | Batch 1: processing PDFs
2025-11-10 10:30:50,456 | INFO | harvest | Done. Total rows: 5 → results/report.xlsx
Harvesting completed successfully. Processed 5 DOIs.
```

## ⚙️ Configuration

Create a YAML configuration file with the following structure:

```yaml
# Input data
input_excel: "doi_data.xlsx"
doi_column: "doi"
email: "your.email@institution.edu"  # Required for Unpaywall API

# Search strings (case-insensitive)
strings:
  - "machine learning"
  - "artificial intelligence"
  - "neural network"

# Output settings
output_dir: "results"
batch_size: 5
concurrency: 6
write_after_each_batch: true

# Folder structure
folders:
  downloads: "downloads"      # Staging area
  found: "output_found"       # PDFs with matches
  notfound: "output_notfound" # PDFs without matches

# Caching
cache:
  enabled: true
  force_refresh: false

# HTTP settings
http:
  user_agent: "pdfharvest/0.1.0 (+your.email@institution.edu)"
  max_keepalive: 20
  max_connections: 20

# Timeouts (seconds)
timeouts:
  read: 30.0
  connect: 15.0

# Logging
logging:
  level: "INFO"
  file: "harvest.log"
  rotate_bytes: 10485760  # 10MB
  backup_count: 5
```

### Configuration Parameters Explained

| Parameter | Description | Default | Required |
|-----------|-------------|---------|----------|
| `input_excel` | Path to Excel file with DOIs | - | ✅ Yes |
| `doi_column` | Name of column containing DOIs | "doi" | ✅ Yes |
| `email` | Your email (required by Unpaywall) | - | ✅ Yes |
| `strings` | List of keywords to search in PDFs | [] | ✅ Yes |
| `output_dir` | Directory for results | "results" | ❌ No |
| `batch_size` | Number of DOIs per batch | 5 | ❌ No |
| `concurrency` | Concurrent downloads per batch | 3 | ❌ No |
| `write_after_each_batch` | Save incremental reports | true | ❌ No |

## 📊 Input Data Format

Your Excel file should contain a column with DOI identifiers:

| doi | title (optional) | notes (optional) |
|-----|------------------|------------------|
| 10.1371/journal.pone.0227849 | Machine Learning Paper | High priority |
| 10.3390/s20051357 | IoT Research | - |
| 10.1038/s41598-020-58831-9 | Neural Networks | Review later |

**Supported formats:**
- `.xlsx` (Excel 2007+)
- `.xls` (Excel 97-2003)
- Any format supported by `pandas.read_excel()`

## 📁 Output Structure

```
results/
├── 📁 logs/
│   └── harvest.log              # Detailed execution logs with timestamps
│
├── 📁 cache/                    # Cached API responses (speeds up re-runs)
│   ├── 📁 crossref/            # Crossref metadata (JSON)
│   ├── 📁 unpaywall/           # Unpaywall OA info (JSON)
│   └── 📁 matches/             # PDF search results (JSON)
│
├── 📁 downloads/                # Temporary staging area for PDFs
│
├── 📁 output_found/             # ✅ PDFs containing your keywords
│   ├── 10.1234_example1.pdf
│   └── 10.5678_example2.pdf
│
├── 📁 output_notfound/          # ❌ PDFs without keyword matches
│   └── 10.9012_example3.pdf
│
├── 📄 report.xlsx               # Comprehensive results (Excel format)
└── 📄 report.csv                # Same data in CSV format
```

## 📈 Report Columns

The generated `report.xlsx` includes the following columns:

### Identification
- `doi` - Digital Object Identifier
- `title` - Paper title
- `crossref_url` - Link to Crossref record

### Metadata
- `journal` - Journal name
- `year` - Publication year
- `authors` - Author list (semicolon-separated)
- `publisher` - Publisher name
- `type` - Publication type (journal-article, conference-paper, etc.)

### Open Access Information
- `is_oa` - Boolean: Is the paper Open Access?
- `oa_license` - License type (CC-BY, CC-BY-NC, etc.)
- `pdf_url` - Direct URL to PDF (if available)

### Search Results
- `match_found` - Boolean: Were keywords found?
- `matched_strings` - Which keywords were found (comma-separated)
- `match_pages` - Page numbers where keywords appear (comma-separated)

### File Management
- `pdf_temp_path` - Temporary download location (staging)
- `pdf_final_path` - Final location (output_found/ or output_notfound/)

## 🧪 Testing

The project includes comprehensive unit tests with 100% pass rate.

### Run All Tests

```bash
# Run all tests with verbose output
python -m pytest tests/ -v

# Run with coverage report
python -m pytest tests/ --cov=src --cov-report=html

# Run specific test file
python -m pytest tests/test_http_download.py -v

# Run specific test
python -m pytest tests/test_http.py::test_best_pdf_url -v
```

### Test Statistics

- ✅ **15 tests** (100% passing)
- 📊 **54% code coverage**
- 🧪 Test categories:
  - Configuration validation (2 tests)
  - HTTP utilities & APIs (3 tests)
  - PDF download with redirects (6 tests)
  - Orchestration logic (2 tests)
  - PDF operations (2 tests)

### Create Test Data

```python
# Create sample Excel file with DOIs
python -c "
import pandas as pd
df = pd.DataFrame({
    'doi': [
        '10.1371/journal.pone.0227849',
        '10.3390/s20051357',
        '10.1038/s41598-020-58831-9'
    ]
})
df.to_excel('test_dois.xlsx', index=False)
print('✅ Created test_dois.xlsx')
"
```

## 🛠️ Development

### Code Quality Tools

```bash
# Format code with Black
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/

# Lint with pylint
pylint src/
```

### Project Structure

```
PDF_CRAWLER/
├── src/
│   ├── __init__.py          # Package initialization
│   ├── cache.py             # Cache management utilities
│   ├── cli.py               # Command-line interface
│   ├── config.py            # Configuration validation
│   ├── http.py              # HTTP client & API calls
│   ├── log_setup.py         # Logging configuration
│   ├── orchestrator.py      # Main workflow coordination
│   └── pdfops.py            # PDF operations (search, move)
│
├── tests/
│   ├── test_config.py       # Configuration tests
│   ├── test_http.py         # API tests
│   ├── test_http_download.py  # Download tests (NEW)
│   ├── test_orchestrator.py   # Orchestration tests
│   └── test_pdfops.py       # PDF operation tests
│
├── config.yaml              # Example configuration
├── pyproject.toml           # Project metadata & dependencies
├── README.md                # This file
└── .gitignore              # Git ignore patterns
```

## 🏗️ Architecture

### Two-Stage Batched Processing

The system uses an efficient two-stage batched approach to optimize resource usage:

```
┌─────────────────────────────────────────────────────────────┐
│                        STAGE 1                               │
│              Concurrent Metadata + Download                  │
│  (Network I/O - Async, Parallelized with Semaphore)        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   Batch of 5-10 DOIs   │
              └────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                        STAGE 2                               │
│              Sequential PDF Processing                       │
│     (CPU-bound - Thread Pool for PDF Parsing)               │
└─────────────────────────────────────────────────────────────┘
```

### Stage 1: Concurrent Network Operations
- Fetch Crossref metadata (async)
- Fetch Unpaywall OA info (async)
- Download PDFs to staging area (async with streaming)
- Controlled concurrency via `asyncio.Semaphore`
- Automatic retry with exponential backoff

### Stage 2: PDF Processing
- Text extraction from PDFs (CPU-bound, uses thread pool)
- Keyword search (case-insensitive)
- File organization based on search results
- Cache search results for future runs

### Key Design Decisions

1. **Separation of I/O and CPU work**: Prevents network operations from blocking PDF processing
2. **Batching**: Allows progress tracking and incremental saves
3. **Caching**: Reduces API calls and speeds up re-runs
4. **Streaming downloads**: Prevents memory overflow with large PDFs
5. **Atomic file moves**: Prevents file corruption and handles name collisions

### Redirect Handling Flow

```
URL Request
    ↓
[follow_redirects=True]
    ↓
Check Status Code
    ├─ 200-299: Continue ✅
    ├─ 301-308: Follow redirect automatically 🔄
    └─ 400+: Abort ❌
    ↓
Check Content-Type
    ├─ application/pdf: Download ✅
    └─ text/html: Check first bytes
        ├─ Starts with %PDF: Download anyway ✅
        └─ Actually HTML: Skip ❌
    ↓
Validate PDF Header
    ├─ Valid %PDF: Keep file ✅
    └─ Invalid: Delete & report ❌
```

## 🌐 API Information

### Crossref API
- **Endpoint**: `https://api.crossref.org/works/{doi}`
- **Authentication**: None required
- **Rate limit**: Be respectful, no hard limit
- **Data returned**: Title, authors, journal, publisher, publication date, type
- **Documentation**: https://api.crossref.org/swagger-ui/index.html

### Unpaywall API
- **Endpoint**: `https://api.unpaywall.org/v2/{doi}`
- **Authentication**: Email parameter required
- **Rate limit**: 100,000 requests/day (more than sufficient)
- **Data returned**: OA status, license, PDF URLs, OA locations
- **Documentation**: https://unpaywall.org/products/api

### Best Practices
- Always include a valid email in configuration
- Use caching to minimize API calls
- Respect rate limits and server load
- Include identifying User-Agent string

### Debug Mode

Enable detailed logging:

```yaml
logging:
  level: "DEBUG"  # Change from INFO to DEBUG
  file: "harvest.log"
```

Then check `results/logs/harvest.log` for detailed information.

### Performance Tips

1. **Enable caching** to speed up re-runs:
   ```yaml
   cache:
     enabled: true
     force_refresh: false
   ```

2. **Adjust batch size** based on your connection:
   - Slow connection: `batch_size: 3`, `concurrency: 2`
   - Fast connection: `batch_size: 10`, `concurrency: 5`

3. **Use incremental saves** for large datasets:
   ```yaml
   write_after_each_batch: true
   ```

### Submitting Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass: `pytest tests/ -v`
6. Update documentation if needed
7. Commit with clear messages: `git commit -m "feat: add amazing feature"`
8. Push to your fork: `git push origin feature/amazing-feature`
9. Open a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/PDF_CRAWLER.git
cd PDF_CRAWLER

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks (optional)
pip install pre-commit
pre-commit install

# Run tests
pytest tests/ -v

# Check code quality
black src/ tests/
isort src/ tests/
mypy src/
```

