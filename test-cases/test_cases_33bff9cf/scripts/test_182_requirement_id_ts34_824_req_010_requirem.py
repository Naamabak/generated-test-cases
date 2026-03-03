```python
# File: tests/test_rpm_parameter_default_values.py

"""
Test Case for:
Requirement ID : TS.34_8.2.4_REQ_010

Requirement:
RPM parameter default values SHALL match those defined in GSMA TS.34 v8.0, Section 8.2.4.

References:
- GSMA TS.34 v8.0, Section 8.2.4, TS.34_8.2.4_REQ_010 (page 50)
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest

# --- Reference: Official TS.34 required RPM defaults (hardcoded here for auditability) ---
TS34_RPM_DEFAULTS = {
    "RPM_Flag": 1,                 # 1 = ON, 0 = OFF
    "N1": 1,                       # Max SW resets/hour by RPM after permanent MM/GMM/EMM reject
    "T1": 60,                      # Minutes before RPM resets modem after permanent reject
    "T1_ext": 48,                  # Hours if T1 == 0xFF
    "F1": 60,                      # Max PDP Activation/PDN Conn Req/hour after ignore
    "F2": 30,                      # Max PDP Activation/PDN Conn Req/hour after Permanent reject
    "F3": 60,                      # Max PDP Activation/PDN Conn Req/hour after Temporary reject
    "F4": 30,                      # Max PDP context or PDN Conn Activation/Deactivation Requests/hour
}

# ---- PLACEHOLDER: Mock firmware/device storage class. Replace this with device API or parameter loader in integration! ----
class MockFirmwareRPMParameterStore:
    """
    Simulates readout of all RPM parameter values as stored in the IoT Communication Module firmware/EEPROM.
    """
    def __init__(self, param_overrides=None):
        values = dict(TS34_RPM_DEFAULTS)
        if param_overrides:
            values.update(param_overrides)
        self.rpm_params = values.copy()

    def get_param(self, key):
        return self.rpm_params[key]

    def get_all_params(self):
        return self.rpm_params.copy()

# ---- PYTEST FIXTURE ----
@pytest.fixture
def rpm_param_store():
    # In production, build from real device config, e.g., query via AT command/API/diagnostic dump!
    mock = MockFirmwareRPMParameterStore()
    yield mock

# ---- TEST SCRIPT ----

def test_rpm_parameter_default_values_match_ts34(rpm_param_store):
    """
    TS.34_8.2.4_REQ_010:
    - All RPM default parameters SHALL be set to the values required in TS.34 v8.0.
    """
    actual = rpm_param_store.get_all_params()
    for key, required in TS34_RPM_DEFAULTS.items():
        assert key in actual, f"Parameter '{key}' missing in module defaults"
        value = actual[key]
        if key == "T1_ext":
            # T1_ext is defined in hours
            assert str(value).lower() in ["48", "48h", "48hrs", "48 hours"], \
                f"T1_ext should be 48 hours by default (got '{value}')"
        elif key == "T1":
            # T1 is in minutes
            assert int(value) == required, f"T1 must be 60 minutes by default (got {value})"
        else:
            assert value == required, f"Parameter '{key}' does not match TS.34 default: got {value}, expected {required}"
    print("RPM parameter default values validated. Current parameters:", actual)

@pytest.mark.parametrize(
    "param,wrong_value",
    [
        ("RPM_Flag", 0),
        ("N1", 2),
        ("T1", 120),
        ("T1_ext", 24),
        ("F1", 25),
        ("F2", 50),
        ("F3", 32),
        ("F4", 80),
    ]
)
def test_rpm_parameter_non_default_detection(param, wrong_value):
    """
    Negative test: Parameters not set to TS.34 defaults must cause test fail.
    """
    overrides = {param: wrong_value}
    store = MockFirmwareRPMParameterStore(param_overrides=overrides)
    expected = TS34_RPM_DEFAULTS[param]
    actual = store.get_param(param)
    assert actual != expected, f"Test setup error: expected a non-default value override"

    with pytest.raises(AssertionError):
        for key in TS34_RPM_DEFAULTS:
            value = store.get_param(key)
            if key == "T1_ext":
                assert str(value).lower() in ["48", "48h", "48hrs", "48 hours"], \
                    f"T1_ext should be 48 hours by default (got '{value}')"
            elif key == "T1":
                assert int(value) == TS34_RPM_DEFAULTS[key], "T1 must be 60 minutes by default"
            else:
                assert value == TS34_RPM_DEFAULTS[key], \
                    f"Parameter '{key}' does not match TS.34 default: got {value}, expected {TS34_RPM_DEFAULTS[key]}"
        print("Negative test should fail if defaults do not match.")

def test_rpm_parameter_keys_are_complete(rpm_param_store):
    """
    Audit completeness: All keys from TS.34_8.2.4_REQ_010 are present in the device/module default RPM parameter block.
    """
    actual = rpm_param_store.get_all_params()
    assert set(actual.keys()) == set(TS34_RPM_DEFAULTS.keys())
    print("All RPM parameters present:", sorted(actual.keys()))

```
---
**Usage:**
- Save as `tests/test_rpm_parameter_default_values.py`
- Replace the mock implementation with your device's real API or extracted configuration in integration/system/lab test.
- Run with:
  ```bash
  pytest tests/test_rpm_parameter_default_values.py
  ```
- Script strictly checks all default values per GSMA TS.34_8.2.4_REQ_010. Print/logging is included for evidence/audit. Negative/edge cases are covered with parameterized tests.
