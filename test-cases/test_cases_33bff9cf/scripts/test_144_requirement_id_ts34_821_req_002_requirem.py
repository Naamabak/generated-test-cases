```python
# File: tests/test_rpm_activation_control_uicc_precedence.py

"""
Test Case for:
Requirement ID : TS.34_8.2.1_REQ_002

Requirement:
If the UICC contains RPM parameters, the IoT Communications Module SHALL enable/disable RPM functionality 
within the Radio Baseband Chipset strictly based on the "RPM_Flag" parameter on the UICC.
UICC-based parameters MUST take precedence over any RPM parameters configured in the module firmware.

References:
- GSMA TS.34 v8.0, Section 8.2.1, TS.34_8.2.1_REQ_002
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest

# --- MOCK CLASSES / PLACEHOLDER IMPLEMENTATION ---
# Replace these mocks with your live integration, control APIs, or device logs/harness hooks.
class MockUICC:
    """Simulates a UICC with RPM parameter storage."""
    def __init__(self, rpm_flag_enabled=True):
        # True = "enabled", False = "disabled"
        self.rpm_flag = rpm_flag_enabled

    def set_rpm_flag(self, enable: bool):
        self.rpm_flag = enable

    def get_rpm_flag(self):
        return self.rpm_flag

class MockFirmware:
    """Simulates the Communication Module firmware setting for RPM (for conflicting/default demonstration)."""
    def __init__(self, rpm_enabled=True):
        self.firmware_rpm_flag = rpm_enabled

    def set_firmware_rpm(self, enable: bool):
        self.firmware_rpm_flag = enable

    def get_firmware_rpm(self):
        return self.firmware_rpm_flag

class MockRadioBasebandChipset:
    """Simulates the chipset, whose RPM functionality state is determined by UICC or firmware parameter (per precedence)."""
    def __init__(self):
        self.rpm_enabled = None
        self.status_log = []

    def apply_rpm_setting(self, uicc: MockUICC, firmware: MockFirmware):
        """Apply only UICC-based setting if present (per TS.34_8.2.1_REQ_002)."""
        if uicc is not None:
            self.rpm_enabled = uicc.get_rpm_flag()
            self.status_log.append(f"RPM set by UICC (RPM_Flag): {self.rpm_enabled}")
        else:
            # Would only use firmware flag if UICC is None or has no RPM_Flag (TS.34_8.2.1_REQ_003)
            self.rpm_enabled = firmware.get_firmware_rpm()
            self.status_log.append(f"RPM set by Firmware (default/config): {self.rpm_enabled}")

    def get_rpm_status(self):
        return self.rpm_enabled

    def get_log(self):
        return list(self.status_log)

    def reset_log(self):
        self.status_log = []


# --- TEST FIXTURES ---
@pytest.fixture
def uicc():
    return MockUICC(rpm_flag_enabled=True)

@pytest.fixture
def firmware():
    return MockFirmware(rpm_enabled=False)

@pytest.fixture
def chipset():
    return MockRadioBasebandChipset()

# --- TEST SCRIPT ---
def test_uicc_rpm_flag_precedence_over_firmware(uicc, firmware, chipset):
    """
    TS.34_8.2.1_REQ_002:
    - If UICC RPM_Flag is present, chipset always follows UICC setting, regardless of firmware setting.
    - UICC-based parameters take precedence in all scenarios.
    """

    # 1. RPM_Flag on UICC ENABLED, firmware DISABLED (conflict, should follow UICC)
    uicc.set_rpm_flag(True)
    firmware.set_firmware_rpm(False)
    chipset.apply_rpm_setting(uicc, firmware)
    assert chipset.get_rpm_status() is True, (
        "Chipset RPM should follow UICC RPM_Flag=ENABLED, not firmware setting"
    )
    log1 = chipset.get_log()
    assert any("RPM set by UICC" in entry for entry in log1)
    chipset.reset_log()

    # 2. RPM_Flag on UICC DISABLED, firmware ENABLED (conflict, should follow UICC)
    uicc.set_rpm_flag(False)
    firmware.set_firmware_rpm(True)
    chipset.apply_rpm_setting(uicc, firmware)
    assert chipset.get_rpm_status() is False, (
        "Chipset RPM should follow UICC RPM_Flag=DISABLED, not firmware setting"
    )
    log2 = chipset.get_log()
    assert any("RPM set by UICC" in entry for entry in log2)
    chipset.reset_log()

    # 3. RPM_Flag on UICC ENABLED, firmware ENABLED (agree, should follow UICC)
    uicc.set_rpm_flag(True)
    firmware.set_firmware_rpm(True)
    chipset.apply_rpm_setting(uicc, firmware)
    assert chipset.get_rpm_status() is True, (
        "Chipset RPM should match UICC RPM_Flag=ENABLED when in agreement"
    )
    chipset.reset_log()

    # 4. RPM_Flag on UICC DISABLED, firmware DISABLED (agree, should follow UICC)
    uicc.set_rpm_flag(False)
    firmware.set_firmware_rpm(False)
    chipset.apply_rpm_setting(uicc, firmware)
    assert chipset.get_rpm_status() is False, (
        "Chipset RPM should match UICC RPM_Flag=DISABLED when in agreement"
    )
    chipset.reset_log()

    # 5. Attempt to change only firmware RPM setting while UICC RPM_Flag present (should have no effect)
    uicc.set_rpm_flag(True)
    firmware.set_firmware_rpm(False)
    chipset.apply_rpm_setting(uicc, firmware)  # Should follow UICC (ENABLED)
    assert chipset.get_rpm_status() is True
    firmware.set_firmware_rpm(True)            # Change firmware setting only
    chipset.apply_rpm_setting(uicc, firmware)  # Still should follow UICC (ENABLED)
    assert chipset.get_rpm_status() is True, "Firmware change should have no effect when UICC RPM_Flag is present"
    chipset.reset_log()

    print("All UICC RPM_Flag precedence and firmware setting conflict checks passed.")

def test_rpm_flag_pass_fail_criteria_summary():
    """
    Exit Criteria:
    - Chipset RPM strictly follows UICC RPM_Flag if present, regardless of firmware config.
    - UICC RPM parameter always takes precedence.
    - Log output/trace confirms activation/deactivation matches UICC for each tested scenario.
    """
    # This is covered implicitly in the above test; just output summary for compliance log.
    print("Test covers strict UICC RPM_Flag precedence. Firmware config ignored where UICC RPM is present. See test logs for traceability.")

```
---

**How to use/adapt:**
- Save as `tests/test_rpm_activation_control_uicc_precedence.py`
- Replace mocks with your device/module/testbed/hardware integration logic as available.
- Run with:
  ```bash
  pytest tests/test_rpm_activation_control_uicc_precedence.py
  ```
- Assertions and logging map directly to TS.34_8.2.1_REQ_002 requirement and pass/fail criteria (firmware override, UICC precedence, log evidence).

Let me know if you need direct integration with UICC test cards, hardware/AT command scripting, or Radio Baseband logs for full system compliance!