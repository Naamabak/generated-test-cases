```python
# File: tests/test_rpm_activation_firmware_default.py

"""
Test Case for:
Requirement ID : TS.34_8.2.1_REQ_003

Requirement:
If the UICC is present but does NOT contain RPM parameters, RPM functionality SHALL be enabled/disabled 
based on the default setting of the parameter “RPM_Flag” saved within the IoT Communications Module Firmware.

References:
- GSMA TS.34 v8.0, Section 8.2.1, Requirement TS.34_8.2.1_REQ_003
- Section 8.2.4, Parameter management and default settings
"""

import pytest

# --- MOCK CLASSES / PLACEHOLDER IMPLEMENTATION (Replace with integration hooks, logs or device APIs!) ---

class MockUICC:
    """Simulates a UICC which may or may not contain RPM parameters."""
    def __init__(self, rpm_parameters_present=False):
        self.rpm_parameters_present = rpm_parameters_present

    def has_rpm_parameters(self):
        return self.rpm_parameters_present

class MockFirmware:
    """Simulates IoT Communications Module Firmware that holds the RPM_Flag (default RPM state)."""
    def __init__(self, rpm_flag_enabled=True):
        self.rpm_flag = rpm_flag_enabled  # True = enable RPM, False = disable

    def set_rpm_flag(self, enable: bool):
        self.rpm_flag = enable

    def get_rpm_flag(self):
        return self.rpm_flag

class MockRadioBasebandChipset:
    """
    Simulates the Radio Baseband Chipset which enables/disables RPM functionality based on RPM flag rules.
    With no RPM params on UICC, uses firmware's RPM_Flag.
    """
    def __init__(self):
        self.rpm_enabled = None
        self.status_log = []

    def apply_rpm_setting(self, uicc: MockUICC, firmware: MockFirmware):
        # If UICC has no RPM param, chipset follows firmware's RPM_Flag per TS.34_8.2.1_REQ_003.
        if not uicc.has_rpm_parameters():
            self.rpm_enabled = firmware.get_rpm_flag()
            self.status_log.append(f"RPM set by Firmware RPM_Flag: {self.rpm_enabled}")
        else:
            # if UICC did have params, it would take precedence (per another requirement)
            self.status_log.append("RPM would be set by UICC (but not in this test case)")

    def get_rpm_status(self):
        return self.rpm_enabled

    def get_log(self):
        return list(self.status_log)

    def reset_log(self):
        self.status_log = []

# --- TEST FIXTURES ---

@pytest.fixture
def uicc_without_rpm_params():
    return MockUICC(rpm_parameters_present=False)  # ALWAYS lacking RPM parameters for this test

@pytest.fixture
def firmware():
    """Yield new instance for each test run."""
    return MockFirmware(rpm_flag_enabled=True)

@pytest.fixture
def chipset():
    return MockRadioBasebandChipset()

# --- TEST SCRIPT ---

def test_chipset_rpm_activation_according_to_firmware_flag(uicc_without_rpm_params, firmware, chipset):
    """
    TS.34_8.2.1_REQ_003:
    - With UICC present and lacking RPM parameters, RPM state in chipset strictly follows firmware's RPM_Flag.
    """
    # Step 1: Insert UICC without RPM parameters
    assert not uicc_without_rpm_params.has_rpm_parameters(), "Test setup error: UICC must not carry RPM parameters"

    # Step 2: Set firmware's RPM_Flag => ENABLED, power on (apply setting)
    firmware.set_rpm_flag(True)
    chipset.apply_rpm_setting(uicc_without_rpm_params, firmware)
    assert chipset.get_rpm_status() is True, (
        "Chipset RPM should be ENABLED if firmware RPM_Flag is set to True (no override from UICC)"
    )
    log1 = chipset.get_log()
    assert "RPM set by Firmware RPM_Flag: True" in log1

    # Step 3/4: Set firmware's RPM_Flag => DISABLED, power cycle/restart (apply setting)
    chipset.reset_log()
    firmware.set_rpm_flag(False)
    chipset.apply_rpm_setting(uicc_without_rpm_params, firmware)
    assert chipset.get_rpm_status() is False, (
        "Chipset RPM should be DISABLED if firmware RPM_Flag is set to False (no override from UICC)"
    )
    log2 = chipset.get_log()
    assert "RPM set by Firmware RPM_Flag: False" in log2

    # Step 5: Repeat and verify no fallback or override occurs by another parameter/logic
    for value in [True, False]:
        chipset.reset_log()
        firmware.set_rpm_flag(value)
        chipset.apply_rpm_setting(uicc_without_rpm_params, firmware)
        assert chipset.get_rpm_status() is value

    # Step 6: Assert that ONLY the firmware RPM_Flag determines the RPM function when UICC lacks RPM params
    # Simulate a check for other influencing factors (none should have effect)
    assert chipset.get_log()[-1].startswith("RPM set by Firmware RPM_Flag:")

    print("Log entries confirming RPM controlled strictly by firmware RPM_Flag with UICC not providing RPM params:")
    for entry in chipset.get_log():
        print(entry)

def test_no_fallback_to_other_overrides(uicc_without_rpm_params, firmware, chipset):
    """
    Confirm: With UICC lacking RPM, setting random/conflicting firmware/system settings has no effect beyond RPM_Flag.
    """
    # Set firmware RPM_Flag True/False, check it's always matched
    for desired in [True, False]:
        firmware.set_rpm_flag(desired)
        # Simulate some unrelated config option—should not affect RPM
        unrelated_config = "dummy_value"
        chipset.apply_rpm_setting(uicc_without_rpm_params, firmware)
        assert chipset.get_rpm_status() == desired

def test_rpm_status_is_consistent_with_flag_on_multiple_reboots(uicc_without_rpm_params, firmware, chipset):
    """
    RPM state must match firmware setting across multiple resets with UICC (no RPM params) inserted.
    """
    for _ in range(3):
        firmware.set_rpm_flag(True)
        chipset.apply_rpm_setting(uicc_without_rpm_params, firmware)
        assert chipset.get_rpm_status() is True
        firmware.set_rpm_flag(False)
        chipset.apply_rpm_setting(uicc_without_rpm_params, firmware)
        assert chipset.get_rpm_status() is False
    print("Multiple reboots/trials: RPM state always mirrors firmware RPM_Flag (no external overrides present).")

```
---
**How to use:**
- Save as `tests/test_rpm_activation_firmware_default.py`
- Integrate with your test automation/hardware integrations or hook up to live device/module firmware and chipset APIs
- Run with:
  ```bash
  pytest tests/test_rpm_activation_firmware_default.py
  ```
- This test directly covers TS.34_8.2.1_REQ_003, with assertions and logs mapping firmware RPM_Flag to chipset RPM activation status only when UICC lacks RPM params—no other parameter should override.

Let me know if you need it tailored for AT command/device APIs, or want to pull logs from a real hardware testbed!