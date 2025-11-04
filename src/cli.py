"""
Command-line interface for pdfharvest.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from .orchestrator import run


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Batched DOI harvester: staged downloads → processing → routed outputs"
    )
    parser.add_argument(
        "--config", 
        required=True, 
        help="Path to YAML configuration file"
    )
    parser.add_argument(
        "--version", 
        action="version", 
        version="pdfharvest 0.1.0"
    )
    
    args = parser.parse_args()
    
    # Validate config file exists
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Configuration file '{config_path}' not found", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Run the harvester
        result_df = asyncio.run(run(str(config_path)))
        print(f"Harvesting completed successfully. Processed {len(result_df)} DOIs.")
    except KeyboardInterrupt:
        print("\nHarvesting interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error during harvesting: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()