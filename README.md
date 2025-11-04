# PDF Harvest

A Python tool for harvesting academic papers via DOI, downloading open access PDFs, and searching them for specific content.

## Features

- **Batch Processing**: Process DOIs in configurable batches with controlled concurrency
- **API Integration**: Fetch metadata from Crossref and open access information from Unpaywall
- **PDF Download**: Download and validate PDF files from open access sources
- **Content Search**: Search PDF content for specific strings with page-level results
- **Caching**: Intelligent caching of API responses and search results
- **Resilient**: Retry logic with exponential backoff for network requests
- **Reporting**: Generate comprehensive Excel and CSV reports

## Installation

### From Source

```bash
cd pdfharvest
pip install -e .
```

### Development Installation

```bash
cd pdfharvest
pip install -e ".[dev]"
```

## Usage

### Command Line

```bash
pdfharvest --config config.yaml
```

### Python API

```python
import asyncio
from pdfharvest.src import run

# Run the harvester
result_df = asyncio.run(run("config.yaml"))
print(f"Processed {len(result_df)} DOIs")
```

## Configuration

Create a YAML configuration file:

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

## Input Data Format

Your Excel file should contain a column with DOI identifiers:

| doi | other_columns |
|-----|---------------|
| 10.1000/example1 | ... |
| 10.1000/example2 | ... |

## Output Structure

```
results/
├── logs/
│   └── harvest.log
├── cache/
│   ├── crossref/
│   ├── unpaywall/
│   └── matches/
├── downloads/          # Staging area
├── output_found/       # PDFs with search matches
├── output_notfound/    # PDFs without matches
├── report.xlsx         # Comprehensive results
└── report.csv          # Same data in CSV format
```

## Report Columns

The generated report includes:

- **Metadata**: DOI, title, journal, year, authors, publisher, type
- **Open Access**: is_oa, oa_license, pdf_url
- **Search Results**: match_found, matched_strings, match_pages
- **File Paths**: pdf_final_path

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black src/
isort src/
```

### Type Checking

```bash
mypy src/
```

## Architecture

The system uses a two-stage batched approach:

1. **Stage 1**: Concurrently fetch metadata and download PDFs to staging area
2. **Stage 2**: Process PDFs (search + move to final locations)

This design separates network I/O from CPU-intensive PDF processing, enabling better resource utilization and fault tolerance.

## API Rate Limits

- **Crossref**: No authentication required, but be respectful
- **Unpaywall**: Requires email parameter, free for academic use

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request