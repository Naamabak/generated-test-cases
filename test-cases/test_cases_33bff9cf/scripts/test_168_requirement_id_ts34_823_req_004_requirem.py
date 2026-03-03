```python
# File: tests/test_rpm_counter_cpdp2_increment_and_no_rollover.py

"""
Test Case for:
Requirement ID : TS.34_8.2.3_REQ_004

Requirement:
- RPM SHALL increment counter C-PDP-2 by 1 each time a PDP Context Activation/PDN Connectivity Request is ignored due to a permanent SM Reject Cause (TS.34_8.2.3_REQ_003).
- The counter SHALL NOT roll over (e.g., max at 0xFF, further increments have no effect).

References:
- GSMA TS.34 v8.0, Section 8.2.3, TS.34_8.2.3_REQ_004/003
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest

# --- MOCK CLASS IMPLEMENTATION (replace with your real device/firmware/system interface for integration) ---

class MockRPM_C_PDP_2:
    """
    Simulates RPM counter C-PDP-2 and "Permanent" SM Reject Cause handling.
    """
    PERMANENT_SM_REJECT_CAUSES = {8, 27, 28, 29, 30, 32, 33}
    MAX_C_PDP_2 = 0xFF  # 255

    def __init__(self, initial_value=0):
        self.cpdp2 = initial_value
        self.log = []

    def read_counter(self):
        return self.cpdp2

    def trigger_permanent_sm_reject(self, cause):
        """
        Simulate a network response with a Permanent SM Reject cause for a PDP Context Activation/PDN Connectivity Request.
        Only increments the counter if cause is permanent as defined.
        """
        prev_value = self.cpdp2
        if cause in self.PERMANENT_SM_REJECT_CAUSES:
            if self.cpdp2 < self.MAX_C_PDP_2:
                self.cpdp2 += 1
            # If already at max, no roll-over/overflow
            self.log.append(
                f"Permanent SM Reject Cause #{cause}: C-PDP-2 {prev_value:#04x} -> {self.cpdp2:#04x} (incremented)"
                if self.cpdp2 != prev_value
                else f"Permanent SM Reject Cause #{cause}: C-PDP-2 stays at {self.cpdp2:#04x} (max, no roll-over)"
            )
        else:
            self.log.append(f"Non-permanent SM Reject Cause #{cause}: no change to C-PDP-2 ({self.cpdp2:#04x})")

    def set_counter(self, value):
        """Directly set the counter to simulate initial state or max value."""
        self.cpdp2 = value

    def get_log(self):
        return list(self.log)

    def reset(self):
        self.cpdp2 = 0
        self.log = []

# --- PYTEST FIXTURE ---

@pytest.fixture
def rpm_cpdp2():
    rpm = MockRPM_C_PDP_2()
    yield rpm
    rpm.reset()

# --- TEST SCRIPT ---

def test_cpdp2_increments_by_one_for_permanent_reject(rpm_cpdp2):
    """
    a) Each time a "Permanent" SM Reject cause is encountered, C-PDP-2 increments by 1.
    """
    initial = rpm_cpdp2.read_counter()
    for cause in [8, 27, 28]:
        prev = rpm_cpdp2.read_counter()
        rpm_cpdp2.trigger_permanent_sm_reject(cause)
        curr = rpm_cpdp2.read_counter()
        assert curr == prev + 1, f"C-PDP-2 did not increment by 1 for Permanent SM Reject Cause #{cause}"
    print("C-PDP-2 increments for Permanent SM Rejects:", rpm_cpdp2.get_log())

def test_cpdp2_no_increment_for_non_permanent_reject(rpm_cpdp2):
    """
    No increment should occur for non-permanent SM reject causes.
    """
    prev = rpm_cpdp2.read_counter()
    rpm_cpdp2.trigger_permanent_sm_reject(21)  # e.g., non-permanent cause
    curr = rpm_cpdp2.read_counter()
    assert curr == prev, "C-PDP-2 incremented for non-permanent SM Reject cause!"
    print("C-PDP-2 did not increment for non-permanent cause:", rpm_cpdp2.get_log()[-1])

def test_cpdp2_cap_and_no_rollover_at_max(rpm_cpdp2):
    """
    b) When C-PDP-2 reaches 0xFF, further increments do not roll over or increase the counter.
    """
    # Step 1: Set to 0xFF
    rpm_cpdp2.set_counter(0xFF)
    assert rpm_cpdp2.read_counter() == 0xFF

    # Step 2: Attempt multiple increments for permanent SM reject causes
    for _ in range(5):
        rpm_cpdp2.trigger_permanent_sm_reject(30)
        assert rpm_cpdp2.read_counter() == 0xFF, "C-PDP-2 rolled over or incremented past 0xFF!"
    print("C-PDP-2 saturation at 0xFF log:", rpm_cpdp2.get_log()[-5:])

def test_cpdp2_multiple_increments_and_cap(rpm_cpdp2):
    """
    c) Test multiple increments from initial state and show log for audit.
    """
    log_before = []
    for _ in range(10):
        rpm_cpdp2.trigger_permanent_sm_reject(29)
        log_before.append(rpm_cpdp2.read_counter())
    print("10 increments (should increment up to 10):", log_before)
    rpm_cpdp2.set_counter(0xFF)
    for _ in range(3):
        rpm_cpdp2.trigger_permanent_sm_reject(28)
    print(f"After cap at 0xFF, extra increments give: {rpm_cpdp2.get_log()[-3:]}")

@pytest.mark.parametrize("cause", [8, 27, 28, 29, 30, 32, 33])
def test_cpdp2_increments_for_each_permanent_cause(rpm_cpdp2, cause):
    """
    Confirm all listed permanent SM reject causes increment C-PDP-2.
    """
    prev = rpm_cpdp2.read_counter()
    rpm_cpdp2.trigger_permanent_sm_reject(cause)
    curr = rpm_cpdp2.read_counter()
    assert curr == prev + 1, f"C-PDP-2 did not increment for cause {cause}"
    print(f"Cause {cause}: C-PDP-2 is now {curr}")

```
---

**How to use/adapt:**
- Save as `tests/test_rpm_counter_cpdp2_increment_and_no_rollover.py`
- Replace the mock logic with your device/module system integration if available.
- Run with:
  ```bash
  pytest tests/test_rpm_counter_cpdp2_increment_and_no_rollover.py
  ```
- The test script makes assertions for counter increments, non-rollover, and includes logs for evidence as per TS.34_8.2.3_REQ_004.
- Adjust/reuse the set of permanent SM reject causes and RPM interface functions as per your product/module implementation.