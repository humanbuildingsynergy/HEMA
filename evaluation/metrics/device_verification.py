# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# evaluation/metrics/device_verification.py
"""Device state verification for Control Agent evaluation.

Verifies that actual device state changes match expected changes
defined in test scenarios.

Supported check types in expected_changes:
    - {"_changed": True}: Property should have changed (any value)
    - {"_in_range": [min, max]}: Final value should be in range
    - {"_direction": "increase"}: Value should have increased
    - {"_direction": "decrease"}: Value should have decreased
    - {"_direction": "increase", "_min_delta": N}: Value increased by at least N
    - {"_direction": "decrease", "_min_delta": N}: Value decreased by at least N
    - {"_any_of": [check1, check2, ...]}: At least one check must pass (OR logic)
    - Any other value: Exact match required

Example with _any_of (OR logic):
    expected_device_changes={
        "water_heater": {
            "_any_of": [
                {"mode": {"_changed": True}},
                {"scheduled_time": {"_changed": True}},
                {"target_water_temp_f": {"_in_range": [110, 120]}},
            ]
        }
    }
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple


@dataclass
class DeviceStateVerificationResult:
    """Result of verifying device state changes against expected changes."""

    # Overall pass/fail
    verification_passed: bool

    # Detailed results per device
    devices_verified: List[str]  # Devices that were checked
    devices_passed: List[str]  # Devices that met expectations
    devices_failed: List[str]  # Devices that didn't meet expectations

    # Detailed check results
    check_details: Dict[str, Dict[str, Any]]  # {device: {property: {expected, actual, passed}}}

    # Summary stats
    total_checks: int
    passed_checks: int
    failed_checks: int

    # Target accuracy metrics (for Control Agent)
    unintended_device_changes: List[str] = field(default_factory=list)  # Devices changed but not expected
    target_device_accuracy: float = 1.0  # 1.0 if only expected devices changed, else fraction

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "verification_passed": self.verification_passed,
            "devices_verified": self.devices_verified,
            "devices_passed": self.devices_passed,
            "devices_failed": self.devices_failed,
            "check_details": self.check_details,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "unintended_device_changes": self.unintended_device_changes,
            "target_device_accuracy": round(self.target_device_accuracy, 2),
        }


def _evaluate_single_property_check(
    prop_name: str,
    expected_value: Any,
    state_changes: Dict[str, Any],
    device_state_before: Optional[Dict[str, Any]],
    device_state_after: Optional[Dict[str, Any]],
    device_key: str,
) -> Tuple[bool, str, Any, Any]:
    """
    Evaluate a single property check.

    Args:
        prop_name: Name of the property to check
        expected_value: Expected value or check specification
        state_changes: Actual state changes for the device
        device_state_before: Full before snapshot
        device_state_after: Full after snapshot
        device_key: Key of the device being checked

    Returns:
        Tuple of (check_passed, check_type, before_val, after_val)
    """
    prop_change = state_changes.get(prop_name, {})

    # Get before/after values
    before_val = prop_change.get("before") if prop_change else None
    after_val = prop_change.get("after") if prop_change else None

    # If no change recorded, try to get current value from snapshots
    if after_val is None and device_state_after:
        device_after = device_state_after.get("devices", {}).get(device_key, {})
        after_val = device_after.get("current_state", {}).get(prop_name)

    if before_val is None and device_state_before:
        device_before = device_state_before.get("devices", {}).get(device_key, {})
        before_val = device_before.get("current_state", {}).get(prop_name)

    # Evaluate the check
    check_passed = False
    check_type = "exact_match"

    if isinstance(expected_value, dict):
        if expected_value.get("_changed"):
            check_type = "changed"
            check_passed = prop_change and before_val != after_val

        elif "_in_range" in expected_value:
            check_type = "in_range"
            min_val, max_val = expected_value["_in_range"]
            if after_val is not None:
                try:
                    check_passed = min_val <= float(after_val) <= max_val
                except (TypeError, ValueError):
                    check_passed = False

        elif "_direction" in expected_value:
            direction = expected_value["_direction"]
            min_delta = expected_value.get("_min_delta", 0)
            check_type = f"direction_{direction}"
            if min_delta:
                check_type += f"_min{min_delta}"

            if before_val is not None and after_val is not None:
                try:
                    before_num = float(before_val)
                    after_num = float(after_val)
                    actual_delta = after_num - before_num

                    if direction == "increase":
                        check_passed = actual_delta >= min_delta
                    elif direction == "decrease":
                        check_passed = actual_delta <= -min_delta
                except (TypeError, ValueError):
                    check_passed = False
    else:
        # Exact match
        check_passed = after_val == expected_value

    return check_passed, check_type, before_val, after_val


def verify_device_state_changes(
    expected_changes: Optional[Dict[str, Dict]],
    device_state_changes: Optional[Dict[str, Any]],
    device_state_before: Optional[Dict[str, Any]] = None,
    device_state_after: Optional[Dict[str, Any]] = None,
) -> Optional[DeviceStateVerificationResult]:
    """
    Verify that actual device state changes match expected changes.

    Args:
        expected_changes: Expected changes from scenario definition
            Format: {"device_key": {"property": expected_value_or_check}}
            Special checks:
                - {"_changed": True}: Property should have changed (any value)
                - {"_in_range": [min, max]}: Final value should be in range
                - {"_direction": "increase"}: Value should have increased
                - {"_direction": "decrease"}: Value should have decreased
                - {"_any_of": [check1, check2, ...]}: At least one must pass (OR logic)
                - Any other value: Exact match required
        device_state_changes: Actual changes captured during experiment
        device_state_before: Device state snapshot before conversation
        device_state_after: Device state snapshot after conversation

    Returns:
        DeviceStateVerificationResult or None if no expected changes defined
    """
    if not expected_changes:
        return None

    devices_verified = []
    devices_passed = []
    devices_failed = []
    check_details = {}
    total_checks = 0
    passed_checks = 0

    actual_changes_by_device = (
        device_state_changes.get("changes_by_device", {})
        if device_state_changes
        else {}
    )

    # Track expected vs actual device changes for target accuracy
    expected_device_keys = set(expected_changes.keys())
    actual_changed_device_keys = set(actual_changes_by_device.keys())

    for device_key, expected_props in expected_changes.items():
        devices_verified.append(device_key)
        device_check_details = {}
        device_passed = True

        # Get state changes for this device
        device_changes = actual_changes_by_device.get(device_key, {})
        state_changes = device_changes.get("state_changes", {})

        # Check for _any_of (OR logic) at the device level
        if "_any_of" in expected_props:
            total_checks += 1
            any_of_checks = expected_props["_any_of"]
            any_of_passed = False
            any_of_details = []

            # Evaluate each alternative check
            for alt_check in any_of_checks:
                # Each alt_check is a dict like {"mode": {"_changed": True}}
                alt_results = []
                alt_passed = True

                for prop_name, expected_value in alt_check.items():
                    check_passed, check_type, before_val, after_val = _evaluate_single_property_check(
                        prop_name=prop_name,
                        expected_value=expected_value,
                        state_changes=state_changes,
                        device_state_before=device_state_before,
                        device_state_after=device_state_after,
                        device_key=device_key,
                    )

                    alt_results.append({
                        "property": prop_name,
                        "check_type": check_type,
                        "expected": expected_value,
                        "before": before_val,
                        "after": after_val,
                        "passed": check_passed,
                    })

                    if not check_passed:
                        alt_passed = False

                any_of_details.append({
                    "checks": alt_results,
                    "passed": alt_passed,
                })

                if alt_passed:
                    any_of_passed = True

            if any_of_passed:
                passed_checks += 1
            else:
                device_passed = False

            device_check_details["_any_of"] = {
                "check_type": "any_of",
                "alternatives": any_of_details,
                "passed": any_of_passed,
            }

        # Process regular (non _any_of) property checks
        for prop_name, expected_value in expected_props.items():
            if prop_name == "_any_of":
                continue  # Already handled above

            total_checks += 1

            check_passed, check_type, before_val, after_val = _evaluate_single_property_check(
                prop_name=prop_name,
                expected_value=expected_value,
                state_changes=state_changes,
                device_state_before=device_state_before,
                device_state_after=device_state_after,
                device_key=device_key,
            )

            if check_passed:
                passed_checks += 1
            else:
                device_passed = False

            device_check_details[prop_name] = {
                "check_type": check_type,
                "expected": expected_value,
                "before": before_val,
                "after": after_val,
                "passed": check_passed,
            }

        check_details[device_key] = device_check_details

        if device_passed:
            devices_passed.append(device_key)
        else:
            devices_failed.append(device_key)

    # Compute unintended device changes (devices changed but not in expected list)
    unintended_device_changes = list(actual_changed_device_keys - expected_device_keys)

    # Compute target device accuracy
    # If there are no actual changes, accuracy is 1.0 (no unintended changes)
    # Otherwise, it's the fraction of changed devices that were expected
    if actual_changed_device_keys:
        intended_changes = actual_changed_device_keys & expected_device_keys
        target_device_accuracy = len(intended_changes) / len(actual_changed_device_keys)
    else:
        # No devices changed - if we expected changes, this will be caught in verification
        target_device_accuracy = 1.0

    return DeviceStateVerificationResult(
        verification_passed=len(devices_failed) == 0,
        devices_verified=devices_verified,
        devices_passed=devices_passed,
        devices_failed=devices_failed,
        check_details=check_details,
        total_checks=total_checks,
        passed_checks=passed_checks,
        failed_checks=total_checks - passed_checks,
        unintended_device_changes=unintended_device_changes,
        target_device_accuracy=target_device_accuracy,
    )
