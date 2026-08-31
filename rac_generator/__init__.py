"""RAC Generator application package."""

__version__ = "0.2.0"

# Keep the public validation API stable while using the enhanced SCT-aware
# implementation that supports legitimate repeated-controller/multi-equipment rows.
from . import logic as _logic
from .sct_validation import validate_project_for_sct

_logic.validate_records_for_sct = validate_project_for_sct
