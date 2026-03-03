```python
# File: tests/test_rpm_cr1_decrement_by_lr2.py

"""
Test Case for:
Requirement ID : TS.34_8.2.4_REQ_005

Requirement:
If LR-2 is NOT 0, C-R-1 SHALL be decremented by 1 every LR-2 hours if C-R-1 is greater than 0.
C-R-1 SHALL never be negative. C-R-1 SHALL not be decremented if LR-2 is 0.

References:
- GSMA TS.34 v8.0, Section 8.2.4, Requirement TS.34_8.2.4_REQ_005
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest

class MockCR1CounterManager:
    """
    Simulates C-R-1 counter and LR-2 timer logic for test and demonstration.
    In production, connect this to your actual device/system/firmware implementation!
    """
    def __init__(self):
        self.cr1 = 0                  # C-R-1 counter (must be >= 0)
        self.lr2_hours = 0            # LR-2 parameter (hours, int or float)
        self.current_time_hrs = 0     # Simulated time in hours
        self.last_decrement_time = 0  # Time (in hours) when last decrement occurred
        self.log = []

    def set_cr1(self, value):
        """Set the C-R-1 counter to a specific value >= 0"""
        assert value >= 0, "C-R-1 cannot be set negative"
        self.cr1 = value
        self.log.append(f"Set C-R-1 = {value}")

    def set_lr2(self, value):
        """Set LR-2 parameter (decrement time interval in hours, may be 0)"""
        assert value >= 0, "LR-2 must be >= 0"
        self.lr2_hours = value
        self.log.append(f"Set LR-2 = {value} hours")
        self.last_decrement_time = self.current_time_hrs  # Reset timer for new LR-2

    def tick(self, advance_hours):
        """
        Advances time and checks if it's time to decrement C-R-1.
        Simulates time-advancing in test (advance_hours may be integer or float).
        """
        start_time = self.current_time_hrs
        end_time = self.current_time_hrs + advance_hours
        # Simulate hour-by-hour (or with step = LR-2), for clarity
        while self.current_time_hrs + self.lr2_hours <= end_time:
            # Only decrement if LR-2 > 0 and C-R-1 > 0
            if self.lr2_hours > 0 and self.cr1 > 0:
                self.current_time_hrs += self.lr2_hours
                self.cr1 -= 1
                self.cr1 = max(self.cr1, 0)
                self.log.append(f"At {self.current_time_hrs:.2f} hr: C-R-1 decremented to {self.cr1} (LR-2 interval)")
            else:
                # Time advances if no decrement needed/possible
                self.current_time_hrs += self.lr2_hours if self.lr2_hours > 0 else (end_time - self.current_time_hrs)
        # Jump to requested end time if not exactly aligned
        self.current_time_hrs = end_time

    def get_cr1(self):
        return self.cr1

    def get_log(self):
        return list(self.log)

    def reset(self):
        self.cr1 = 0
        self.lr2_hours = 0
        self.current_time_hrs = 0
        self.last_decrement_time = 0
        self.log.clear()


@pytest.fixture
def cr1_manager():
    mgr = MockCR1CounterManager()
    yield mgr
    mgr.reset()


def test_cr1_decrement_per_lr2_interval_and_no_negative(cr1_manager):
    """
    - With LR-2 > 0, C-R-1 is decremented by 1 every LR-2 hours if C-R-1 > 0.
    - C-R-1 never becomes negative.
    - LR-2 = 0 disables decrement regardless of time.
    """
    # Step 1: Set LR-2 to 2 hours, C-R-1 to 3
    cr1_manager.set_lr2(2)
    cr1_manager.set_cr1(3)

    assert cr1_manager.get_cr1() == 3
    log = [f"t={cr1_manager.current_time_hrs}: {cr1_manager.get_cr1()}"]

    # Step 2: Advance (observe) for each LR-2 interval (2 hours) and check decrement
    cr1_manager.tick(2)  # after 2 hours
    assert cr1_manager.get_cr1() == 2
    log.append(f"t={cr1_manager.current_time_hrs}: {cr1_manager.get_cr1()}")

    cr1_manager.tick(2)  # after 4 hours total
    assert cr1_manager.get_cr1() == 1
    log.append(f"t={cr1_manager.current_time_hrs}: {cr1_manager.get_cr1()}")

    cr1_manager.tick(2)  # after 6 hours total
    assert cr1_manager.get_cr1() == 0
    log.append(f"t={cr1_manager.current_time_hrs}: {cr1_manager.get_cr1()}")

    # Step 3: Now, even if more LR-2 intervals pass, C-R-1 must remain at 0 (no negative)
    for _ in range(3):
        cr1_manager.tick(2)
        assert cr1_manager.get_cr1() == 0
        log.append(f"t={cr1_manager.current_time_hrs}: {cr1_manager.get_cr1()}")

    # Step 4: Set LR-2 to zero, set C-R-1 to non-zero, tick forward, confirm no decrement
    cr1_manager.set_lr2(0)
    cr1_manager.set_cr1(5)
    before = cr1_manager.get_cr1()
    cr1_manager.tick(6)
    after = cr1_manager.get_cr1()
    assert after == before, "C-R-1 should not decrement when LR-2 is 0"

    log.append(f"LR-2 set to 0, C-R-1 initial: {before}, after 6h: {after}")

    # Print all logs for audit
    print("C-R-1 counter/history log:")
    for entry in log:
        print(entry)
    # Also output the detailed decrement log actions
    for entry in cr1_manager.get_log():
        print(entry)


@pytest.mark.parametrize("initial_cr1, lr2, hours, expected", [
    (2, 1, 2, 0),    # 2 decrements, should hit zero
    (5, 2, 4, 3),    # 2 intervals (4 hours): 5->3
    (3, 3, 6, 1),    # 2 intervals: 3->1
    (1, 1, 4, 0),    # Hit zero and stay zero
])
def test_various_cr1_decrement_cases(cr1_manager, initial_cr1, lr2, hours, expected):
    cr1_manager.set_lr2(lr2)
    cr1_manager.set_cr1(initial_cr1)
    cr1_manager.tick(hours)
    assert cr1_manager.get_cr1() == expected, f"Expected C-R-1={expected}; got {cr1_manager.get_cr1()} for initial_c={initial_cr1}, LR-2={lr2}, {hours}h"

def test_cr1_never_decrements_below_zero_negative_check(cr1_manager):
    cr1_manager.set_cr1(1)
    cr1_manager.set_lr2(2)
    # Go past zero
    cr1_manager.tick(10)
    assert cr1_manager.get_cr1() == 0, "C-R-1 must never be negative!"
    cr1_manager.tick(10)
    assert cr1_manager.get_cr1() == 0, "C-R-1 must not decrement below zero even after long time with LR-2 > 0"

def test_no_decrement_when_lr2_zero_for_long_period(cr1_manager):
    cr1_manager.set_lr2(0)
    cr1_manager.set_cr1(10)
    cr1_manager.tick(100)
    assert cr1_manager.get_cr1() == 10, "C-R-1 must not be decremented if LR-2 is 0"
    print("C-R-1 correctly does not decrement for LR-2=0 over extended time.")

```
---

**How to use:**
- Save as `tests/test_rpm_cr1_decrement_by_lr2.py`.
- Replace the mock class with your real module/device interface for counter/timer access in integration/lab.
- Run with:
  ```
  pytest tests/test_rpm_cr1_decrement_by_lr2.py
  ```

The script covers:
- Every decrement logic scenario (LR-2 > 0, LR-2 = 0, no negative, step-by-step).
- Multiple edge and negative test cases.
- Print/log steps are for audit and result review. Adjust or plug into your automation as appropriate for device/production use.