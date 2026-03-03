```python
# File: tests/test_rpm_t1_timer_stop_on_ue_reset.py

"""
Test Case for:
Requirement ID : TS.34_8.2.2_REQ_008

Requirement:
UE internal timer related to T1 (T1 ext) SHALL be stopped when UE is reset (hardware or software).
RPM SHALL not reset the Radio Baseband Chipset if it is already reset by the IoT Device Application or IoT Communications Module.

References:
- GSMA TS.34 v8.0, Section 8.2.2, TS.34_8.2.2_REQ_008
- TS.34_8.2.2_REQ_006 (T1 timer event context)
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest
import time

# --- MOCK IMPLEMENTATION (replace or adapt for integration/system testing) ---

class MockRadioBasebandChipset:
    """
    Simulates the Radio Baseband Chipset, T1/T1ext timer, and reset events.
    """
    def __init__(self):
        self.t1_running = False
        self.t1_start_time = None
        self.t1_value = 60  # seconds (example)
        self.rpm_awaiting_reset = False
        self.chipset_reset_count = 0
        self.log = []
        self._now = time.time()  # allow manual control if needed

    def trigger_permanent_reject_event(self):
        # Simulates reception of a permanent reject event, which should start T1 timer
        if not self.t1_running:
            self.t1_running = True
            self.t1_start_time = self._now
            self.rpm_awaiting_reset = True
            self.log.append("T1 timer started due to permanent reject event.")
        else:
            self.log.append("T1 timer already running, not restarted.")

    def advance_time(self, seconds):
        # Advances internal "now" (simulate in fast tests)
        self._now += seconds

    def check_timer(self):
        # Polling-style check. If timer expired, perform RPM-triggered reset unless already externally reset.
        if self.t1_running:
            elapsed = self._now - self.t1_start_time
            if elapsed >= self.t1_value:
                if self.rpm_awaiting_reset:
                    self.issue_rpm_reset()
                else:
                    self.log.append("T1 expired but chipset was already reset externally, no redundant RPM reset.")
                self.t1_running = False  # Stop timer

    def hardware_reset(self):
        """Simulates power-cycle or physical button reset."""
        self.stop_and_clear_t1("hardware")
        self.chipset_reset_count += 1
        self.log.append("CHIPSET hardware-reset externally by UE.")

    def software_reset(self):
        """Simulates software reset via app/module."""
        self.stop_and_clear_t1("software")
        self.chipset_reset_count += 1
        self.log.append("CHIPSET software-reset externally by UE.")

    def stop_and_clear_t1(self, reason):
        """Stops T1, clears RPM reset pending flag (called on UE external reset)."""
        if self.t1_running:
            self.log.append(f"External {reason} reset: T1 timer stopped and cleared.")
        self.t1_running = False
        self.t1_start_time = None
        self.rpm_awaiting_reset = False

    def issue_rpm_reset(self):
        """RPM triggers a chipset reset if timer expires and not already externally reset."""
        self.log.append("RPM issued chipset reset due to T1 timeout!")
        self.chipset_reset_count += 1
        self.rpm_awaiting_reset = False

    def reset_state(self):
        self.__init__()

    def get_log(self):
        return list(self.log)

    def get_chipset_reset_count(self):
        return self.chipset_reset_count

    def is_timer_running(self):
        return self.t1_running

# -- PYTEST FIXTURE --

@pytest.fixture
def chipset():
    chip = MockRadioBasebandChipset()
    yield chip
    chip.reset_state()

# -- TEST SCRIPT --

def test_t1_timer_stops_on_hardware_reset(chipset):
    """
    Requirement TS.34_8.2.2_REQ_008:
    - T1 (or T1ext) is immediately stopped on hardware reset,
    - No redundant RPM-initiated reset occurs after an external (hardware) reset,
    - Timer does not run after HW reset,
    - Logs confirm correct sequence.
    """
    # Step 1: Start T1 timer with a permanent reject event
    chipset.trigger_permanent_reject_event()
    assert chipset.is_timer_running()
    assert chipset.rpm_awaiting_reset

    # Step 2: Before T1 expires, perform hardware reset (power-cycle)
    chipset.advance_time(10)
    chipset.hardware_reset()

    # Step 3: Confirm that the timer stopped and no RPM reset followed
    assert not chipset.is_timer_running()
    # Even after enough time passes, no RPM reset should occur
    chipset.advance_time(70)
    chipset.check_timer()
    # Only one reset event (the external HW reset), not duplicated by the RPM
    assert chipset.get_chipset_reset_count() == 1
    log = chipset.get_log()
    assert any("hardware-reset externally" in l for l in log)
    assert any("T1 timer stopped" in l for l in log)
    assert not any("RPM issued chipset reset" in l for l in log), "RPM should not trigger 2nd reset after HW reset."
    print("Hardware Reset Log:", log)

def test_t1_timer_stops_on_software_reset(chipset):
    """
    - T1 (or T1ext) is immediately stopped on software reset,
    - No redundant RPM-initiated reset occurs after software reset,
    - Logs and reset count confirm only one reset takes place.
    """
    chipset.trigger_permanent_reject_event()
    chipset.advance_time(5)
    chipset.software_reset()
    assert not chipset.is_timer_running()
    chipset.advance_time(70)
    chipset.check_timer()
    assert chipset.get_chipset_reset_count() == 1
    log = chipset.get_log()
    assert any("software-reset externally" in l for l in log)
    assert any("T1 timer stopped" in l for l in log)
    assert not any("RPM issued chipset reset" in l for l in log), "RPM should not trigger double-reset after SW reset."
    print("Software Reset Log:", log)

def test_no_double_reset_and_timer_stopped_both_cases(chipset):
    """
    - For both HW and SW reset, repeat across several cycles to confirm
      timer is always stopped and no duplicate RPM reset can ever occur.
    """
    resets = []
    for mode in ("hardware", "software"):
        for _ in range(2):
            chipset.trigger_permanent_reject_event()
            chipset.advance_time(5)
            if mode == "hardware":
                chipset.hardware_reset()
            else:
                chipset.software_reset()
            chipset.advance_time(65)  # move past T1 expiry
            chipset.check_timer()
            resets.append(chipset.get_chipset_reset_count())
            assert not chipset.is_timer_running()
            assert chipset.get_chipset_reset_count() == 1
            # Reset for next cycle
            chipset.reset_state()
    print("Cycles run, each time only one reset, timer stopped, never double.")

def test_rpm_reset_occurs_if_no_external_reset(chipset):
    """
    Negative control: If timer expires and no external reset happened,
    then and only then should RPM trigger a reset.
    """
    chipset.trigger_permanent_reject_event()
    chipset.advance_time(70)
    chipset.check_timer()
    assert chipset.get_chipset_reset_count() == 1
    log = chipset.get_log()
    assert any("RPM issued chipset reset" in l for l in log)
    print("RPM reset log (no external reset):", log)
```
---

**Usage/Adaptation Notes:**
- Save as `tests/test_rpm_t1_timer_stop_on_ue_reset.py`.
- Replace `MockRadioBasebandChipset` with actual device/module interface for timer/check/reset observation.
- Run with:
  ```bash
  pytest tests/test_rpm_t1_timer_stop_on_ue_reset.py
  ```
- All assertions and logs correspond to TS.34_8.2.2_REQ_008 pass/fail, including timer stop, non-duplication, and log evidence.