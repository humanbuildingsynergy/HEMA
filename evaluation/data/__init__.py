# evaluation/data/__init__.py
"""Data utilities for evaluation.

Contains ground truth extraction and household metrics
for factual accuracy verification and case study comparisons.
"""

from .ground_truth import (
    GroundTruthSummary,
    extract_ground_truth,
    get_current_ground_truth,
)
from .household_metrics import (
    HouseholdProfile,
    extract_household_profile,
    format_household_comparison,
)

__all__ = [
    # Ground truth
    "GroundTruthSummary",
    "extract_ground_truth",
    "get_current_ground_truth",
    # Household metrics
    "HouseholdProfile",
    "extract_household_profile",
    "format_household_comparison",
]
