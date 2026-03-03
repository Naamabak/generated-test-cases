```python
# File: tests/test_rpm_parameter_readability.py

"""
Test Case for:
Requirement ID : TS.34_8.2.1_REQ_007

Requirement:
The IoT Communication Module SHALL provide a means to read the RPM Parameters listed in TS.34_8.2.4_REQ_010.

References:
- GSMA TS.34 v8.0, TS.34_8.2.1_REQ_007 (RPM Parameter Readability)
- GSMA TS.34 v8.0, TS.34_8.2.4_REQ_010 (RPM Parameter List/Content)
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest

# --- ASSUMED/PARTIAL RPM PARAMETER LIST PER TS.34_8.2.4_REQ_010 ---
REQUIRED_RPM_PARAMETERS = [
    "RPM_Flag",
    "RPM_MaxAttachAttempts",
    "RPM_Timer1",
    "RPM_Timer2",
    "RPM_ConnHoldTime",
    "RPM_BackoffFactor",
    "RPM_ProfileID",
    "RPM_LastUpdate",
    # Add all additional parameters listed in TS.34_8.2.4_REQ_010 as needed.
]

# --- MOCK IMPLEMENTATION FOR TESTING ---
# Replace with your actual device/module/API or AT/diagnostics integration!

class MockUICC:
    """
    Simulates a UICC: may present a subset of RPM parameters or none.
    """
    def __init__(self, rpm_params=None):
        self.rpm_params = rpm_params or {}

    def get_param(self, key):
        return self.rpm_params.get(key, None)

    def has_rpm_parameters(self):
        return bool(self.rpm_params)

class MockFirmwareParams:
    """
    Simulates default/module-stored RPM parameter set.
    """
    def __init__(self, defaults):
        self.defaults = defaults

    def get_param(self, key):
        return self.defaults.get(key, None)

class MockIoTCommModule:
    """
    Main test object, simulates the ability to read parameters and apply precedence (UICC > Firmware).
    Supports a uniform 'read_rpm_param' interface to emulate AT commands, DIAG API, or UI.
    """
    def __init__(self, uicc: MockUICC, firmware: MockFirmwareParams):
        self.uicc = uicc
        self.firmware = firmware
        self.read_log = []

    def read_rpm_param(self, key):
        # Precedence: UICC if present, otherwise firmware/module defaults.
        value = (
            self.uicc.get_param(key)
            if self.uicc.has_rpm_parameters() and key in self.uicc.rpm_params
            else self.firmware.get_param(key)
        )
        self.read_log.append((key, value, "uicc" if key in self.uicc.rpm_params else "firmware"))
        return value

    def read_all_rpm_parameters(self):
        results = {}
        for param in REQUIRED_RPM_PARAMETERS:
            results[param] = self.read_rpm_param(param)
        return results

    def get_read_log(self):
        return list(self.read_log)

    def reset_log(self):
        self.read_log = []

# --- TEST FIXTURES ---

@pytest.fixture
def firmware_defaults():
    # Example default values for all required parameters (customize as needed)
    return {
        "RPM_Flag": True,
        "RPM_MaxAttachAttempts": 10,
        "RPM_Timer1": 5,
        "RPM_Timer2": 15,
        "RPM_ConnHoldTime": 90,
        "RPM_BackoffFactor": 3,
        "RPM_ProfileID": "DEF01",
        "RPM_LastUpdate": "2024-07-03T08:30:00Z"
    }

@pytest.fixture
def uicc_with_params():
    # Example: UICC provides a subset of RPM parameters (preference will be given to those over firmware)
    return MockUICC({
        "RPM_Flag": False,
        "RPM_ConnHoldTime": 60,
        "RPM_ProfileID": "SIM99"
    })

@pytest.fixture
def uicc_no_params():
    # Example: Blank/test UICC provides no RPM parameters
    return MockUICC({})

@pytest.fixture
def comm_module_with_uicc_and_fw(uicc_with_params, firmware_defaults):
    fw = MockFirmwareParams(firmware_defaults)
    return MockIoTCommModule(uicc_with_params, fw)

@pytest.fixture
def comm_module_fw_only(uicc_no_params, firmware_defaults):
    fw = MockFirmwareParams(firmware_defaults)
    return MockIoTCommModule(uicc_no_params, fw)

# --- TEST SCRIPT ---

def test_read_all_rpm_parameters_fw_only(comm_module_fw_only, firmware_defaults):
    """
    a) When UICC provides no RPM parameters, all parameter reads return the firmware/module values.
    """
    results = comm_module_fw_only.read_all_rpm_parameters()
    # All required RPM parameters must be present and returned without error
    for key in REQUIRED_RPM_PARAMETERS:
        assert results[key] == firmware_defaults.get(key), f"Expected {key} from firmware, got {results[key]}"
    log = comm_module_fw_only.get_read_log()
    assert all("firmware" in src for _, _, src in log), "Unexpected source precedence in RPM param reads (should be 'firmware')"
    print("FW-only RPM parameter read log:", log)

def test_read_all_rpm_parameters_with_uicc(comm_module_with_uicc_and_fw, firmware_defaults, uicc_with_params):
    """
    b) When UICC provides RPM parameters, those are read in preference to firmware, others fall back to firmware.
    """
    results = comm_module_with_uicc_and_fw.read_all_rpm_parameters()
    # Check returned parameters match UICC for provided subset, firmware for the rest
    for key in REQUIRED_RPM_PARAMETERS:
        expected = uicc_with_params.get_param(key) if key in uicc_with_params.rpm_params else firmware_defaults.get(key)
        assert results[key] == expected, f"Parameter {key}: expected {expected}, got {results[key]}"
    # Precedence checks in log
    log = comm_module_with_uicc_and_fw.get_read_log()
    assert any("uicc" in src for _, _, src in log)
    assert any("firmware" in src for _, _, src in log)
    print("Hybrid RPM parameter read log (with UICC params):", log)

def test_all_rpm_parameter_names_and_accessibility(comm_module_fw_only):
    """
    a) The interface delivers a value for each named parameter in the RPM parameter list, and does not error on any.
    """
    for key in REQUIRED_RPM_PARAMETERS:
        val = comm_module_fw_only.read_rpm_param(key)
        assert val is not None, f"Parameter {key} could not be read or is missing."

def test_precedence_persists_on_presence_and_absence(comm_module_with_uicc_and_fw, comm_module_fw_only):
    """
    c) Confirm parameter source precedence is correct both when UICC provides and does not provide parameters.
    """
    comm_module_with_uicc_and_fw.read_all_rpm_parameters()
    for key in uicc_with_params().rpm_params:
        val, source = None, None
        for k,v,src in comm_module_with_uicc_and_fw.get_read_log():
            if k == key:
                val, source = v, src
        assert source == "uicc", f"Expected source 'uicc' for key {key}, got {source}"

    comm_module_fw_only.read_all_rpm_parameters()
    fw_log = comm_module_fw_only.get_read_log()
    for k, v, src in fw_log:
        assert src == "firmware", f"Expected source 'firmware' for key {k}, got {src}"

def test_documented_procedure_for_audit(comm_module_with_uicc_and_fw):
    """
    d) Log/report output for every read operation, for audit/compliance evidence.
    """
    comm_module_with_uicc_and_fw.read_all_rpm_parameters()
    log = comm_module_with_uicc_and_fw.get_read_log()
    print("RPM Parameter Readout/Audit Log:")
    for record in log:
        print(f"Parameter: {record[0]}, Value: {record[1]}, Source: {record[2]}")

```
---
**Instructions:**
- Save as `tests/test_rpm_parameter_readability.py`.
- Replace mocks with your real AT command, diagnostic API, or device test harness code.
- Run with:
  ```
  pytest tests/test_rpm_parameter_readability.py
  ```
- All steps and assertions are mapped to GSMA TS.34_8.2.1_REQ_007, TS.34_8.2.4_REQ_010, and associated precedence rules. Print/log output is suitable for audit/evidence. Adjust parameter names and readout integration as needed for your module/hardware.
