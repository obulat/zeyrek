"""Top-level package for Turkish Lemmatizer."""

__author__ = """Olga Bulat"""
__email__ = "obulat@gmail.com"
from importlib.metadata import version

__version__ = version("zeyrek")

from .morphology import MorphAnalyzer

__all__ = ["MorphAnalyzer"]
