"""
DevContainer Tools - Simplified DevContainer management for teams

This package provides a streamlined interface for managing development containers,
with automatic configuration merging and simplified command-line options.
"""

__version__ = "0.0.1"
__author__ = "Ryo Koizumi <koizumiryo@gmail.com>"

from .cli import cli

__all__ = ["cli"]
