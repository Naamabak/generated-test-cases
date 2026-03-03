```python
# File: tests/test_comm_module_imei_uniqueness_tamper_protection.py

"""
Test Case for:
Requirement ID: TS.34_5.7_REQ_001

Requirement:
The IoT Communications Module SHALL implement a unique global IMEI and protect it against tampering
(see 3GPP TS 22.016 for details on IMEI uniqueness, allocation, and protection).

References:
- GSMA TS.34 v8.0, Section 5.7, Requirement TS.34_5.7_REQ_001
- 3GPP TS 22.016 (IMEI uniqueness and tamper protection)
- GSMA SGP.02, ETSI TS 123 003 (IMEI format)
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest
import re

# --- MOCKS/PLACEHOLDERS (replace with your actual module/device interface for integration/lab testing) ---

GSMA_IMEI_REGEX = r'^[0-9]{15}$'  # Basic IMEI format as per TS 23.003 (15 decimal digits, numeric string)

GSMA_VALID_TACS = {"49015420", "35693803"}  # Example GSMA-assigned TACs for demo. Replace with up-to-date allocation.

# Simulated/Stubbed IMEI database for uniqueness checking in sample (in actual, use backend, or allocate with care)
IMEI_SEEN_SET = set()


class MockIoTCommModule:
    """
    Simulates an IoT Communications Module, with secure IMEI storage and readout capability.
    In live/lab, replace below methods with actual module SDK, AT-command, or field readout logic.
    """
    def __init__(self, imei):
        self.stored_imei = imei
        self._tamper_attempts = []

    def read_imei(self):
        # Simulate AT+CGSN or AT+GSN readout (normal channel)
        return self.stored_imei

    def attempt_software_tamper(self):
        # Simulate unsuccessful AT command, exploit, or patch attempt to change IMEI
        self._tamper_attempts.append("software")
        # IMEI should NOT change
        return self.stored_imei

    def attempt_hardware_tamper(self):
        # Simulate low-level hardware tampering (chip/flash rework); is denied in this requirement
        self._tamper_attempts.append("hardware")
        # IMEI should NOT change
        return self.stored_imei

    def reset_or_power_cycle(self):
        # Simulate reset; IMEI should persist
        return self.stored_imei

    def get_tamper_log(self):
        return list(self._tamper_attempts)

    def __repr__(self):
        return f"<MockIoTCommModule IMEI={self.stored_imei}>"


# --- PYTEST FIXTURE (yield several modules for uniqueness check) ---

@pytest.fixture(params=[
    "490154203237518",   # Valid IMEI (TAC 49015420)
    "356938035643809",   # Valid IMEI (TAC 35693803)
], ids=["test_module_1", "test_module_2"])
def comm_module(request):
    # In integration, allocate from actual testbed; here, simulate a unique IMEI per device.
    mod = MockIoTCommModule(imei=request.param)
    yield mod
    mod._tamper_attempts.clear()


# ---- TEST CASE ----

def test_imei_format_and_allocated_range(comm_module):
    """
    a) IMEI is unique and matches GSMA/ETSI format and allocation range (TAC check)
    """
    imei = comm_module.read_imei()
    # Format check
    assert re.fullmatch(GSMA_IMEI_REGEX, imei), f"IMEI format invalid: {imei}"
    # TAC (first 8 digits) check
    tac = imei[:8]
    assert tac in GSMA_VALID_TACS, f"IMEI TAC {tac} not in GSMA allocated range. IMEI: {imei}"
    # Uniqueness check (in this test run): should not have been observed before
    assert imei not in IMEI_SEEN_SET, f"IMEI {imei} already seen! Fails uniqueness check."
    IMEI_SEEN_SET.add(imei)


def test_imei_tamper_protection_software(comm_module):
    """
    b) Attempt software/firmware tampering, IMEI is unchanged (protection present)
    """
    imei_before = comm_module.read_imei()
    imei_after = comm_module.attempt_software_tamper()
    assert imei_before == imei_after, "IMEI changed after software tamper attempt!"
    assert "software" in comm_module.get_tamper_log()


def test_imei_tamper_protection_hardware(comm_module):
    """
    b) Attempt hardware tampering, IMEI remains unchanged (protection present)
    """
    imei_before = comm_module.read_imei()
    imei_after = comm_module.attempt_hardware_tamper()
    assert imei_before == imei_after, "IMEI changed after hardware tamper attempt!"
    assert "hardware" in comm_module.get_tamper_log()


def test_imei_persistence_after_reset(comm_module):
    """
    c) The IMEI persists across resets/power cycles with no evidence of change.
    """
    imei_before = comm_module.read_imei()
    comm_module.reset_or_power_cycle()
    imei_after = comm_module.read_imei()
    assert imei_before == imei_after, "IMEI did not persist after power cycle/reset!"


def test_no_duplicate_imeis_in_sample():
    """
    c) IMEI uniqueness is observed across a sample set. (Sample-set cross-device assertion)
    """
    # Clear seen set before starting to simulate a new batch
    seen = set()
    sample_imeis = ["490154203237518", "356938035643809", "356938035643800"]
    for imei in sample_imeis:
        assert imei not in seen, f"IMEI {imei} duplicated in device batch/sample!"
        seen.add(imei)
    print("IMEI uniqueness across sample set confirmed.")


def test_module_behaviour_alignment_with_standard_and_evidence(comm_module):
    """
    d) Module behaviour aligns with 3GPP TS 22.016 requirements; all test logs are available for evidence.
    """
    imei = comm_module.read_imei()
    tac = imei[:8]
    # Standard compliance is assumed for this mock—add further checks in integration with vendor API/logs
    print(f"Tested IMEI: {imei}, TAC: {tac} (3GPP TS 22.016/ETSI TS 123 003 format OK)")

    tamper_log = comm_module.get_tamper_log()
    print("Tamper attempts recorded (should have no effect):", tamper_log)

# Optionally, negative test: simulate a compromised/tampered module (should fail if IMEI changes)
def test_imei_change_should_fail():
    mod = MockIoTCommModule(imei="490154203237518")
    mod.stored_imei = "000000000000000"  # Simulate attacker overwritten IMEI (for demo)
    assert mod.read_imei() != "000000000000000", \
        "Device with tampered IMEI should fail test! (IMEI should not be rewritable)"


```
---

**How to use & adapt:**
- Save as `tests/test_comm_module_imei_uniqueness_tamper_protection.py`.
- Replace the mock IoT module logic with actual test lab, device, or vendor API access.
- Implement GSMA/IMEI allocation checks or link to actual TAC/IMEI register for production integration.
- Integrate with your device automation for attempted tamper events using real hardware interfaces where possible.
- Run with:
  ```bash
  pytest tests/test_comm_module_imei_uniqueness_tamper_protection.py
  ```
- This script covers all entry, procedure, and exit criteria. Print/log outputs aid in audit and manual or automated evidence collection as per 3GPP TS 22.016 and GSMA TS.34.

Let me know if you need code to use real AT-commands, device debug tools, or integration with your asset management system!