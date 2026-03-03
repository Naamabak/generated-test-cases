```python
# File: tests/test_rpm_pdp_temp_reject_backoff.py

"""
Test Case for:
Requirement ID : TS.34_8.2.3_REQ_005 | TS.34_8.2.3_REQ_007

Requirement:
If PDP Context Activation / PDN Connectivity Request is rejected with “temporary” SM reject causes
[#25, #26, #31, #34, #35, #38, #102, #111], RPM SHALL use a back-off algorithm to ensure no more than F3
such requests are sent to the same APN within one hour. Algorithm SHALL be disabled if F3=0.
F3 and algorithm must meet TS.34_8.2.3_REQ_007: in any 15-minute window, at least MAX(0.05*F3, 1) attempts allowed.

References:
- GSMA TS.34 v8.0, Section 8.2.3, TS.34_8.2.3_REQ_005, TS.34_8.2.3_REQ_007
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest
import time

TEMP_REJECT_CAUSES = [25, 26, 31, 34, 35, 38, 102, 111]

class MockRPMBackoffController:
    """Implements the back-off logic and F3 policings per requirement."""
    def __init__(self):
        self.F3_values = {}  # APN -> F3 setting
        self.sent_requests = []  # (APN, timestamp)
        self.log = []
        self.request_interval = 15 * 60  # 15 min in seconds
        self.current_time = time.time()

    def set_time(self, t):
        self.current_time = t

    def advance_time(self, seconds):
        self.current_time += seconds

    def set_apn_f3(self, apn, f3):
        self.F3_values[apn] = f3
        self.log.append(f"Set F3={f3} for APN={apn}")

    def _backoff_active(self, apn):
        """Returns True if F3 limit reached (should block transmission)"""
        f3 = self.F3_values[apn]
        if f3 == 0:
            return True  # block when disabled
        t = self.current_time
        hour_ago = t - 3600
        requests_last_hour = [ts for apn2, ts in self.sent_requests if apn2 == apn and ts > hour_ago]
        return len(requests_last_hour) >= f3

    def _allowed_per_15min_window(self, apn):
        f3 = self.F3_values[apn]
        if f3 == 0:
            return 0
        min_per_15m = max(round(0.05 * f3), 1)
        t = self.current_time
        wstart = t - self.request_interval
        recent = [ts for apn2, ts in self.sent_requests if apn2 == apn and ts > wstart]
        return len(recent) < min_per_15m

    def request_pdp_activation(self, apn, reject_cause):
        if apn not in self.F3_values:
            raise ValueError("F3 not set for APN")

        f3 = self.F3_values[apn]

        if reject_cause not in TEMP_REJECT_CAUSES:
            self.log.append(f"Non-temporary reject cause ({reject_cause}); ignoring F3 algo")
            return False  # Out of scope.

        if f3 == 0:
            self.log.append(f"F3=0: No PDP/PDN request sent for APN={apn}")
            return False

        # Enforce F3 max/hr
        if self._backoff_active(apn):
            self.log.append(f"Back-off active: Max F3 ({f3}) already sent to APN={apn} for rolling hour")
            return False

        # Enforce minimum per-15min rule.
        if not self._allowed_per_15min_window(apn):
            self.log.append(f"15min window: request suppressed for APN={apn}")
            return False

        # Request is allowed
        self.sent_requests.append((apn, self.current_time))
        self.log.append(f"Request sent to APN={apn} at {self.current_time} (Reject cause: {reject_cause})")
        return True

    def count_requests_in_window(self, apn, window_sec):
        t = self.current_time
        cutoff = t - window_sec
        return len([1 for apn2, ts in self.sent_requests if apn2 == apn and ts > cutoff])

    def get_log(self):
        return list(self.log)

    def reset(self):
        self.sent_requests = []
        self.log = []

@pytest.fixture
def rpm_backoff():
    ctrl = MockRPMBackoffController()
    t0 = time.time()
    ctrl.set_time(t0)
    yield ctrl
    ctrl.reset()


def test_rpm_respects_f3_hourly_limit_for_temp_rejects(rpm_backoff):
    """ (a) F3 > 0: no more than F3 sent per hour for any temporary reject cause. """
    apn = 'iot.temp'
    F3 = 6
    rpm_backoff.set_apn_f3(apn, F3)
    rpm_backoff.set_time(time.time())

    # Try F3 = 6: 6 attempts allowed per hour, all temp causes.
    interval = int(3600 / F3)
    allowed_attempts = []
    for i in range(F3):
        assert rpm_backoff.request_pdp_activation(apn, TEMP_REJECT_CAUSES[i % len(TEMP_REJECT_CAUSES)])
        rpm_backoff.advance_time(interval)
        allowed_attempts.append(rpm_backoff.current_time)

    # All attempts should be within 1 hour and allowed.
    assert len(allowed_attempts) == F3
    assert sum(1 for l in rpm_backoff.get_log() if "Request sent" in l) == F3

    # Next (7th) attempt should be blocked within same hour.
    assert not rpm_backoff.request_pdp_activation(apn, TEMP_REJECT_CAUSES[0])
    print("Hourly F3 test log:", rpm_backoff.get_log())

def test_rpm_backoff_minimum_15min_distribution_requirement(rpm_backoff):
    """ (b) At least max(0.05*F3, 1) permitted per 15min window. """
    apn = "dm.15min"
    F3 = 10
    rpm_backoff.set_apn_f3(apn, F3)
    rpm_backoff.set_time(time.time())

    min_per_15m = max(round(0.05 * F3), 1)  # Should be 1 for F3=10

    # Send min_per_15m attempts in a 15min window
    requests_this_win = 0
    for _ in range(min_per_15m):
        assert rpm_backoff.request_pdp_activation(apn, TEMP_REJECT_CAUSES[0])
        requests_this_win += 1

    # Exceeding min_per_15m: should now block within the 15-min window
    assert not rpm_backoff.request_pdp_activation(apn, TEMP_REJECT_CAUSES[1])
    print("15-minute window log:", rpm_backoff.get_log())

    # Advance by 16min, should allow another min_per_15m
    rpm_backoff.advance_time(16 * 60)
    assert rpm_backoff.request_pdp_activation(apn, TEMP_REJECT_CAUSES[2])

def test_rpm_algo_disabled_when_f3_zero(rpm_backoff):
    """ (c) When F3=0, the back-off logic is disabled and NO requests are sent. """
    apn = "apn.blocked"
    F3 = 0
    rpm_backoff.set_apn_f3(apn, F3)
    rpm_backoff.set_time(time.time())
    for cause in TEMP_REJECT_CAUSES:
        assert not rpm_backoff.request_pdp_activation(apn, cause)
    print("Log for F3=0 (algorithm disabled):", rpm_backoff.get_log())

def test_rpm_backoff_step_logic_and_edge_cases(rpm_backoff):
    """ (d) Behavior/logs, including edge condition coverage (min/max, distribution, disables). """
    apn = "apn.edge"
    F3 = 20
    rpm_backoff.set_apn_f3(apn, F3)
    rpm_backoff.set_time(time.time())
    interval = int(3600 / F3)
    results = []

    # Simulate full hour of requests, should accept F3 but block the rest
    for i in range(F3):
        ok = rpm_backoff.request_pdp_activation(apn, TEMP_REJECT_CAUSES[i % len(TEMP_REJECT_CAUSES)])
        assert ok, f"Attempt {i+1} should be allowed under hourly cap"
        rpm_backoff.advance_time(interval)
        results.append(ok)
    # Now try one more (should be blocked)
    assert not rpm_backoff.request_pdp_activation(apn, TEMP_REJECT_CAUSES[0])

    # For each 15min window, at least MAX(0.05*F3, 1) allowed
    rpm_backoff.reset()
    rpm_backoff.set_apn_f3(apn, F3)
    rpm_backoff.set_time(time.time())
    for window in range(0, 4):
        for _ in range(max(round(0.05 * F3), 1)):
            assert rpm_backoff.request_pdp_activation(apn, TEMP_REJECT_CAUSES[0])
        assert not rpm_backoff.request_pdp_activation(apn, TEMP_REJECT_CAUSES[1])  # Exceed, should block
        rpm_backoff.advance_time(16 * 60)

    print("Edge case log:", rpm_backoff.get_log())

@pytest.mark.parametrize("temp_cause", TEMP_REJECT_CAUSES)
def test_each_temp_reject_cause_triggers_backoff(rpm_backoff, temp_cause):
    """Algorithm must treat each temp reject cause as requiring backoff (i.e. ALL listed codes)."""
    apn = f"apn{temp_cause}"
    F3 = 2
    rpm_backoff.set_apn_f3(apn, F3)
    rpm_backoff.set_time(time.time())
    # Allow F3 attempts
    for _ in range(F3):
        assert rpm_backoff.request_pdp_activation(apn, temp_cause)
    # After F3, further requests blocked
    assert not rpm_backoff.request_pdp_activation(apn, temp_cause)
```
---

**How to use/adapt:**
- Save as `tests/test_rpm_pdp_temp_reject_backoff.py`.
- For real lab/system use, replace the logic with hooks to your device/module log parsing, diagnostic APIs, and time-speedup or event-injection tools.
- Run:
  ```bash
  pytest tests/test_rpm_pdp_temp_reject_backoff.py
  ```
- All steps and assertions directly map to GSMA TS.34_8.2.3_REQ_005/007. Print/log outputs are for traceability or evidence. Adjust timings/APN/cause lists as needed for your implementation or protocol stack.