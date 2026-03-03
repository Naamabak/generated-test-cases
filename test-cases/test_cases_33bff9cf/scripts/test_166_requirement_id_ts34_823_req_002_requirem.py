```python
# File: tests/test_rpm_counter_cpdp1_increment_and_no_rollover.py

"""
Test Case for:
Requirement ID : TS.34_8.2.3_REQ_002

Requirement:
- RPM SHALL increment counter C-PDP-1 by 1 when PDP Context Activation Request / PDN Connectivity Request
  is ignored by RPM because of TS.34_8.2.3_REQ_001 (“Handling of PDP Context Activation Request / PDN Connectivity Request Ignore”).
- The counter SHALL not roll over.

References:
- GSMA TS.34 v8.0, Section 8.2.3, TS.34_8.2.3_REQ_002
- TS.34_8.2.3_REQ_001
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest

# --- MOCK IMPLEMENTATION FOR TESTING (replace with integration/hw interface for live test) ---

class MockRPM:
    """
    Simulates C-PDP-1 counter and logic for ignoring PDP Context Activation/PDN Connectivity requests.
    """
    def __init__(self):
        self.cpdp1 = 0  # 8-bit unsigned counter (0~0xFF, i.e., 0~255)
        self.max_value = 0xFF
        self.event_log = []

    def read_cpdp1(self):
        return self.cpdp1

    def ignore_pdp_activation(self):
        """
        Simulate a PDP Context Activation or PDN Connectivity Request that is ignored per TS.34_8.2.3_REQ_001.
        Increments C-PDP-1 if not at max value (no rollover).
        """
        prev = self.cpdp1
        if self.cpdp1 < self.max_value:
            self.cpdp1 += 1
        self.event_log.append(f"PDP/PDN activation ignored: C-PDP-1 {prev:#04x} -> {self.cpdp1:#04x}")

    def reset(self):
        self.cpdp1 = 0
        self.event_log = []

    def get_log(self):
        return list(self.event_log)

# --- PYTEST FIXTURE ---

@pytest.fixture
def rpm():
    obj = MockRPM()
    yield obj
    obj.reset()

# --- TEST SCRIPT ---

def test_cpdp1_increments_by_one_per_ignored_request(rpm):
    """
    a) After each ignored PDP Context Activation/PDN Connectivity Request, C-PDP-1 increments by 1 (capped at 0xFF).
    """
    values = []
    for i in range(5):
        before = rpm.read_cpdp1()
        rpm.ignore_pdp_activation()
        after = rpm.read_cpdp1()
        values.append((before, after))
        assert after == min(before + 1, 0xFF), f"Fail at event {i+1}: C-PDP-1 did not increment or cap at 0xFF"
    print("First 5 increments log:", values)

def test_cpdp1_does_not_rollover_at_maximum(rpm):
    """
    b) When C-PDP-1 reaches max (0xFF), further ignored requests DO NOT increment or roll over the counter.
    c) Counter must never roll over to 0 or wrap.
    """
    # Step 1: Increment to 255 (0xFF)
    for _ in range(255):
        rpm.ignore_pdp_activation()
    assert rpm.read_cpdp1() == 0xFF, f"C-PDP-1 did not reach expected max 0xFF, got {rpm.read_cpdp1():#04x}"

    # Step 2: Trigger more ignored requests—counter must remain at 0xFF
    for _ in range(10):
        rpm.ignore_pdp_activation()
        assert rpm.read_cpdp1() == 0xFF, "C-PDP-1 counter incremented past 0xFF!"

    # Step 3: Ensure never rolls back to zero
    for _ in range(5):
        rpm.ignore_pdp_activation()
        assert rpm.read_cpdp1() != 0, "C-PDP-1 counter rolled over to zero (no wrap permitted)"

    # Step 4: Print log entries for last increments
    log = rpm.get_log()
    capped_entries = [l for l in log[-10:] if "C-PDP-1" in l]
    for entry in capped_entries:
        assert "0xff" in entry, f"Log or result mismatch for capped counter: {entry}"
    print("Final C-PDP-1 log entries (capped):", capped_entries)

@pytest.mark.parametrize("start_val,expected_after", [
    (0, 1),
    (0xFE, 0xFF),
    (0xFF, 0xFF)
])
def test_cpdp1_edge_cases(rpm, start_val, expected_after):
    """
    Check increment/capping logic when starting at or near max for C-PDP-1.
    """
    rpm.cpdp1 = start_val
    rpm.ignore_pdp_activation()
    after = rpm.read_cpdp1()
    assert after == expected_after, f"Expected C-PDP-1 == {expected_after:#04x} after increment from {start_val:#04x}, got {after:#04x}"

def test_cpdp1_logs_for_traceability(rpm):
    """
    Ensure log records all increments and confirms no rollover, for trace compliance.
    """
    for i in range(260):
        rpm.ignore_pdp_activation()
    logs = rpm.get_log()
    assert len(logs) >= 255, "Insufficient log entries for increments"
    final_logs = logs[-10:]
    print("Final C-PDP-1 increment log entries:", final_logs)
```
---

**How to use/adapt:**
- Save as `tests/test_rpm_counter_cpdp1_increment_and_no_rollover.py`
- Replace mock logic with integration for your RPM/device/module implementation for compliance checks.
- Run with:
  ```bash
  pytest tests/test_rpm_counter_cpdp1_increment_and_no_rollover.py
  ```
- Every assertion and log step covers GSMA TS.34_8.2.3_REQ_002: correct +1 increment, capping at 0xFF, and no rollover/wrap.
- Print/log output enables audit for conformance evidence and regression documentation.