```python
# File: tests/test_rpm_parameters_reset_on_uicc_change.py

"""
Test Case for:
Requirement ID : TS.34_8.2.4_REQ_003

Requirement:
All RPM parameters SHOULD be reset upon UICC change, and the determination of UICC change SHOULD be based on ICCID.

References:
- GSMA TS.34 v8.0, Section 8.2.4, Requirement TS.34_8.2.4_REQ_003
- TS.34_8.2.4_REQ_010 (list of RPM parameters)
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest

# -- Define a sample full set of RPM parameter names as per TS.34_8.2.4_REQ_010 --
RPM_PARAMETER_KEYS = [
    "RPM_Flag",
    "RPM_MaxAttachAttempts",
    "RPM_Timer1",
    "RPM_Timer2",
    "RPM_ConnHoldTime",
    "RPM_BackoffFactor",
    "RPM_ProfileID",
    "RPM_LastUpdate",
]

# Default values for RPM parameters (customize according to actual device/firmware specification)
DEFAULT_RPM_PARAMS = {
    "RPM_Flag": True,
    "RPM_MaxAttachAttempts": 10,
    "RPM_Timer1": 5,
    "RPM_Timer2": 20,
    "RPM_ConnHoldTime": 120,
    "RPM_BackoffFactor": 3,
    "RPM_ProfileID": "DEF01",
    "RPM_LastUpdate": "N/A"
}

class MockUICC:
    """Simulates a UICC card with unique ICCID value."""
    def __init__(self, iccid, rpm_params=None):
        self.iccid = iccid
        # Optionally UICC can supply its own RPM params, otherwise use device/firmware defaults
        self.rpm_params = rpm_params if rpm_params is not None else {}

    def get_iccid(self):
        return self.iccid

    def get_rpm_params(self):
        return dict(self.rpm_params)    # Copy for safety

class MockCommModule:
    """
    Simulates an IoT Communication Module with the ability to read and set RPM parameters,
    track currently inserted UICC by ICCID, and reset RPM params on UICC change.
    """
    def __init__(self, firmware_defaults):
        self.firmware_defaults = dict(firmware_defaults)
        self.inserted_iccid = None
        self.known_iccid = None     # Last ICCID seen (for change detection)
        self.rpm_parameters = dict(firmware_defaults)
        self.log = []

    def power_on(self, uicc: MockUICC):
        """
        Detect if UICC (ICCID) has changed on power on. If so, reset RPM parameters to default or UICC-provided.
        """
        iccid = uicc.get_iccid()
        self.log.append(f"Power on: UICC inserted w/ ICCID={iccid}")
        if self.known_iccid is None or iccid != self.known_iccid:
            # Detected UICC change, reset RPM parameters
            self.log.append(f"UICC/ICCID change detected ({self.known_iccid!r} -> {iccid!r}). Resetting RPM parameters!")
            if uicc.get_rpm_params():
                self.rpm_parameters = dict(uicc.get_rpm_params())
                self.log.append("RPM parameters imported from UICC.")
            else:
                self.rpm_parameters = dict(self.firmware_defaults)
                self.log.append("RPM parameters set to firmware defaults.")
            self.known_iccid = iccid
        self.inserted_iccid = iccid

    def power_off(self):
        self.log.append(f"Device power off (ICCID={self.inserted_iccid})")

    def set_rpm_param(self, key, value):
        if key not in RPM_PARAMETER_KEYS:
            raise ValueError("Unknown RPM parameter")
        self.rpm_parameters[key] = value
        self.log.append(f"RPM parameter '{key}' set to {value}")

    def get_rpm_params(self):
        return dict(self.rpm_parameters)

    def get_current_iccid(self):
        return self.inserted_iccid

    def get_log(self):
        return list(self.log)

    def reset(self):
        self.rpm_parameters = dict(self.firmware_defaults)
        self.inserted_iccid = None
        self.known_iccid = None
        self.log = []

# --- PYTEST FIXTURE ---

@pytest.fixture
def comm_module():
    mod = MockCommModule(DEFAULT_RPM_PARAMS)
    yield mod
    mod.reset()

@pytest.fixture
def uicc_1():
    return MockUICC(iccid="1234567890123456789")     # Test ICCID 1

@pytest.fixture
def uicc_2():
    return MockUICC(iccid="9876543210987654321")     # Test ICCID 2, different value

# --- TEST SCRIPT ---

def test_rpm_parameters_are_reset_on_uicc_iccid_change(comm_module, uicc_1, uicc_2):
    """
    a) Upon UICC (ICCID) swap, all RPM parameters are reset to default (or UICC-provided).
    b) Determination of UICC change is explicitly based on ICCID.
    c) Re-inserting original UICC resets RPM params again, confirming ICCID-based detection.
    """

    # Step 1: Insert UICC #1 and power on the device
    comm_module.power_on(uicc_1)
    iccid_1 = comm_module.get_current_iccid()
    assert iccid_1 == "1234567890123456789"

    # Step 2: Set/modify RPM parameters to known non-default values
    comm_module.set_rpm_param("RPM_Flag", False)
    comm_module.set_rpm_param("RPM_MaxAttachAttempts", 88)
    before_params = comm_module.get_rpm_params().copy()
    for k in before_params:
        # At least one param must be non-default now
        if k in ["RPM_Flag", "RPM_MaxAttachAttempts"]:
            assert before_params[k] != DEFAULT_RPM_PARAMS[k]

    # Step 3: Power off
    comm_module.power_off()

    # Step 4: Remove UICC #1, insert UICC #2 (ICCID differs), power on
    comm_module.power_on(uicc_2)

    # Step 5: Retrieve/log all RPM parameter values - must be reset to default (firmware) or from UICC if provided
    after_params = comm_module.get_rpm_params()
    # For this test (UICC_2 w/o custom params), must match firmware defaults
    assert after_params == DEFAULT_RPM_PARAMS, "RPM params did not reset to default after ICCID/UICC change"

    # Step 7: System detects ICCID change
    assert comm_module.known_iccid == uicc_2.iccid
    assert comm_module.known_iccid != iccid_1

    # Step 8: Optionally, swap back to original UICC and repeat - confirm RPM params reset again
    comm_module.power_off()
    comm_module.power_on(uicc_1)
    after_params2 = comm_module.get_rpm_params()
    assert after_params2 == DEFAULT_RPM_PARAMS
    assert comm_module.known_iccid == iccid_1

    # Check log evidence of ICCID-based detection and reset
    logs = comm_module.get_log()
    assert any("UICC/ICCID change detected" in l for l in logs)
    assert logs.count("RPM parameters set to firmware defaults.") >= 2, "RPM defaults not restored on each ICCID change"

    print("Test log:")
    for l in logs:
        print(l)

@pytest.mark.parametrize("custom_params", [
    {"RPM_Flag": False, "RPM_MaxAttachAttempts": 5, "RPM_LastUpdate": "2024-08-15T04:00:00Z"},
    {"RPM_Timer1": 67, "RPM_Timer2": 149},
])
def test_rpm_parameters_reset_and_imported_from_uicc(comm_module, uicc_1, custom_params):
    """
    If new UICC contains RPM parameters, after ICCID change the RPM params must be imported from UICC,
    not just reset to defaults.
    """
    uicc_custom = MockUICC(iccid="2222222222222222222", rpm_params=custom_params)
    comm_module.power_on(uicc_custom)
    after_params = comm_module.get_rpm_params()
    # Parameters provided by UICC must take effect (others remain at default)
    for k, v in custom_params.items():
        assert after_params[k] == v, f"RPM param {k} did not update from UICC: expected {v}, got {after_params[k]}"
    for k in DEFAULT_RPM_PARAMS:
        if k not in custom_params:
            assert after_params[k] == DEFAULT_RPM_PARAMS[k], f"RPM param {k} should remain at default"
    print("After UICC with custom params:", after_params)

def test_iccid_change_is_the_basis_for_rpm_reset(comm_module, uicc_1, uicc_2):
    """
    The reset mechanism is strictly tied to ICCID change. No reset if the same ICCID is re-inserted.
    """
    # Insert UICC #1 and power on
    comm_module.power_on(uicc_1)
    comm_module.set_rpm_param("RPM_ProfileID", "AABBCC")
    # Power cycle with same UICC/ICCID (should NOT trigger reset)
    comm_module.power_off()
    comm_module.power_on(uicc_1)
    after_params_same = comm_module.get_rpm_params()
    # ProfileID should NOT be reset if ICCID is unchanged
    assert after_params_same["RPM_ProfileID"] == "AABBCC"
    # Now swap ICCID (insert different UICC)
    comm_module.power_off()
    comm_module.power_on(uicc_2)
    # ProfileID should be reset
    after_params_new = comm_module.get_rpm_params()
    assert after_params_new["RPM_ProfileID"] == DEFAULT_RPM_PARAMS["RPM_ProfileID"]

    print("ICCID change = parameter reset; no change = no reset. Log: ", comm_module.get_log())
```
---

**Instructions:**

- Save as `tests/test_rpm_parameters_reset_on_uicc_change.py`.
- Integrate with your real parameter read/write and UICC/ICCID management interface for system/lab/hardware test.
- Run using:
  ```bash
  pytest tests/test_rpm_parameters_reset_on_uicc_change.py
  ```
- All assertions, structure, and logs map directly to TS.34_8.2.4_REQ_003 (ICCID-based UICC change resets RPM to default or UICC-supplied, per requirements).
- Print/logs provide audit evidence for compliance.

Let me know if your real RPM/UICC API has additional hooks or if you want laboratory AT command tests or device log scraping integration!