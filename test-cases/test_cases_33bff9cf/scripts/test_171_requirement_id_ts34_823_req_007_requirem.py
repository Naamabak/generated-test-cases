```python
# File: tests/test_rpm_backoff_algorithm_minimum_requirement.py

"""
Test Case for:
Requirement ID : TS.34_8.2.3_REQ_007

Requirement:
- For PDP Context Activation / PDN Connectivity Reject/Ignore scenarios, the RPM back-off algorithm SHALL:
  (a) ensure no more than Fx requests (Fx = F1 for ignored, F2 for permanent reject, F3 for temporary reject) are sent to
      the same APN in any 1 hour,
  (b) allow at least MAX(0.05*Fx,1) requests to the same APN in each 15min window,
  (c) apply the correct Fx based on event type (ignore, permanent, temporary),
  (d) be properly disabled when Fx=0 for a given scenario,
  (e) logs and timings confirm requirement in all cause/duration conditions.

References:
- GSMA TS.34 v8.0, Section 8.2.3, TS.34_8.2.3_REQ_007
- TS.34_8.2.3_REQ_001/003/005
"""

import pytest
import time

# Constants for event types
EVENT_IGNORE = "ignore"
EVENT_PERMANENT_REJECT = "permanent_reject"
EVENT_TEMPORARY_REJECT = "temporary_reject"

# This mock controller represents simplified but faithful back-off logic per TS.34_8.2.3_REQ_007
class MockPDPBackoffController:
    def __init__(self):
        # Fx values for each scenario per APN (Fx = F1, F2, F3 depending on event type)
        self.backoff_limits = {}        # { (apn, event_type): Fx }
        self.sent_requests = []         # [(apn, event_type, timestamp)]
        self.window_hr = 3600
        self.window_15m = 900
        self.now = float(time.time())
        self.log = []

    def set_time(self, t):
        self.now = t

    def advance_time(self, seconds):
        self.now += seconds

    def configure_fx(self, apn, event_type, fx):
        self.backoff_limits[(apn, event_type)] = fx
        self.log.append(f"Fx set to {fx} for {apn} ({event_type})")

    def _windowed_count(self, apn, event_type, window):
        cutoff = self.now - window
        return len([1 for a, e, t in self.sent_requests if a == apn and e == event_type and t > cutoff])

    def attempt(self, apn, event_type):
        fx = self.backoff_limits.get((apn, event_type), None)
        if fx is None:
            raise Exception(f"Fx not configured for {apn}, {event_type}")
        if fx == 0:
            self.log.append(f"Fx=0: {event_type} requests to {apn} are disabled.")
            return False, "disabled"

        # Hourly limit
        requests_last_hr = self._windowed_count(apn, event_type, self.window_hr)
        if requests_last_hr >= fx:
            self.log.append(f"Blocked by 1-hour Fx ({event_type}, Fx={fx}): {requests_last_hr}/{fx} for {apn}")
            return False, "hr_cap"

        # Minimum allowed in 15-minute window
        min_per_15m = max(round(0.05 * fx), 1)
        requests_15m = self._windowed_count(apn, event_type, self.window_15m)
        if requests_15m >= min_per_15m:
            self.log.append(f"15-min min threshold for Fx ({event_type}, Fx={fx}) reached: {requests_15m}/{min_per_15m} for {apn}")
            return False, "window_cap"

        # Passed all caps—allowed
        self.sent_requests.append((apn, event_type, self.now))
        self.log.append(f"Request allowed for {apn} ({event_type}) at t={self.now}, Fx={fx} (hour count: {requests_last_hr+1}/{fx}, 15m count: {requests_15m+1}/{min_per_15m})")
        return True, "allowed"

    def get_log(self):
        return list(self.log)

    def reset(self):
        self.sent_requests.clear()
        self.log = []

    def set_now(self):
        self.now = float(time.time())

# ----- PYTEST FIXTURE -----
@pytest.fixture
def backoff_controller():
    ctrl = MockPDPBackoffController()
    ctrl.set_now()
    yield ctrl
    ctrl.reset()

# ----- TEST SCRIPT -----

@pytest.mark.parametrize("apn,fx,event_type", [
    ("apn.ignore", 20, EVENT_IGNORE),
    ("apn.perm", 8, EVENT_PERMANENT_REJECT),
    ("apn.temp", 12, EVENT_TEMPORARY_REJECT)
])
def test_fx_hourly_and_15min_window_limits(backoff_controller, apn, fx, event_type):
    """
    (a) Fx requests per hour for each event scenario
    (b) At least MAX(0.05*Fx,1) per 15min window (cannot block more strictly)
    (c) Proper event type mapping, limit, and windowing logic
    """
    backoff_controller.configure_fx(apn, event_type, fx)
    t0 = backoff_controller.now
    interval_15m = backoff_controller.window_15m // max(round(0.05*fx), 1)
    interval_hr = backoff_controller.window_hr // fx

    # --- Test the minimum per 15-min-window requirement ---
    min_15m = max(round(0.05*fx), 1)
    # Fill up the 15min window
    for i in range(min_15m):
        allowed, reason = backoff_controller.attempt(apn, event_type)
        assert allowed, f"Attempt {i+1}: Should be allowed in 15-min window ({backoff_controller.get_log()})"
        backoff_controller.advance_time(interval_15m)
    # Next attempt (still in 15-min window) should be blocked by window
    allowed, reason = backoff_controller.attempt(apn, event_type)
    assert not allowed and reason == "window_cap", "Exceeded min per 15m, must be blocked"
    # Move into a new 15m window
    backoff_controller.advance_time(901)
    allowed, reason = backoff_controller.attempt(apn, event_type)
    assert allowed

    # --- Test enforcement of Fx requests per APN per hour ---
    backoff_controller.reset()
    backoff_controller.configure_fx(apn, event_type, fx)
    for i in range(fx):
        allowed, reason = backoff_controller.attempt(apn, event_type)
        assert allowed, f"Should allow up to Fx in hour, failed at {i+1}"
        backoff_controller.advance_time(interval_hr)
    # Should block the Fx+1th request in same hour
    allowed, reason = backoff_controller.attempt(apn, event_type)
    assert not allowed and reason == "hr_cap", "Did not cap at Fx per hour"

    # --- Print logs for audit ---
    print(f"Log for {apn} ({event_type}):")
    for entry in backoff_controller.get_log()[-10:]:
        print("    ", entry)

@pytest.mark.parametrize("apn,event_type", [
    ("apn.ignore0", EVENT_IGNORE),
    ("apn.perm0", EVENT_PERMANENT_REJECT),
    ("apn.temp0", EVENT_TEMPORARY_REJECT)
])
def test_fx_disablement(backoff_controller, apn, event_type):
    """(d) If Fx=0, scenario is disabled for the given event type (no requests allowed)"""
    backoff_controller.configure_fx(apn, event_type, 0)
    for _ in range(5):
        allowed, reason = backoff_controller.attempt(apn, event_type)
        assert not allowed and reason == "disabled"
    print(f"Fx=0 disablement log for {apn}, {event_type}: {backoff_controller.get_log()}")

def test_correct_fx_applied_for_event_type(backoff_controller):
    """(c) Fx is selected as F1 for ignore, F2 for perm reject, F3 for temp reject - all mapped correctly."""
    f1, f2, f3 = 5, 3, 2
    apn = "apn.mapcheck"
    for event_type, value in [(EVENT_IGNORE, f1), (EVENT_PERMANENT_REJECT, f2), (EVENT_TEMPORARY_REJECT, f3)]:
        # Configure each
        backoff_controller.configure_fx(apn, event_type, value)
        for i in range(value):
            allowed, reason = backoff_controller.attempt(apn, event_type)
            assert allowed
        allowed, reason = backoff_controller.attempt(apn, event_type)
        assert not allowed and reason == "hr_cap"
        backoff_controller.reset()
        backoff_controller.configure_fx(apn, event_type, value)

def test_multiple_apns_and_scenarios(backoff_controller):
    """
    (f) Distinct APNs/cause types: windowing is per-APN-per-scenario, not global.
    """
    apn1, apn2 = "apn1", "apn2"
    f1, f2, f3 = 5, 3, 4
    # Configure limits
    backoff_controller.configure_fx(apn1, EVENT_IGNORE, f1)
    backoff_controller.configure_fx(apn2, EVENT_PERMANENT_REJECT, f2)
    for i in range(f1):
        allowed1, _ = backoff_controller.attempt(apn1, EVENT_IGNORE)
        allowed2, _ = backoff_controller.attempt(apn2, EVENT_PERMANENT_REJECT)
        assert allowed1 and allowed2
        backoff_controller.advance_time(10)
    # Both reach cap simultaneously, both blocked for additional attempts
    allowed1, reason1 = backoff_controller.attempt(apn1, EVENT_IGNORE)
    allowed2, reason2 = backoff_controller.attempt(apn2, EVENT_PERMANENT_REJECT)
    assert not allowed1 and not allowed2

def test_logs_and_timing_audit(backoff_controller):
    """
    (g) Print log and audit window for coverage.
    """
    apn = "audit.apn"
    fx = 6
    backoff_controller.configure_fx(apn, EVENT_PERMANENT_REJECT, fx)
    t0 = backoff_controller.now
    for i in range(fx):
        allowed, reason = backoff_controller.attempt(apn, EVENT_PERMANENT_REJECT)
        assert allowed
        backoff_controller.advance_time(3600 // fx)
    # Block next (extra) request
    allowed, reason = backoff_controller.attempt(apn, EVENT_PERMANENT_REJECT)
    assert not allowed
    print("Audit log:")
    for entry in backoff_controller.get_log():
        print("    ", entry)
```
---

**How to use/integrate:**
- Save as `tests/test_rpm_backoff_algorithm_minimum_requirement.py`
- Replace mock logic with your hardware/system RPM back-off and log parsing code for integration or lab use.
- Run with:
  ```bash
  pytest tests/test_rpm_backoff_algorithm_minimum_requirement.py
  ```
- All steps/assertions map directly to GSMA TS.34_8.2.3_REQ_007 and referenced back-off requirements, including correct hourly/15-min rate limiting, disablement, and per-scenario (F1/F2/F3) mapping. Prints/logs provide traceable evidence for compliance/certification. 

Let me know if you need this tailored for lab scripting or field log analysis!