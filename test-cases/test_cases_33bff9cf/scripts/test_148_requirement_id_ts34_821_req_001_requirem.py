```python
# File: tests/test_rpm_default_parameter_settings.py

"""
Test Case for:
Requirement ID : TS.34_8.2.1_REQ_001

Requirement:
If RPM parameters are NOT present on the UICC, the Radio Baseband Chipset SHALL use default RPM parameter settings
(as specified in TS.34_8.2.4_REQ_010) saved within the IoT Communication Module Firmware.

References:
- GSMA TS.34 v8.0, TS.34_8.2.1_REQ_001, TS.34_8.2.4_REQ_010
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest

# --- MOCK CLASSES / PLACEHOLDERS (replace with real integration in lab/hardware/system) ---

DEFAULT_RPM_FW_PARAMETERS = {
    "RPM_Flag": True,
    "RPM_Param1": 42,
    "RPM_Param2": "default",
    "RPM_Param3": 5,
}  # Example default settings per TS.34_8.2.4_REQ_010

UICC_EMPTY = {}  # No RPM parameters present
UICC_WITH_RPM = {
    "RPM_Flag": False,
    "RPM_Param1": 99,
    "RPM_Param2": "uicc",
    "RPM_Param3": 13,
}

class MockUICC:
    """Simulates a UICC card with optional RPM parameters."""
    def __init__(self, rpm_parameters=None):
        self.rpm_parameters = rpm_parameters or {}

    def has_rpm(self):
        return bool(self.rpm_parameters)

class MockFirmware:
    """Contains default RPM parameter settings as per documentation/config."""
    def __init__(self, defaults):
        self.default_rpm_params = dict(defaults)

class MockRadioBasebandChipset:
    """
    Runtime RPM parameter reporting for the radio baseband chipset.
    Selects parameter source based on UICC presence (UICC > Firmware).
    """
    def __init__(self, firmware: MockFirmware):
        self.firmware = firmware
        self.active_params = dict(firmware.default_rpm_params)
        self.source = "firmware"

    def initialize_with_uicc(self, uicc: MockUICC):
        # If UICC has RPM parameters, use those, otherwise use firmware defaults
        if uicc.has_rpm():
            self.active_params = dict(uicc.rpm_parameters)
            self.source = "uicc"
        else:
            self.active_params = dict(self.firmware.default_rpm_params)
            self.source = "firmware"

    def get_active_params(self):
        return dict(self.active_params)

    def get_source(self):
        return self.source

    def reset(self):
        self.active_params = dict(self.firmware.default_rpm_params)
        self.source = "firmware"


# --- PYTEST FIXTURES ---

@pytest.fixture
def firmware():
    return MockFirmware(DEFAULT_RPM_FW_PARAMETERS)

@pytest.fixture
def chipset(firmware):
    return MockRadioBasebandChipset(firmware)

@pytest.fixture
def blank_uicc():
    return MockUICC(UICC_EMPTY.copy())

@pytest.fixture
def uicc_with_rpm():
    return MockUICC(UICC_WITH_RPM.copy())

# --- TEST SCRIPT ---

def test_chipset_uses_fw_defaults_when_no_uicc_rpm(chipset, firmware, blank_uicc):
    """
    Verify that when UICC does not have RPM parameters, the chipset uses ONLY firmware defaults.
    """
    # Step 1–2: Insert blank UICC, power on/init system
    chipset.initialize_with_uicc(blank_uicc)

    # Step 3: Query chipset's active RPM parameters
    active_params = chipset.get_active_params()

    # Step 4: Assert active RPM parameter values match firmware defaults exactly
    assert chipset.get_source() == "firmware", "RPM parameter source should be 'firmware' when UICC is empty."
    assert active_params == firmware.default_rpm_params, (
        f"Chipset RPM parameters {active_params} do not match firmware defaults {firmware.default_rpm_params}"
    )

    # Step 5: Optionally repeat after reset
    chipset.reset()
    chipset.initialize_with_uicc(blank_uicc)
    assert chipset.get_active_params() == firmware.default_rpm_params

    print("Test PASSED: Chipset uses default RPM settings from firmware when UICC does not provide RPM parameters.")

def test_chipset_uses_uicc_params_when_present(chipset, uicc_with_rpm):
    """
    Negative/precedence control: When UICC has RPM parameters, chipset uses UICC params (not FW defaults).
    """
    # Insert UICC with explicit RPM parameters, initialize
    chipset.initialize_with_uicc(uicc_with_rpm)
    active_params = chipset.get_active_params()
    assert chipset.get_source() == "uicc", "RPM parameter source should be 'uicc' if UICC provides RPM params."
    expected = uicc_with_rpm.rpm_parameters
    assert active_params == expected, (
        f"Chipset RPM parameters {active_params} do not match UICC-provided RPM params {expected}"
    )
    # Confirm not equal to firmware defaults
    assert active_params != DEFAULT_RPM_FW_PARAMETERS

    print("Test PASSED: Chipset correctly prioritizes UICC-provided RPM parameters over firmware defaults.")

@pytest.mark.parametrize(
    "uicc_params,expected_source,expected_params",
    [
        (UICC_EMPTY, "firmware", DEFAULT_RPM_FW_PARAMETERS),
        (UICC_WITH_RPM, "uicc", UICC_WITH_RPM)
    ]
)
def test_rpm_parameter_selection_logic(firmware, uicc_params, expected_source, expected_params):
    """
    Both positive and negative controls: cover both parameter source cases in one convenience test.
    """
    chipset = MockRadioBasebandChipset(firmware)
    uicc = MockUICC(uicc_params.copy())
    chipset.initialize_with_uicc(uicc)
    assert chipset.get_source() == expected_source
    assert chipset.get_active_params() == expected_params

    # Output test evidence for audit/logging
    print(f"RPM source: {chipset.get_source()}, active parameters: {chipset.get_active_params()}")
```
---

**How to use/adapt:**
- Place as `tests/test_rpm_default_parameter_settings.py`.
- Replace mock class logic with hardware/device integration or actual parameter reporting API.
- Add additional default/explicit RPM parameters as per TS.34_8.2.4_REQ_010 and your firmware documentation.
- Run with:
  ```bash
  pytest tests/test_rpm_default_parameter_settings.py
  ```
- Script covers both the default case (UICC empty) and precedence case (UICC with parameters) per TS.34_8.2.1_REQ_001/002.

Let me know if you need direct test hooks for real module/AT command sets or hardware debug logs!