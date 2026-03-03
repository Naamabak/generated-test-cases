```python
# File: tests/test_connection_efficiency_rule_structure.py

"""
Test Case for:
Requirement ID : TS.34_7.2.1_REQ_003

Requirement:
Each Individual Connection Efficiency Rule SHALL contain:
  - A set of 1 to 15 conditions related to the IoT Communication Module status (e.g., Time of day, Device location, IMSI, ICCID, IMEI, etc.)
  - A set of 0 to 31 applicable Service Classes for the Rule
  - A single, specific action (block traffic, retry connection, switch network, ...)

References:
- GSMA TS.34 v8.0, Section 7.2.1, Requirement TS.34_7.2.1_REQ_003
"""

import pytest

# ---- MOCK/PSEUDO-SYSTEM CLASSES (replace with real policy engine, data model or API libraries!) ----

class ConnectionEfficiencyRule:
    """
    Example class representing an Individual Connection Efficiency Rule.
    In a real system, this could be loaded via API, configuration interface, or a data model.
    """
    def __init__(self, conditions, service_classes, action):
        # Each argument is expected to be:
        # - conditions: list of dicts describing status checks ("type": e.g. "TimeOfDay", "IMSI", etc.)
        # - service_classes: list of service class names (could be empty, max 31)
        # - action: string naming the action e.g. "block_traffic", "switch_network", etc.
        self.conditions = list(conditions)
        self.service_classes = list(service_classes)
        self.action = action

    def is_valid(self):
        return (
            1 <= len(self.conditions) <= 15 and
            0 <= len(self.service_classes) <= 31 and
            bool(self.action)
        )

    def missing_elements(self):
        issues = []
        if not (1 <= len(self.conditions) <= 15):
            issues.append("missing_or_invalid_conditions")
        if not (0 <= len(self.service_classes) <= 31):
            issues.append("invalid_service_classes")
        if not self.action:
            issues.append("missing_action")
        return issues

# ---- FIXTURE FOR TESTED RULES ----

@pytest.fixture
def example_rules():
    """
    Creates a set of valid and intentionally invalid Connection Efficiency Rules for testing.
    Replace these with real API calls or configuration file loads in production.
    """
    rules = [
        # Valid Rule 1
        ConnectionEfficiencyRule(
            conditions=[{"type": "TimeOfDay", "value": "08:00-20:00"}],
            service_classes=["Telemetry", "Alarms"],
            action="block_traffic"
        ),
        # Valid Rule 2
        ConnectionEfficiencyRule(
            conditions=[
                {"type": "IMSI", "pattern": "23401*"},
                {"type": "CellLocation", "cell_id": "123-456"}
            ],
            service_classes=["OTAUpdates"],
            action="retry_connection"
        ),
        # Valid Rule 3 (edge: 15 conditions, 0 services, one action)
        ConnectionEfficiencyRule(
            conditions=[{"type": f"ICCIDSet_{i}"} for i in range(15)],
            service_classes=[],
            action="switch_network"
        ),
        # Invalid: missing action
        ConnectionEfficiencyRule(
            conditions=[{"type": "IMEI", "value": "123456789012345"}],
            service_classes=["Messaging"],
            action=""
        ),
        # Invalid: missing all conditions
        ConnectionEfficiencyRule(
            conditions=[],
            service_classes=["DataUpload"],
            action="block_traffic"
        ),
        # Invalid: more than 31 service classes
        ConnectionEfficiencyRule(
            conditions=[{"type": "TimeOfDay", "value": "00:00-06:00"}],
            service_classes=[f"Class{i}" for i in range(32)],
            action="restrict_bandwidth"
        ),
    ]
    return rules

# ---- TEST SCRIPTS ----

def test_valid_rules_meet_all_structure_requirements(example_rules):
    """ Test that all valid rules have (a) 1-15 conditions, (b) 0-31 service classes, (c) one action. """
    # Here we treat the first three as valid for the purpose of the script
    for i, rule in enumerate(example_rules[:3]):
        assert rule.is_valid(), f"Rule {i+1} is invalid: issues={rule.missing_elements()}"
        # Check structure in detail
        assert 1 <= len(rule.conditions) <= 15, "Rule missing required conditions count"
        assert 0 <= len(rule.service_classes) <= 31, "Rule has out-of-bounds service classes"
        assert bool(rule.action), "Rule missing explicit action"

def test_each_rule_has_no_missing_elements(example_rules):
    """ No rule (in the valid set) should miss any required structural element. """
    for i, rule in enumerate(example_rules[:3]):
        assert not rule.missing_elements(), f"Rule {i+1} missing elements: {rule.missing_elements()}"

def test_invalid_rules_are_rejected(example_rules):
    """
    Attempt to instantiate rules with missing elements (condition(s), service classes, or action).
    These should be recognized and rejected as invalid.
    """
    # 4th rule: missing action
    assert not example_rules[3].is_valid()
    assert "missing_action" in example_rules[3].missing_elements()
    # 5th rule: missing conditions
    assert not example_rules[4].is_valid()
    assert "missing_or_invalid_conditions" in example_rules[4].missing_elements()
    # 6th rule: too many service classes
    assert not example_rules[5].is_valid()
    assert "invalid_service_classes" in example_rules[5].missing_elements()

def test_rule_structures_are_documented(example_rules):
    """
    Document the parameter structure of each rule (for conformance evidence/audit).
    """
    for idx, rule in enumerate(example_rules[:3], 1):
        print(f"Rule {idx}:")
        print(f"  Conditions ({len(rule.conditions)}): {rule.conditions}")
        print(f"  Service Classes ({len(rule.service_classes)}): {rule.service_classes}")
        print(f"  Action: {rule.action}")

def test_rule_creation_interface_enforces_constraints():
    """
    Simulate creation interface (API, config, or policy manager) enforcing element presence.
    For a real API, this would expect exceptions or failed creation for missing/invalid element(s).
    """
    def try_create_rule(conditions, service_classes, action):
        try:
            rule = ConnectionEfficiencyRule(conditions, service_classes, action)
            if not rule.is_valid():
                raise ValueError(f"Invalid rule structure: {rule.missing_elements()}")
            return True
        except Exception:
            return False

    # Valid: should succeed
    assert try_create_rule(
        [{"type": "TimeOfDay"}], ["A"], "block"
    )
    # Invalid: no action
    assert not try_create_rule([{"type": "TimeOfDay"}], ["B"], "")
    # Invalid: no conditions
    assert not try_create_rule([], ["A", "B"], "block")
    # Invalid: too many service classes
    assert not try_create_rule(
        [{"type": "TimeOfDay"}], [f"S{i}" for i in range(32)], "block"
    )

```

---

**How to use/adapt:**
- Save as `tests/test_connection_efficiency_rule_structure.py`.
- Replace the `ConnectionEfficiencyRule` and sample rule creation/inspection with your real system's rule/model/API or import device config directly.
- Run with:
  ```bash
  pytest tests/test_connection_efficiency_rule_structure.py
  ```
- All assertions and print statements cover requirements (a–d) and facilitate evidence capture for audits or compliance reviews.

**Coverage:**
- Checks the presence and correct count of required elements in each rule.
- Verifies rejection of invalid rule attempts (missing/too many elements).
- Prints details for each rule for traceability.
- Easily adaptable to real APIs, management platforms, or configuration sources.