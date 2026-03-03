```python
# File: tests/test_comm_module_mnc_length_support.py

"""
Test Case for:
Requirement ID : TS.34_5.9_REQ_002

Requirement:
The IoT Communications Module SHALL support 2-digit and 3-digit Mobile Network Codes (MNCs) in IMSIs.

References:
- GSMA TS.34 v8.0, Section 5.9, TS.34_5.9_REQ_002
- 3GPP TS 23.003: Numbering, addressing and identification (IMSI format)
- ITU-T E.212: The international identification plan for public networks and subscriptions
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest
import re

# ----------- MOCKS / PLACEHOLDER CLASSES ----------- 
# In real tests, replace with integration to your actual SIM/UICC handlers, device/module API, and network/testbed logging.

IMSI_REGEX_2DIGIT_MNC = r"^\d{5}\d{10}$"  # MCC 3 + 2 digit MNC + MSIN
IMSI_REGEX_3DIGIT_MNC = r"^\d{6}\d{9}$"   # MCC 3 + 3 digit MNC + MSIN
VALID_2DIGIT_MNC = "01"  # Example: 2-digit MNC (use real MNCs from SIM profiles)
VALID_3DIGIT_MNC = "123" # Example: 3-digit MNC

class MockUICC:
    """Simulates a UICC/SIM with a programmable IMSI."""
    def __init__(self, mcc, mnc, msin: str):
        self.imsi = mcc + mnc + msin
        self.mnc_length = len(mnc)

class MockIoTCommModule:
    """
    Simulates an IoT Communications Module with registration/IMSI parsing support.
    Replace with actual module API for a real device-under-test.
    """
    def __init__(self):
        self.attached = False
        self.last_imsi = None
        self.log = []

    def insert_sim_and_power_on(self, sim: MockUICC):
        """Insert (U)SIM and boot/connect to network using IMSI."""
        self.last_imsi = sim.imsi
        self.log.append(f"SIM inserted with IMSI: {sim.imsi}")
        # Simulate parsing logic (real system would verify/parse against 3GPP/ITU standards)
        if (sim.mnc_length == 2 and re.fullmatch(IMSI_REGEX_2DIGIT_MNC, sim.imsi)) \
           or (sim.mnc_length == 3 and re.fullmatch(IMSI_REGEX_3DIGIT_MNC, sim.imsi)):
            # Simulate network registration/authentication success
            self.attached = True
            self.log.append(f"Registration/authentication successful with IMSI {sim.imsi} (MNC len={sim.mnc_length})")
        else:
            self.attached = False
            self.log.append("Registration failed: IMSI not in correct format or unsupported MNC length.")

    def power_off(self):
        self.attached = False

    def get_log(self):
        return list(self.log)

    def reset(self):
        self.attached = False
        self.last_imsi = None
        self.log.clear()

# ----------- PYTEST FIXTURE -----------

@pytest.fixture
def iot_module():
    mod = MockIoTCommModule()
    yield mod
    mod.reset()

# ----------- TEST SCRIPT -----------

def test_comm_module_supports_both_2_and_3_digit_mnc(iot_module):
    """
    TS.34_5.9_REQ_002:
    Verify that the module accepts and processes IMSIs with both 2-digit and 3-digit MNCs.
    Registration and authentication must succeed in both cases and logs confirm correct IMSI parsing.
    """

    mcc = "310"  # Example MCC (USA)
    msin_2 = "1234567890"   # 10 digits for 2-digit MNC IMSI (15-digit total)
    msin_3 = "567890123"    # 9 digits for 3-digit MNC IMSI (15-digit total)

    # Step 1: Insert SIM with 2-digit MNC IMSI
    sim_2digit = MockUICC(mcc, VALID_2DIGIT_MNC, msin_2)
    iot_module.insert_sim_and_power_on(sim_2digit)
    assert iot_module.attached, "Module failed to register with 2-digit MNC IMSI"
    log = iot_module.get_log()
    assert any("successful" in entry for entry in log), "2-digit MNC registration not logged as successful"
    assert len(iot_module.last_imsi) == 15 and sim_2digit.mnc_length == 2, "IMSI/MNC length verification failed for 2-digit case"

    # Step 2: Power down
    iot_module.power_off()

    # Step 3: Insert SIM with 3-digit MNC IMSI
    sim_3digit = MockUICC(mcc, VALID_3DIGIT_MNC, msin_3)
    iot_module.insert_sim_and_power_on(sim_3digit)
    assert iot_module.attached, "Module failed to register with 3-digit MNC IMSI"
    log = iot_module.get_log()
    assert any("successful" in entry for entry in log), "3-digit MNC registration not logged as successful"
    assert len(iot_module.last_imsi) == 15 and sim_3digit.mnc_length == 3, "IMSI/MNC length verification failed for 3-digit case"

    # Step 4: Confirm logs for both
    print("Test logs for both 2-digit and 3-digit MNC IMSIs:")
    for entry in iot_module.get_log():
        print(entry)

@pytest.mark.parametrize("mnc,msin,should_pass", [
    ("01",     "1234567890",    True),   # Valid 2-digit (15 digits)
    ("123",    "567890123",     True),   # Valid 3-digit (15 digits)
    ("1234",   "56789012",      False),  # Invalid: MNC too long (16-digit IMSI)
    ("0",      "12345678901",   False),  # Invalid: MNC too short (14-digit IMSI)
])
def test_comm_module_imsi_parsing_compliance(iot_module, mnc, msin, should_pass):
    """Test module IMSI parsing logic for various MNC lengths and formats."""
    mcc = "310"
    sim = MockUICC(mcc, mnc, msin)
    iot_module.insert_sim_and_power_on(sim)
    if should_pass:
        assert iot_module.attached, f"Should register for IMSI with MNC={mnc} (IMSI: {sim.imsi})"
    else:
        assert not iot_module.attached, f"Should reject invalid IMSI (MNC={mnc}, IMSI: {sim.imsi})"

    print("IMSI:", sim.imsi, "Attached:", iot_module.attached, "| Log:", iot_module.get_log())

```
---

**Usage:**
- Save as `tests/test_comm_module_mnc_length_support.py`
- Replace mocks/stubs with actual SIM/UICC handling, module APIs, and network integration as appropriate.
- Run with:
  ```bash
  pytest tests/test_comm_module_mnc_length_support.py
  ```
- The script verifies both 2-digit and 3-digit MNC IMSI support, registration/handling logic, and negative test cases.
- All major requirements and GSMA/3GPP formats for IMSI/MNC are mapped to code and assertion checks.
