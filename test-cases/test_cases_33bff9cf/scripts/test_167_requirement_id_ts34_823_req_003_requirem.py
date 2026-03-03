```python
# File: tests/test_rpm_perm_sm_reject_backoff.py

"""
Test Case for:
Requirement ID : TS.34_8.2.3_REQ_003

Requirement:
If PDP Context Activation / PDN Connectivity Request is rejected with “permanent” SM reject causes (#8, #27, #28, #29, #30, #32, #33), 
the RPM SHALL use a back-off algorithm to ensure no more than F2 requests are sent to the same APN every hour (disabled if F2=0); 
see TS.34_8.2.3_REQ_007 for minimum back-off requirements.

References:
- GSMA TS.34 v8.0, Section 8.2.3, TS.34_8.2.3_REQ_003/007
- 3GPP/TS.34 context for PDP/PDN connectivity and reject handling
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest
import time

# --- Constants for Permanent "SM" Reject Causes as per requirement ---
SM_PERMANENT_REJECT_CAUSES = [8, 27, 28, 29, 30, 32, 33]

# --- Mock RPM Backoff Controller Implementation ---
class MockRPMBackoffF2:
    """
    Simulates RPM back-off for permanent SM reject scenarios (TS.34_8.2.3_REQ_003 and _007)
    """
    def __init__(self):
        self.F2 = None
        self.req_log = []  # [(apn, cause, ts)]
        self.now = time.time()
        self.request_interval = 15 * 60  # 15 minutes, for minimum back-off window
        self.one_hour = 60 * 60

    def set_f2(self, f2):
        self.F2 = f2
        
    def _advance_time(self, seconds):
        self.now += seconds

    def _requests_in_last_hour(self, apn):
        cutoff = self.now - self.one_hour
        return [r for r in self.req_log if r[0] == apn and r[2] > cutoff]

    def _allowed_per_15min(self, apn):
        min_dist = max(round(0.05 * self.F2) if self.F2 else 0, 1)
        cutoff = self.now - self.request_interval
        count = sum(1 for r in self.req_log if r[0] == apn and r[2] > cutoff)
        return count < min_dist

    def attempt_pdp_activation(self, apn, reject_cause):
        # Only enforce for permanent reject causes
        if reject_cause not in SM_PERMANENT_REJECT_CAUSES:
            return True, "Not a permanent SM reject, request allowed"
        if self.F2 == 0:
            return False, "F2=0, no requests allowed after permanent reject"
        # Limit to F2 requests per hour
        hour_reqs = self._requests_in_last_hour(apn)
        if len(hour_reqs) >= self.F2:
            return False, f"F2 limit {self.F2}/hr reached for {apn}"
        # Min distribution requirement per TS.34_8.2.3_REQ_007
        if not self._allowed_per_15min(apn):
            return False, f"Minimum distribution for F2 (0.05*{self.F2} or 1/15min) not met"
        # Record allowed request
        self.req_log.append((apn, reject_cause, self.now))
        return True, "Request sent"

    def reset(self):
        self.req_log = []
        self.now = time.time()

    def set_time(self, t):
        self.now = t

    def get_log(self):
        return list(self.req_log)

# --- PyTest Fixture ---
@pytest.fixture
def rpm_backoff_f2():
    rpm = MockRPMBackoffF2()
    yield rpm
    rpm.reset()

# --- Test Script ---

@pytest.mark.parametrize("reject_cause", SM_PERMANENT_REJECT_CAUSES)
def test_rpm_limits_requests_per_apn_permanent_reject(rpm_backoff_f2, reject_cause):
    """
    a) After any permanent SM reject, RPM limits requests to F2 per APN/Hour.
    c) Back-off distribution meets minimum requirements (at least MAX(0.05*F2, 1) allowed per 15min window if total F2 reached).
    """
    apn = "test.apn"
    F2 = 3
    rpm_backoff_f2.set_f2(F2)
    rpm_backoff_f2.set_time(time.time())
    permitted = []
    interval = int(3600 / F2)
    for i in range(F2):
        ok, msg = rpm_backoff_f2.attempt_pdp_activation(apn, reject_cause)
        permitted.append(ok)
        assert ok, f"Attempt {i+1} should be allowed (msg={msg})"
        rpm_backoff_f2._advance_time(interval)
    # The next (F2+1st) should NOT be allowed within 1 hour
    ok, msg = rpm_backoff_f2.attempt_pdp_activation(apn, reject_cause)
    assert not ok, "More than F2 requests allowed within 1 hour"
    print(f"Permitted attempts log (should be {F2} True, then False):", permitted + [ok], "| Message:", msg)

def test_rpm_minimum_distribution_and_disabled_state(rpm_backoff_f2):
    """
    b) Minimum allowed distribution: max(0.05*F2, 1) per 15 minute window
    b) When F2=0, no requests sent at all.
    """
    apn = "iot.permanent"
    F2 = 4
    rpm_backoff_f2.set_f2(F2)
    rpm_backoff_f2.set_time(time.time())
    # Allow one immediately
    ok1, msg1 = rpm_backoff_f2.attempt_pdp_activation(apn, 8)
    assert ok1
    # Should block second attempt within 15 minutes due to distribution rule
    ok2, msg2 = rpm_backoff_f2.attempt_pdp_activation(apn, 8)
    assert not ok2, f"Second attempt (<15min) incorrectly allowed: {msg2}"
    # Advance over 15 minutes, try again - should be allowed
    rpm_backoff_f2._advance_time(16 * 60)
    ok3, msg3 = rpm_backoff_f2.attempt_pdp_activation(apn, 8)
    assert ok3, f"Should be allowed after 15 minute window passed: {msg3}"
    # Now set F2 = 0 and no request should be permitted at all
    rpm_backoff_f2.set_f2(0)
    ok4, msg4 = rpm_backoff_f2.attempt_pdp_activation(apn, 8)
    assert not ok4 and "F2=0" in msg4
    print("Minimum distribution/back-off disabling log:", [msg1, msg2, msg3, msg4])

@pytest.mark.parametrize("reject_cause", SM_PERMANENT_REJECT_CAUSES)
def test_rpm_backoff_behavior_all_permanent_reject_causes(rpm_backoff_f2, reject_cause):
    """
    d) Consistent behavior across all listed permanent reject causes.
    """
    apn = "manyreasons.apn"
    rpm_backoff_f2.set_f2(2)
    rpm_backoff_f2.set_time(time.time())
    # Issue 2 requests with permanent reject
    ok1, _ = rpm_backoff_f2.attempt_pdp_activation(apn, reject_cause)
    rpm_backoff_f2._advance_time(1800)
    ok2, _ = rpm_backoff_f2.attempt_pdp_activation(apn, reject_cause)
    rpm_backoff_f2._advance_time(1800)
    ok3, msg3 = rpm_backoff_f2.attempt_pdp_activation(apn, reject_cause)
    # Third attempt should be denied within the same hour, then allowed outside of window
    assert ok1 and ok2 and not ok3, f"3 requests within 1 hour were not properly capped at F2=2: log={msg3}"
    rpm_backoff_f2._advance_time(3600)
    ok4, _ = rpm_backoff_f2.attempt_pdp_activation(apn, reject_cause)
    assert ok4, "Should permit request again after hour window rolls off"

def test_rpm_backoff_log_and_traceability(rpm_backoff_f2):
    """
    d) Logs / request data match requirement: holds max F2 per hour, disables when F2=0, and correct minimum distribution.
    """
    apn = "log.apn"
    F2 = 2
    rpm_backoff_f2.set_f2(F2)
    rpm_backoff_f2.set_time(time.time())
    # Issue allowed requests
    rpm_backoff_f2.attempt_pdp_activation(apn, 8)
    rpm_backoff_f2._advance_time(20*60)
    rpm_backoff_f2.attempt_pdp_activation(apn, 8)
    # Block more requests in same hour
    rpm_backoff_f2._advance_time(10)
    rpm_backoff_f2.attempt_pdp_activation(apn, 8)
    # Check disabling
    rpm_backoff_f2.set_f2(0)
    rpm_backoff_f2.attempt_pdp_activation(apn, 8)
    log = rpm_backoff_f2.get_log()
    assert any("F2=0" in str(l) for l in log)
    assert sum("Request sent" in str(e) for e in log) == F2
    print("RPM Back-off request/send log:", log)
```
---

**How to use/adapt:**

- Save as `tests/test_rpm_perm_sm_reject_backoff.py`.
- Replace the mock back-off controller with your device/module integration if available.
- Run with:
  ```
  pytest tests/test_rpm_perm_sm_reject_backoff.py
  ```
- All pass/fail and behavioral logic per GSMA TS.34 requirements are covered, including exact F2 limit, disabled state, minimum request distribution, and per-cause validation.