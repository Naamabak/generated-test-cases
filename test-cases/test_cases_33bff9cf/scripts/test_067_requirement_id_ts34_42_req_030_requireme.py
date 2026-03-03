```python
# File: tests/test_esl_operator_policy_enforcement.py

"""
Test Case for:
Requirement ID: TS.34_4.2_REQ_030

Requirement:
If the IoT Embedded Service Layer identifies the IoT Service communicates over a Mobile IoT RAT, it SHOULD ensure all application data sent and received complies with the Mobile Network Operator’s data volume and communication frequency policies (e.g., monthly allowance, daily message cap, per-message payload size limit).

References:
- GSMA TS.34 v8.0, Section 4.2, Requirement TS.34_4.2_REQ_030
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest

# ---- MOCK/PLACEHOLDER CLASSES ----
# In a real system, these would be replaced by actual device/ESL APIs.

class MockOperatorPolicy:
    """Represents the Network Operator policy (data and frequency caps)."""
    def __init__(self, monthly_bytes, max_msgs_per_day, days_per_month=30):
        self.monthly_bytes = monthly_bytes
        self.max_msgs_per_day = max_msgs_per_day
        self.days_per_month = days_per_month
        self.day_bytes = monthly_bytes // days_per_month
        self.max_payload_bytes = self.day_bytes // max_msgs_per_day

class MockESLApp:
    """
    Simulates the ESL with policy enforcement.
    - Tracks per-day and per-month stats
    - Applies operator policy to all outgoing/incoming messages
    """
    def __init__(self, operator_policy):
        self.policy = operator_policy
        self.current_day = 1
        self.current_month = 1
        self.day_sent = 0
        self.month_sent = 0
        self.day_msgs = 0
        self.log = []
        self.period_log = []
        self.reset_window()

    def reset_window(self):
        self.day_sent = 0
        self.day_msgs = 0

    def increment_day(self):
        self.current_day += 1
        self.period_log.append(list(self.log))
        self.log = []
        self.reset_window()

    def increment_month(self):
        self.current_month += 1
        self.month_sent = 0

    def send_data(self, payload: bytes):
        # Check message limit (per day)
        if self.day_msgs >= self.policy.max_msgs_per_day:
            self.log.append({"event": "blocked_msg_limit", "size": len(payload)})
            return False
        # Check total data limit (per day and per month)
        if self.day_sent + len(payload) > self.policy.day_bytes:
            self.log.append({"event": "blocked_day_data_limit", "size": len(payload)})
            return False
        if self.month_sent + len(payload) > self.policy.monthly_bytes:
            self.log.append({"event": "blocked_month_data_limit", "size": len(payload)})
            return False
        # Check payload size limit
        if len(payload) > self.policy.max_payload_bytes:
            self.log.append({"event": "blocked_payload_limit", "size": len(payload)})
            return False
        # All checks passed, send allowed
        self.day_msgs += 1
        self.day_sent += len(payload)
        self.month_sent += len(payload)
        self.log.append({"event": "sent", "size": len(payload)})
        return True

    def get_log(self):
        return self.log[:]

    def reset_all(self):
        self.current_day = 1
        self.current_month = 1
        self.month_sent = 0
        self.reset_window()
        self.log = []

    def get_period_log(self):
        # All logs from previous periods
        return self.period_log[:]

# ---- PYTEST FIXTURES ----

@pytest.fixture
def operator_policy():
    # Example: 300 MB / month, 10 messages/day, 30 days/month
    return MockOperatorPolicy(
        monthly_bytes=300 * 1024 * 1024,  # 300MB
        max_msgs_per_day=10,
        days_per_month=30
    )

@pytest.fixture
def esl_app(operator_policy):
    return MockESLApp(operator_policy)

# ---- TEST CASES ----

def test_esl_operator_policy_limits(enforce_multiple_days=True, operator_policy=None, esl_app=None):
    """TS.34_4.2_REQ_030: Test compliance with Operator policy (daily/monthly limits and payload size cap)."""
    if operator_policy is None or esl_app is None:
        # Pytest injection for standalone run
        import inspect
        frame = inspect.currentframe().f_back
        operator_policy = frame.f_globals["operator_policy"]()
        esl_app = frame.f_globals["esl_app"](operator_policy)
    # a) The number of messages sent/received per day does not exceed the operator’s daily maximum.
    # b) The total data sent/received per month does not exceed the monthly allowance.
    # c) Each message payload adheres to the maximum allowed size as determined by the policy formula.

    payload_size = operator_policy.max_payload_bytes
    msg_per_day = operator_policy.max_msgs_per_day

    # Day 1: Send exactly up to the cap, all messages at max payload size
    for _ in range(msg_per_day):
        payload = bytes([0xff] * payload_size)
        assert esl_app.send_data(payload), "Valid message within limit should succeed"
    # Next message should be blocked on count:
    assert not esl_app.send_data(bytes([0x01] * payload_size))
    # Try an oversized payload (should be blocked by payload limit)
    assert not esl_app.send_data(bytes([0x01] * (payload_size + 1)))
    log = esl_app.get_log()
    assert any(e["event"] == "blocked_msg_limit" for e in log)
    assert any(e["event"] == "blocked_payload_limit" for e in log)

    # Exceed daily data limit with a smaller payload if possible
    esl_app.reset_window()
    esl_app.day_sent = esl_app.policy.day_bytes - 10
    assert not esl_app.send_data(bytes([0x02] * 20))
    log = esl_app.get_log()
    assert any(e["event"] == "blocked_day_data_limit" for e in log)

    # Exceed monthly data limit: simulate near end of month data
    esl_app.month_sent = esl_app.policy.monthly_bytes - (payload_size-1)
    esl_app.reset_window()
    assert esl_app.send_data(bytes([0x03] * (payload_size-1)))
    assert not esl_app.send_data(bytes([0x04] * 10))
    log = esl_app.get_log()
    assert any(e["event"] == "blocked_month_data_limit" for e in log)

    # d) Excess or over-limit data/messages must be blocked, delayed, or queued (here: blocked)
    # e) Logs record all enforcement events
    blocked = [e["event"] for e in esl_app.get_log() if "blocked" in e["event"]]
    assert blocked, "Blocking events should be recorded in the logs"

    # f) Repeat for at least 2 periods (days)
    if enforce_multiple_days:
        esl_app.increment_day()
        for _ in range(msg_per_day):
            payload = bytes([0x10] * payload_size)
            assert esl_app.send_data(payload)
        assert not esl_app.send_data(bytes([0x11] * payload_size))
        log2 = esl_app.get_log()
        assert any(e["event"] == "blocked_msg_limit" for e in log2)
        assert esl_app.day_msgs == msg_per_day
        assert esl_app.day_sent == payload_size * msg_per_day

        # Simulate another period for completeness
        esl_app.increment_day()
        for _ in range(msg_per_day):
            assert esl_app.send_data(bytes([0x03] * payload_size))
        # Should again hit the limit
        assert not esl_app.send_data(bytes([0x04] * payload_size))

    print("Logs per day: ", esl_app.get_period_log() + [esl_app.get_log()])

# ---- Wrapper for Pytest Standard ----

def test_esl_operator_policy_caps_all(operator_policy, esl_app):
    test_esl_operator_policy_limits(True, operator_policy, esl_app)

```

---

**How to Use:**

- Save as `tests/test_esl_operator_policy_enforcement.py`
- Replace `MockESLApp` with your real Embedded Service Layer's send/data control APIs for system/lab/integration; use real logging and monitoring where possible.
- All key exit/pass/fail criteria (policy enforcement, blocking, logging, per-period repeatability) are explicitly covered.
- Run with:
  ```bash
  pytest tests/test_esl_operator_policy_enforcement.py
  ```
- Print statements give traceability of enforcement results and logs for manual/automated review.

Let me know if you want this further adapted to interface with your device test APIs, actual logs, or operator policy data!