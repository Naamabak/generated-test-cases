```python
# File: tests/test_rpm_reset_on_permanent_reject_causes.py

"""
Test Case for:
Requirement ID : TS.34_8.2.2_REQ_006

Requirement Summary:
The RPM SHALL wait for timer T1 (or T1 ext) and then reset the Radio Baseband Chipset when any permanent MM/GMM/EMM reject cause (see list) is received.
 - RPM reset logic is disabled if T1 is set to 0.
 - Timer SHALL not be restarted if already running.
 - EMM reject handling applies only to E-UTRAN capable chipsets.

References:
- GSMA TS.34 v8.0, Section 8.2.2, TS.34_8.2.2_REQ_006
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
- 3GPP TS 24.008, TS 24.301 (cause codes & timer behavior)
"""

import pytest
import time

# --- CONSTANTS/CONFIGURATION ---

MM_REJECT_CAUSES    = [2, 3, 6]           # #2 (IMSI Unknown in HLR), #3 (Illegal MS), #6 (Illegal ME)
GMM_REJECT_CAUSES   = [3, 6, 7, 8]        # #3 (Illegal MS), #6 (Illegal ME), #7 (GPRS Not Allowed), #8 (GPRS & Non-GPRS Not Allowed)
EMM_REJECT_CAUSES   = [3, 6, 7, 8]        # #3 (Illegal UE), #6 (Illegal ME), #7 (EPS Not Allowed), #8 (EPS & Non-EPS Not Allowed)

# --- MOCK / PLACEHOLDER IMPLEMENTATION ---

class MockRadioBasebandChipset:
    """
    Simulates a baseband chipset supporting MM/GMM/EMM reject logic, RPM timer T1, and reset/ignore logic.
    """
    def __init__(self, eutran_capable=True):
        self.eutran_capable = eutran_capable
        self.t1_value_sec = 10   # Default, can be changed per test
        self.t1_running = False
        self.t1_start_time = 0
        self.timer_type = None
        self.received_causes = []
        self.reset_issued = False
        self.event_log = []

    def set_timer(self, t1_value):
        self.t1_value_sec = t1_value

    def inject_reject_cause(self, cause_type, cause_value):
        """cause_type: 'MM', 'GMM', 'EMM'. cause_value = code as integer"""
        rec = f"{cause_type} Reject Cause #{cause_value}"
        self.received_causes.append((cause_type, cause_value))
        # Only certain causes trigger the timer/reset handling (see below)
        is_permanent = False
        if cause_type == "MM" and cause_value in MM_REJECT_CAUSES:
            is_permanent = True
        elif cause_type == "GMM" and cause_value in GMM_REJECT_CAUSES:
            is_permanent = True
        elif cause_type == "EMM" and cause_value in EMM_REJECT_CAUSES:
            is_permanent = True
        else:
            self.event_log.append(f"Ignored {rec} (not permanent or not defined trigger)")
            return

        # EMM reject handling only for E-UTRAN
        if cause_type == "EMM" and not self.eutran_capable:
            self.event_log.append(f"Ignored EMM Reject ({rec}) on non-E-UTRAN device")
            return

        # If T1 is 0, RPM trigger should be disabled
        if self.t1_value_sec == 0:
            self.event_log.append(f"T1 = 0: reset handling for {rec} is DISABLED")
            return

        # If timer is already running, do not start a new timer
        if self.t1_running:
            self.event_log.append(f"T1/T1ext timer already running, {rec} did not restart timer")
            return

        # Trigger RPM timer and record time/timer type
        self.t1_running = True
        self.t1_start_time = time.time()
        self.timer_type = "T1"  # Or "T1ext" per config/context
        self.event_log.append(f"Started {self.timer_type} ({self.t1_value_sec}s) due to {rec}")

    def elapse_time_and_check(self, secs):
        """
        Progress simulated time and perform reset if T1 expires.
        """
        if self.t1_running and (time.time() - self.t1_start_time) >= self.t1_value_sec:
            self.trigger_reset()
            self.t1_running = False
            self.timer_type = None

    def trigger_reset(self):
        """Simulate issuing a reset to the RPM-affected components."""
        self.reset_issued = True
        self.event_log.append("RPM-initiated RESET triggered as per timer expiry")

    def clear_reset(self):
        self.reset_issued = False

    def reset_timer(self):
        self.t1_running = False
        self.t1_start_time = 0
        self.timer_type = None

    def get_log(self):
        return list(self.event_log)

    def reset_log(self):
        self.event_log = []

    def is_timer_running(self):
        return self.t1_running

# --- PYTEST FIXTURE ---
@pytest.fixture(params=[True, False], ids=["eutran_capable", "non_eutran"])
def chipset(request):
    return MockRadioBasebandChipset(eutran_capable=request.param)

# --- TEST SCRIPT ---

def test_rpm_reset_on_permanent_reject_causes(chipset):
    """
    TS.34_8.2.2_REQ_006 full coverage:
    - T1 > 0: correct trigger on all listed MM/GMM/EMM causes (EMM only for EUTRAN)
    - T1 = 0: handling disabled, no timer no reset
    - Timer not restarted if already running
    - Correct log behavior for reject causes/branches
    """

    # Step 1: Set T1 to non-zero (enabled)
    chipset.set_timer(2)      # Fast expiry for test timing
    chipset.reset_log()
    for cause_list, ctype, desc in [ (MM_REJECT_CAUSES, "MM", "MM"), (GMM_REJECT_CAUSES, "GMM", "GMM"), (EMM_REJECT_CAUSES, "EMM", "EMM") ]:
        for cause in cause_list:
            # Step 2: Inject a permanent reject cause; ensure timer triggers properly
            chipset.t1_running = False
            chipset.reset_issued = False
            chipset.inject_reject_cause(ctype, cause)
            log = chipset.get_log()

            # EMM causes only on E-UTRAN
            if ctype == "EMM" and not chipset.eutran_capable:
                assert any("Ignored EMM Reject" in l for l in log), f"EMM reject should be ignored for non-EUTRAN: {log}"
                continue

            # For MM+GMM always trigger, for EMM only on EUTRAN
            timer_started = any("Started T1" in l or "Started T1ext" in l for l in log)
            assert timer_started, f"{ctype} reject cause {cause}: Timer was not started as required (log: {log})"

            # Step 3: If T1 running, next reject should NOT restart it
            chipset.inject_reject_cause(ctype, cause)
            log2 = chipset.get_log()
            assert any("already running" in l for l in log2), "T1 restart not blocked on repeated cause"
            # Step 4: Elapse time and verify reset is triggered
            time.sleep(2.1)
            chipset.elapse_time_and_check(2.1)
            assert chipset.reset_issued, "RPM Reset did not occur on timer expiry"

            # Step 5: Reset state for next cause
            chipset.clear_reset()
            chipset.reset_timer()
            chipset.reset_log()

    # Step 6: Set T1 to zero (RPM reset disabled), repeat for all causes (must not trigger timer or reset)
    chipset.set_timer(0)
    chipset.reset_log()
    for cause_list, ctype in [ (MM_REJECT_CAUSES, "MM"), (GMM_REJECT_CAUSES, "GMM"), (EMM_REJECT_CAUSES, "EMM") ]:
        for cause in cause_list:
            chipset.inject_reject_cause(ctype, cause)
            log = chipset.get_log()
            # For EMM, only care if EUTRAN
            if ctype == "EMM" and not chipset.eutran_capable:
                continue
            assert any("DISABLED" in l for l in log), f"{ctype} with T1=0: Timer/handling not properly disabled {log}"
            assert not chipset.is_timer_running(), "Timer is running when T1=0: should not be"
            assert not chipset.reset_issued, "Reset issued when T1=0: should not be"
            chipset.reset_log()
            chipset.clear_reset()

    print("All required MM/GMM/EMM permanent reject cause, timer, and reset logic verified for both T1 enabled and T1=0 conditions.")

# To test: pytest tests/test_rpm_reset_on_permanent_reject_causes.py
```
**Instructions:**

- Save as `tests/test_rpm_reset_on_permanent_reject_causes.py`.
- Replace mock timer/event/reset implementation and reject injection with integration to your actual baseband/RPM API if available.
- Run with:
  ```bash
  pytest tests/test_rpm_reset_on_permanent_reject_causes.py
  ```
- The script asserts timer handling for all listed reject causes, disables when T1=0, prevents duplicate timer instance, and logs all relevant flows in compliance with TS.34_8.2.2_REQ_006.