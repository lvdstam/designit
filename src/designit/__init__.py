"""DesignIt - A DSL for Yourdon-style design documents."""

from designit.parser.parser import parse_file, parse_string
from designit.model.base import DesignDocument

__version__ = "0.1.0"
__all__ = ["parse_file", "parse_string", "DesignDocument", "__version__"]
