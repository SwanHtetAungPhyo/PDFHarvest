"""
PDF Harvest - DOI harvesting and PDF processing system.

A tool for harvesting academic papers via DOI, downloading open access PDFs,
and searching them for specific content.
"""

__version__ = "0.1.0"
__author__ = "PITE Student"

from .orchestrator import run

__all__ = ["run"]
