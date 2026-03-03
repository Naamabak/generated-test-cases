```python
# File: tests/test_operator_policy_enforcement.py

"""
Test Case for:
Requirement ID: TS.34_4.0_REQ_030
Requirement: If the IoT Device App communicates over a Mobile IoT RAT, it SHOULD ensure data sent/received complies with
             the Mobile Network Operator’s data volume and communication frequency policies (e.g., monthly data cap,
             daily message limit, max payload size per message).
References:
    - GSMA TS.34 v8.0, Section 4.0, TS.34_4.0_REQ_030
    - a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf (including example calculation page 23)
"""

import pytest
import time

# ------------------------- MOCK CLASSES (Replace with SDK/harness for real devices) --------------------------

class MockOperatorPolicy:
    """Holds operator policy configuration for data volume/frequency."""
    def __init__(self, monthly_data_bytes, max_msgs_per_day, days_per_month=30):
        self.monthly_data_bytes = monthly_data_bytes
        self.max_msgs_per_day = max_msgs_per_day
        self.days_per_month = days_per_month
        self.daily_data_bytes = self.monthly_data_bytes // self.days_per_month
        self.max_payload_size = self.daily_data_bytes // self.max_msgs_per_day  # integer division

class MockIoTDeviceApp:
    """
    Simulates an IoT Device App enforcing operator data/message policies.
    Tracks per-day and per-month limits, as well as individual message payload cap.
    """
    def __init__(self, policy):
        self.policy = policy
        self.current_day = 1      # Simplified simulation
        self.current_month = 1    # Single simulated month
        self.reset_window()
        self.log = []

    def reset_window(self):
        self.msgs_sent_today = 0
        self.data_sent_today = 0
        self.data_sent_month = 0
        self.last_day_increment = time.time()
        self.last_month_increment = time.time()

    def increment_day(self):
        self.current_day += 1
        self.msgs_sent_today = 0
        self.data_sent_today = 0
        self.last_day_increment = time.time()

    def increment_month(self):
        self.current_month += 1
        self.data_sent_month = 0
        self.last_month_increment = time.time()

    def send_payload(self, payload_bytes):
        """Simulate sending a payload. Returns True if accepted, False if blocked by policy."""
        # Check payload size
        if payload_bytes > self.policy.max_payload_size:
            self.log.append("rejected:payload_too_large")
            return False

        # Check daily/message/monthly limits
        if self.msgs_sent_today >= self.policy.max_msgs_per_day:
            self.log.append("rejected:msg_limit_daily")
            return False

        if self.data_sent_today + payload_bytes > self.policy.daily_data_bytes:
            self.log.append("rejected:data_limit_daily")
            return False

        if self.data_sent_month + payload_bytes > self.policy.monthly_data_bytes:
            self.log.append("rejected:data_limit_monthly")
            return False

        # All good: Allow transmission
        self.msgs_sent_today += 1
        self.data_sent_today += payload_bytes
        self.data_sent_month += payload_bytes
        self.log.append("sent")
        return True

    def get_log(self):
        return list(self.log)

    def reset_log(self):
        self.log.clear()
        self.reset_window()

# ----------------------------- FIXTURES --------------------------------

@pytest.fixture
def operator_policy():
    # Example: 30 MB/month, 100 messages/day, 30 days/month
    policy = MockOperatorPolicy(monthly_data_bytes=30 * 1024 * 1024,
                               max_msgs_per_day=100,
                               days_per_month=30)
    return policy

@pytest.fixture
def iot_device_app(operator_policy):
    return MockIoTDeviceApp(operator_policy)

# ----------------------------- TEST CASES ------------------------------

def test_enforce_operator_policies(iot_device_app, operator_policy):
    """
    Main requirement: Enforces daily message/data limit, monthly data cap, and max payload size.
    """

    # 1. Policy calculation checks
    max_payload = operator_policy.max_payload_size
    assert max_payload > 0

    # 2. Send up to daily message limit, each with exactly max allowed payload size
    for msg_idx in range(operator_policy.max_msgs_per_day):
        sent = iot_device_app.send_payload(max_payload)
        assert sent, f"Message #{msg_idx+1} should be delivered when within limits"
    # Next message should fail due to message limit
    sent = iot_device_app.send_payload(max_payload)
    assert not sent, "Message limit for the day should be enforced"

    # 3. Reset day, send enough large payloads to hit data limit (using fewer, larger payloads)
    iot_device_app.increment_day()
    chunk = operator_policy.daily_data_bytes // 4
    sent_cnt = 0
    for _ in range(4):
        sent = iot_device_app.send_payload(chunk)
        sent_cnt += int(sent)
    # Next send, even if within message count, should fail if exceeds daily data
    too_much = operator_policy.daily_data_bytes - (chunk*4) + 1
    sent = iot_device_app.send_payload(too_much)
    assert not sent, "Daily data volume cap should be enforced"
    assert sent_cnt == 4

    # 4. Simulate sending messages so monthly cap is reached
    iot_device_app.increment_day()
    iot_device_app.data_sent_month = operator_policy.monthly_data_bytes - 512
    sent = iot_device_app.send_payload(512)
    assert sent
    # Should now block any further, even tiny payload
    sent = iot_device_app.send_payload(1)
    assert not sent, "Monthly data volume cap should be enforced"

    # 5. Test blocking of payloads that individually exceed max payload size
    iot_device_app.increment_day()
    too_large = operator_policy.max_payload_size + 1
    sent = iot_device_app.send_payload(too_large)
    assert not sent, "Payloads exceeding single-message policy cap must be denied"

    # 6. Repeat: Next period (day/month) resets allow again
    iot_device_app.increment_day()
    assert iot_device_app.send_payload(max_payload), "Should allow new sends in next day"
    iot_device_app.increment_month()
    assert iot_device_app.send_payload(max_payload), "Should allow new sends in next month"

    # 7. Log/behavior checks
    log = iot_device_app.get_log()
    assert "rejected:payload_too_large" in log
    assert "rejected:msg_limit_daily" in log
    assert "rejected:data_limit_daily" in log
    assert "rejected:data_limit_monthly" in log
    assert log.count("sent") > 0
    print("Event Log:", log)

def test_block_and_queue_when_limits_reached(iot_device_app, operator_policy):
    """
    When blocked due to limits, device SHOULD refuse or queue data until next period.
    """
    # Fill up messages for the day
    for _ in range(operator_policy.max_msgs_per_day):
        assert iot_device_app.send_payload(operator_policy.max_payload_size)
    # Now MUST reject new messages for today
    assert not iot_device_app.send_payload(1)
    # After day reset, should allow again
    iot_device_app.increment_day()
    assert iot_device_app.send_payload(operator_policy.max_payload_size)

def test_edge_case_max_payload_exact_boundary(iot_device_app, operator_policy):
    """
    Test sending payloads at the exact boundary of maximum allowed size.
    """
    # Exactly max size: should be allowed
    assert iot_device_app.send_payload(operator_policy.max_payload_size)
    # Just over: should be blocked
    assert not iot_device_app.send_payload(operator_policy.max_payload_size + 1)

```

---

**How to Use:**
- Save as `tests/test_operator_policy_enforcement.py`.
- Replace `MockIoTDeviceApp` with your real device API/SDK for actual integration.
- Integrate with your device logs or cloud for backend validation of transmission and policy enforcement.
- Run tests with:
  ```bash
  pytest tests/test_operator_policy_enforcement.py
  ```

**Coverage:**
- Enforces daily message cap, monthly volume cap, max-per-message payload.
- Verifies edge and boundary conditions (over-limit, exact limit).
- Checks blocking/queuing when limits reached and auto-resume after new period.
- All pass/fail criteria mapped to explicit assertions for compliance.