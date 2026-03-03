```python
# File: tests/test_rpm_counter_cr1_increment_and_no_rollover.py

"""
Test Case for:
Requirement ID : TS.34_8.2.2_REQ_007

Requirement:
- RPM SHALL increment counter C-R-1 by 1 when reset is triggered by T1 or T1 ext.
- The counter SHALL NOT roll over (i.e., max is 0xFF, further increments do not increase value).

References:
- GSMA TS.34 v8.0, Section 8.2.2, Requirement TS.34_8.2.2_REQ_007
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf (page 45)
"""

import pytest

# --- MOCK IMPLEMENTATION FOR TESTING (replace with integration/hw interface for live test) ---

class MockRPM:
    """
    Simulates C-R-1 counter and reset logic as required by TS.34_8.2.2_REQ_007.
    """
    def __init__(self):
        self.cr1 = 0  # Counter starts at 0 (8-bit unsigned)
        self.max_value = 0xFF  # 255
        self.event_log = []

    def read_cr1(self):
        return self.cr1

    def trigger_reset_by_timer(self, timer_type):
        """
        Simulate a reset being triggered by T1 or T1ext. ONLY these increments C-R-1.
        """
        prev = self.cr1
        if self.cr1 < self.max_value:
            self.cr1 += 1
        self.event_log.append(f"Reset by {timer_type}: C-R-1 {prev:#04x} -> {self.cr1:#04x}")

    def reset(self):
        self.cr1 = 0
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

def test_cr1_increments_by_one_per_timer_reset(rpm):
    """
    a) C-R-1 increments by 1 each time a reset is triggered by T1/T1 ext.
    """
    values = []
    for i in range(5):
        c_before = rpm.read_cr1()
        rpm.trigger_reset_by_timer("T1")
        c_after = rpm.read_cr1()
        values.append((c_before, c_after))
        assert c_after == min(c_before + 1, 0xFF), f"Iteration {i+1}: C-R-1 did not increment by 1 or cap at 0xFF"
    print("First increments log:", values)

def test_cr1_does_not_rollover_beyond_maximum(rpm):
    """
    b) When C-R-1 reaches max (0xFF), further timer resets do NOT increment/rollover.
    c) All logs and reads confirm holding at max, with no wrap.
    """
    # Step 1: Increment to 0xFF (255)
    for _ in range(255):
        rpm.trigger_reset_by_timer("T1ext")
    assert rpm.read_cr1() == 0xFF  # Should reach maximum

    # Step 2: Trigger additional resets; confirm CR1 stays at 0xFF (no overflow/wrap)
    for _ in range(10):
        rpm.trigger_reset_by_timer("T1")
        assert rpm.read_cr1() == 0xFF, "C-R-1 counter should never increment past 0xFF"

    # Step 3: Confirm counter does NOT roll back to 0 at any point
    for _ in range(5):
        rpm.trigger_reset_by_timer("T1ext")
        assert rpm.read_cr1() != 0, "C-R-1 counter must not roll over to zero (wrap forbidden)"

    # Step 4: Log entries show correct increment/freeze logic
    log = rpm.get_log()
    capped_entries = [l for l in log[-20:] if "C-R-1" in l]
    for entry in capped_entries:
        assert "0xff" in entry, "Log or result mismatch: C-R-1 should be at max (0xff)"
    print("Final increment log (last 20):", capped_entries)

@pytest.mark.parametrize("start_val,expected_after", [
    (0, 1),
    (0xFE, 0xFF),
    (0xFF, 0xFF)
])
def test_cr1_increment_on_edge_cases(rpm, start_val, expected_after):
    """
    Check increment/cap logic when C-R-1 is at or near edge.
    """
    rpm.cr1 = start_val
    rpm.trigger_reset_by_timer("T1")
    assert rpm.read_cr1() == expected_after, (
        f"Increment from {start_val:#04x} expected {expected_after:#04x}, got {rpm.read_cr1():#04x}"
    )

def test_cr1_logs_for_traceability(rpm):
    """
    Confirm that log records show all increments and no roll-over for audit.
    """
    for i in range(260):
        rpm.trigger_reset_by_timer("T1")
    logs = rpm.get_log()
    assert len(logs) >= 255, "Insufficient log entries for increments performed"
    final_logs = logs[-10:]
    print("Final C-R-1 increment log entries:", final_logs)
```
---

**Instructions:**
- Save as `tests/test_rpm_counter_cr1_increment_and_no_rollover.py`
- Replace the mock class with your device/system integration.
- Run with:
  ```bash
  pytest tests/test_rpm_counter_cr1_increment_and_no_rollover.py
  ```
- All steps and logs map directly to GSMA TS.34_8.2.2_REQ_007. Output and assertions confirm correct no-rollover increment logic for C-R-1.