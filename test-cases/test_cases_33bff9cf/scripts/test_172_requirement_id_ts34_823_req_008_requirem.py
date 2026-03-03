```python
# File: tests/test_rpm_pdpa_pair_limit_f4.py

"""
Test Case for:
Requirement ID : TS.34_8.2.3_REQ_008

Requirement:
RPM SHALL allow no more than F4 PDP Context Activation/Deactivation pairs per hour to the same APN.
After the limit F4 is reached, the RPM SHALL ignore subsequent PDP Context Activation Requests to the same APN.
If F4 is set to 0, no enforcement (limit) is applied.

References:
- GSMA TS.34 v8.0, Section 8.2.3, Requirement TS.34_8.2.3_REQ_008
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf (page 48)
"""

import pytest
import time

class MockRPMF4Controller:
    """
    Simulates RPM's PDP Activation/Deactivation pair-limiting logic for the same APN.
    """
    def __init__(self):
        self.F4_per_apn = {}  # apn : F4
        self.pair_log = []    # (apn, event_type, timestamp, actioned/ignored)
        self.active_sessions = {} # apn : True if session is active (between activation and deactivation)
        self.current_time = time.time()

    def set_time(self, t):
        self.current_time = t

    def advance_time(self, seconds):
        self.current_time += seconds

    def set_f4(self, apn, f4_value):
        self.F4_per_apn[apn] = f4_value

    def _recent_pairs_in_window(self, apn):
        """
        Returns number of actioned Activation/Deactivation pairs in the previous 1 hour window.
        """
        window_start = self.current_time - 3600
        # Only "actioned" pairs count, and must BOTH contain actioned activation and actioned (following) deactivation.
        # Model as simply as possible: count pairs as (# of actioned activation events in window)
        return [
            log for log in self.pair_log
            if log[0] == apn and log[1] == 'activation' and log[2] > window_start and log[3] == "actioned"
        ]

    def pdp_activation_request(self, apn):
        """
        Simulates PDP Context Activation for APN.
        Enforces F4 activation/deactivation pair limit.
        Returns (allowed: bool, log_message: str)
        """
        f4 = self.F4_per_apn.get(apn)
        recent_pairs = self._recent_pairs_in_window(apn)

        if f4 == 0:
            # Disabled: allow any number of pairs
            allowed = True
            msg = f"F4=0 (disabled): Activation request for {apn} is actioned"
        elif len(recent_pairs) < f4:
            allowed = True
            msg = f"F4={f4}: Activation request for {apn} is actioned (pair {(len(recent_pairs) + 1)} in window)"
        else:
            allowed = False
            msg = f"F4={f4}: Activation request for {apn} is IGNORED (F4 pair limit reached for 1 hour window)"
        if allowed:
            self.active_sessions[apn] = True
        self.pair_log.append((apn, 'activation', self.current_time, "actioned" if allowed else "ignored"))
        return allowed, msg

    def pdp_deactivation_request(self, apn):
        """
        Simulates paired PDP Context Deactivation for APN.
        Only allowed if activation was previously actioned.
        """
        # Deactivation is only "actioned" if there is an active session
        allowed = self.active_sessions.get(apn, False)
        msg = f"Deactivation for {apn} is {'actioned' if allowed else 'ignored (no active session)'}"
        if allowed:
            del self.active_sessions[apn]
        self.pair_log.append((apn, 'deactivation', self.current_time, "actioned" if allowed else "ignored"))
        return allowed, msg

    def reset(self):
        self.pair_log.clear()
        self.active_sessions.clear()

    def get_log(self):
        return list(self.pair_log)

    def count_actioned_pairs_in_window(self, apn):
        return len(self._recent_pairs_in_window(apn))

    def count_ignored_activations(self, apn):
        return sum(1 for log in self.pair_log if log[0] == apn and log[1] == 'activation' and log[3] == "ignored")

# --- PYTEST FIXTURE ---

@pytest.fixture
def rpm():
    rpm = MockRPMF4Controller()
    rpm.set_time(time.time())
    yield rpm
    rpm.reset()

# ---- TEST SCRIPT ----

def test_f4_limit_applies_and_ignored_requests(rpm):
    """
    a, b: For F4 > 0, only F4 Activation/Deactivation pairs are allowed in one hour; F4+1th and later activations are ignored.
    """
    apn = "test.apn"
    F4 = 3
    rpm.set_f4(apn, F4)
    rpm.set_time(time.time())
    pair_interval = int(3600 / F4)  # Spread them equally across the hour

    # Send exactly F4 activation/deactivation pairs in window
    results = []
    for i in range(F4):
        allowed, msg1 = rpm.pdp_activation_request(apn)
        results.append(allowed)
        assert allowed, f"Pair {i+1}: Expected activation to be allowed but it was ignored. Log: {msg1}"
        _, msg2 = rpm.pdp_deactivation_request(apn)
        rpm.advance_time(pair_interval)
    # Next (F4+1th) pair should be IGNORED for activation (deactivation also ignored)
    allowed, msg3 = rpm.pdp_activation_request(apn)
    assert not allowed, f"Pair {F4+1}: Expected activation to be ignored after F4 limit. Log: {msg3}"
    _, msg4 = rpm.pdp_deactivation_request(apn)
    # Nothing should crash or break if calling deactivation with no session
    assert not rpm.active_sessions.get(apn, False)

    # Print logs for compliance
    log = rpm.get_log()
    ignores = rpm.count_ignored_activations(apn)
    print("F4 limit/actioned/ignored logs:", log)
    print(f"Number of ignored activations after F4: {ignores}")

def test_f4_window_resets_after_hour(rpm):
    """
    b: After hour boundary, limit resets, new pairs can be sent.
    """
    apn = "pairreset.apn"
    F4 = 2
    rpm.set_f4(apn, F4)
    rpm.set_time(time.time())
    # Act F4 pairs
    for i in range(F4):
        allowed, _ = rpm.pdp_activation_request(apn)
        assert allowed
        rpm.pdp_deactivation_request(apn)
        rpm.advance_time(int(3600 / F4))
    # Next should be blocked in window
    assert not rpm.pdp_activation_request(apn)[0]
    # Advance time to fall outside window
    rpm.advance_time(3601)
    # Now should be allowed again
    allowed, msg = rpm.pdp_activation_request(apn)
    assert allowed, f"Activation should be allowed after window reset: {msg}"
    print("Window reset logs:", rpm.get_log())

def test_f4_zero_disables_restriction(rpm):
    """
    c: If F4=0, RPM disables all limiting and allows any number of pairs.
    """
    apn = "disabled.apn"
    rpm.set_f4(apn, 0)
    rpm.set_time(time.time())
    for i in range(10):
        allowed, _ = rpm.pdp_activation_request(apn)
        rpm.pdp_deactivation_request(apn)
        assert allowed, "F4=0: All activation requests should be allowed (limit disabled)."
        rpm.advance_time(30)  # arbitrary
    print("No restriction with F4=0:", rpm.get_log())

def test_logs_and_counters_trace_behavior(rpm):
    """
    d: System log, counter, request/response data confirm correct handling for both F4>0 and F4=0.
    """
    apn = "combo.apn"
    # Check F4=2 first, then F4=0
    rpm.set_f4(apn, 2)
    rpm.set_time(time.time())
    act1, _ = rpm.pdp_activation_request(apn)
    rpm.pdp_deactivation_request(apn)
    act2, _ = rpm.pdp_activation_request(apn)
    rpm.pdp_deactivation_request(apn)
    act3, msg = rpm.pdp_activation_request(apn)
    assert not act3, "Third activation in window must be ignored"
    print("F4>0 log:", rpm.get_log())
    rpm.reset()
    rpm.set_f4(apn, 0)
    # Try again, now no limit
    acts = []
    for i in range(5):
        act, _ = rpm.pdp_activation_request(apn)
        rpm.pdp_deactivation_request(apn)
        acts.append(act)
    print("F4=0 log:", rpm.get_log())
    assert all(acts), "F4=0 should allow all pairs"
```