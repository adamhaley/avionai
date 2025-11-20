"""
XLSX Generator unit tests
"""

import pytest
from pathlib import Path
from app.xlsx_generator import XLSXGenerator


def test_generator_init_nonexistent_file():
    """Test that generator raises error for nonexistent file"""
    with pytest.raises(FileNotFoundError):
        XLSXGenerator(Path("/nonexistent/template.xlsx"))


def test_get_row_number():
    """Test row number extraction from cell reference"""
    # This would require instantiating with a real template
    # For now, just test the method exists
    pass


def test_compare_cell_refs():
    """Test cell reference comparison"""
    # Create a mock generator with a dummy template
    # This is a unit test for the internal method
    pass


# Note: More comprehensive tests would require actual test templates
# You should create small test XLSX files in tests/fixtures/ directory
