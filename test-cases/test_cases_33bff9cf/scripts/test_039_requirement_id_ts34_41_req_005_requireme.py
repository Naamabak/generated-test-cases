```python
# File: tests/test_operator_daily_message_and_payload_limits.py

"""
Test Case for:
Requirement ID: TS.34_4.1_REQ_005
Requirement: IoT Device Application communicating over a Mobile IoT RAT
SHOULD ensure it does NOT exceed the operator's defined daily message count
limit or (if applicable) per-message payload size.

References:
- GSMA TS.34 v8.0, Section 4.1, Requirement TS.34_4.1_REQ_005
- Example operator policy: max_msgs_day, max_payload_size calculation
"""

import pytest

# --- MOCK CLASSES (Replace with device API or test harness integration as needed) ---

class MockOperatorPolicy:
    """Simulates operator policy for maximum daily messages and (optionally) payload size."""
    def __init__(self, monthly_data_bytes, max_msgs_per_day, days_per_month=30):
        self.monthly_data_bytes = monthly_data_bytes
        self.max_msgs_per_day = max_msgs_per_day
        self.days_per_month = days_per_month
        self.max_payload_size = (self.monthly_data_bytes // self.days_per_month) // self.max_msgs_per_day

class MockIoTDeviceApp:
    """
    Simulates the IoT Device App enforcing operator data/message policies.
    Tracks per-day limits and (if applicable) per-message payload size.
    """
    def __init__(self, policy):
        self.policy = policy
        self.current_day = 1
        self.sent_today = []
        self.logs = []

    def reset_day(self):
        self.sent_today.clear()

    def send_message(self, payload: bytes):
        """Simulate sending a message with a payload. Returns True if accepted, False if blocked by policy."""
        if len(self.sent_today) < self.policy.max_msgs_per_day and len(payload) <= self.policy.max_payload_size:
            self.sent_today.append(payload)
            self.logs.append({"event": "sent", "size": len(payload)})
            return True
        elif len(self.sent_today) >= self.policy.max_msgs_per_day:
            self.logs.append({"event": "blocked_excess_msg", "size": len(payload)})
            return False
        elif len(payload) > self.policy.max_payload_size:
            self.logs.append({"event": "blocked_excess_payload", "size": len(payload)})
            return False

    def get_logs(self):
        return self.logs[:]

    def reset_logs(self):
        self.logs.clear()

    def get_message_count(self):
        return len(self.sent_today)

    def get_max_payload_size(self):
        return self.policy.max_payload_size

@pytest.fixture
def operator_policy():
    # Example: 30 MB/month, 100 messages/day (default 30 days/month)
    return MockOperatorPolicy(monthly_data_bytes=30*1024*1024, max_msgs_per_day=100)

@pytest.fixture
def iot_device_app(operator_policy):
    return MockIoTDeviceApp(operator_policy)

# --- TEST CASES ---

def test_daily_message_limit_and_payload_size(iot_device_app, operator_policy):
    """
    Requirement TS.34_4.1_REQ_005: 
    - Number of messages sent per day does not exceed operator limit.
    - No single payload exceeds derived per-message payload size.
    """
    max_msg = operator_policy.max_msgs_per_day
    max_payload = operator_policy.max_payload_size

    # Step 1: Send messages up to the daily limit, each with payload at limit
    for i in range(max_msg):
        payload = bytes([0x42] * max_payload)
        result = iot_device_app.send_message(payload)
        assert result, f"Message {i+1} under limit should be accepted"
    # Step 2: Next message (over the daily cap) should be denied/dropped
    extra_payload = bytes([0x42] * max_payload)
    result = iot_device_app.send_message(extra_payload)
    assert not result, "Message over daily cap should not be sent"
    logs = iot_device_app.get_logs()
    assert any(e["event"] == "blocked_excess_msg" for e in logs)

    # Step 3: Attempt to send a message with payload exceeding the allowed size
    iot_device_app.reset_logs()
    iot_device_app.reset_day()
    oversized_payload = bytes([0x99] * (max_payload + 1))
    result = iot_device_app.send_message(oversized_payload)
    assert not result, "Payload over max size should be blocked"
    logs = iot_device_app.get_logs()
    assert any(e["event"] == "blocked_excess_payload" for e in logs)
    # Sending valid-size message after that is still permitted
    small_payload = bytes([0x01] * max_payload)
    result = iot_device_app.send_message(small_payload)
    assert result

def test_repeat_compliance_over_multiple_days(iot_device_app, operator_policy):
    """
    Repeat policy checks for two consecutive days to confirm persistent compliance.
    """
    max_msg = operator_policy.max_msgs_per_day
    max_payload = operator_policy.max_payload_size

    # First day
    for i in range(max_msg):
        result = iot_device_app.send_message(bytes([i % 256] * max_payload))
        assert result
    result = iot_device_app.send_message(bytes([0]*max_payload))
    assert not result
    iot_device_app.reset_day()
    iot_device_app.reset_logs()
    # Second day
    for i in range(max_msg):
        result = iot_device_app.send_message(bytes([i % 256] * max_payload))
        assert result
    result = iot_device_app.send_message(bytes([0]*max_payload))
    assert not result

def test_message_and_payload_logs(iot_device_app, operator_policy):
    """
    Check the logs for correct classification of sent vs. blocked messages.
    """
    max_msg = operator_policy.max_msgs_per_day
    max_payload = operator_policy.max_payload_size

    # Fill most of the quota
    for i in range(max_msg - 1):
        result = iot_device_app.send_message(bytes([0xA5] * max_payload))
        assert result
    result = iot_device_app.send_message(bytes([0xAB] * (max_payload+5)))
    assert not result, "Should block for excess payload"
    result = iot_device_app.send_message(bytes([0xAB] * max_payload))
    assert result
    # Now block for excess count
    result = iot_device_app.send_message(bytes([0x41] * max_payload))
    assert not result

    logs = iot_device_app.get_logs()
    sent = [e for e in logs if e["event"] == "sent"]
    excess_msg = [e for e in logs if e["event"] == "blocked_excess_msg"]
    excess_payload = [e for e in logs if e["event"] == "blocked_excess_payload"]
    # There should be `max_msg` sent, one excess payload, and one excess count event
    assert len(sent) == max_msg
    assert len(excess_payload) == 1
    assert len(excess_msg) == 1

    print("Logs summary: sent:", len(sent), "blocked_msg:", len(excess_msg), "blocked_payload:", len(excess_payload))

```

---

**How to Use / Customize:**
- Place as `tests/test_operator_daily_message_and_payload_limits.py`.
- Replace the mocks with real device API/test harness or log collector integration.
- Adjust the policy fixture/parameters as per your operator policies under test.
- The tests cover:
  - Maximum daily message cap
  - Per-message payload restriction
  - Blocking or queuing of excess/oversized messages
  - Day-to-day compliance with limits
- Run with:
  ```bash
  pytest tests/test_operator_daily_message_and_payload_limits.py
  ```

Let me know if you want help wiring this directly to a real device or operator integration API!
```