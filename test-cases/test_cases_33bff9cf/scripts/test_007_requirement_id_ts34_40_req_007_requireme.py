```python
# File: tests/test_keepalive_polling_interval.py

"""
TS.34_4.0_REQ_007 - Keep Alive Polling Interval Compliance Test

Verifies that:
  - The device uses the polling interval provided by the Mobile Network Operator (MNO) for keep alive messages.
  - If no interval is specified by the MNO, it defaults to 29 minutes (for TCP).
  - The polling interval can be updated by both local and remote configuration methods.
  - For UDP, the device uses a timer appropriate to the simulated operator/environment.
References:
  - GSMA TS.34 v8.0, Section 4.0, TS.34_4.0_REQ_007/006
  - a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest
import time

# ---- MOCK INTERFACES / PLACEHOLDERS (Replace with real device API calls as needed) ----

class MockIoTDeviceApp:
    """
    Simulates the IoT Device Application's configurable keep alive logic for TCP/UDP.
    """
    def __init__(self, protocol='TCP'):
        self.protocol = protocol
        self.configured_interval = None
        self.operator_interval = None
        self.default_tcp_interval = 29 * 60  # seconds (29 minutes)
        self.udp_env_interval = 10 * 60      # seconds (example operator default for UDP: 10 minutes)
        self.keepalive_log = []
        self.running = False

    def set_protocol(self, protocol):
        self.protocol = protocol

    def set_operator_polling_interval(self, interval_s):
        """Simulate operator configuring a polling interval (None = unknown)."""
        self.operator_interval = interval_s

    def configure_interval_remote(self, interval_s):
        """Change polling interval via remote/OTA config."""
        self.configured_interval = interval_s

    def configure_interval_local(self, interval_s):
        """Change polling interval via local API/UI/config."""
        self.configured_interval = interval_s

    def get_current_keepalive_interval(self):
        if self.configured_interval is not None:
            return self.configured_interval
        elif self.operator_interval is not None:
            return self.operator_interval
        else:
            if self.protocol == 'TCP':
                return self.default_tcp_interval
            elif self.protocol == 'UDP':
                return self.udp_env_interval
            else:
                raise ValueError("Unknown protocol")

    def run_keepalive_cycle(self, cycles=3):
        # Simulate sending keep alive messages based on the currently configured interval
        interval = self.get_current_keepalive_interval()
        self.keepalive_log = []
        now = time.time()
        for i in range(cycles):
            self.keepalive_log.append(now + i * interval)
        return list(self.keepalive_log)

    def change_environment_udp_interval(self, udp_env_interval):
        self.udp_env_interval = udp_env_interval

# ---- TEST FIXTURES ----

@pytest.fixture
def iot_device_app():
    """Provides a new simulated IoT Device Application instance."""
    return MockIoTDeviceApp()

# ---- TESTS ----

def test_keepalive_uses_operator_interval_tcp(iot_device_app):
    """
    Step 1-2: Given operator interval set, protocol TCP, confirm device uses operator value for keep alive.
    """
    iot_device_app.set_protocol('TCP')
    operator_interval = 15 * 60  # 15 minutes
    iot_device_app.set_operator_polling_interval(operator_interval)
    intervals = iot_device_app.run_keepalive_cycle()
    # Intervals between keep alive messages should be approximately the operator interval
    actual_interval = intervals[1] - intervals[0]
    assert abs(actual_interval - operator_interval) < 2, \
        f"Device did not use operator-specified interval for TCP (expected {operator_interval}, got {actual_interval})"


def test_keepalive_uses_default_29m_tcp_when_no_operator_interval(iot_device_app):
    """
    Step 3-4: With no operator interval and TCP, device defaults to 29 minutes.
    """
    iot_device_app.set_protocol('TCP')
    iot_device_app.set_operator_polling_interval(None)  # Simulate unknown/preference not set
    intervals = iot_device_app.run_keepalive_cycle()
    expected_interval = iot_device_app.default_tcp_interval
    actual_interval = intervals[1] - intervals[0]
    assert abs(actual_interval - expected_interval) < 2, \
        f"Device did not use default 29-minute interval for TCP (expected {expected_interval}, got {actual_interval})"


def test_keepalive_remote_and_local_configurable(iot_device_app):
    """
    Step 5: Confirm keep alive polling interval can be changed via both OTA (remote) and local config.
    """
    iot_device_app.set_protocol('TCP')
    iot_device_app.set_operator_polling_interval(15 * 60)  # Operator suggests 15 min

    # Remote config overrides operator interval
    remote_interval = 20 * 60  # 20 minutes
    iot_device_app.configure_interval_remote(remote_interval)
    intervals_remote = iot_device_app.run_keepalive_cycle()
    actual_remote = intervals_remote[1] - intervals_remote[0]
    assert abs(actual_remote - remote_interval) < 2, \
        f"Remote-configured interval not applied (expected {remote_interval}, got {actual_remote})"
    
    # Local config overrides remote/operator
    local_interval = 10 * 60  # 10 minutes
    iot_device_app.configure_interval_local(local_interval)
    intervals_local = iot_device_app.run_keepalive_cycle()
    actual_local = intervals_local[1] - intervals_local[0]
    assert abs(actual_local - local_interval) < 2, \
        f"Local-configured interval not applied (expected {local_interval}, got {actual_local})"


@pytest.mark.parametrize("env_udp_interval", [9*60, 13*60])
def test_keepalive_uses_udp_environment_value(iot_device_app, env_udp_interval):
    """
    Step 6: If UDP, the polling interval used should match environment/operator (not TCP value).
    """
    iot_device_app.set_protocol('UDP')
    iot_device_app.set_operator_polling_interval(None)  # value controlled by simulated environment
    iot_device_app.change_environment_udp_interval(env_udp_interval)
    intervals = iot_device_app.run_keepalive_cycle()
    actual_interval = intervals[1] - intervals[0]
    assert abs(actual_interval - env_udp_interval) < 2, \
        f"UDP environment timer not respected (expected {env_udp_interval}, got {actual_interval})"


def test_keepalive_interval_modification_for_udp(iot_device_app):
    """
    Confirm config API changes interval for UDP as with TCP.
    """
    iot_device_app.set_protocol('UDP')
    iot_device_app.set_operator_polling_interval(None)
    iot_device_app.change_environment_udp_interval(600)  # initial env is 10 min

    # Change via remote
    iot_device_app.configure_interval_remote(500)
    intervals_remote = iot_device_app.run_keepalive_cycle()
    actual_remote = intervals_remote[1] - intervals_remote[0]
    assert abs(actual_remote - 500) < 2, \
        f"Remote config interval not applied on UDP (expected 500, got {actual_remote})"

    # Change via local
    iot_device_app.configure_interval_local(420)
    intervals_local = iot_device_app.run_keepalive_cycle()
    actual_local = intervals_local[1] - intervals_local[0]
    assert abs(actual_local - 420) < 2, \
        f"Local config interval not applied on UDP (expected 420, got {actual_local})"

```

---

**How to Use/Customize:**
- Place this script in your `tests/` directory as `test_keepalive_polling_interval.py`.
- Replace the `MockIoTDeviceApp` methods with real device management APIs if applicable.
- Adjust tolerances and timing as needed for your test lab/testbed environment.
- This script covers: operator-interval adherence, default fallback for TCP, local and remote interval configurability, UDP-specific interval implementation.

**Run with:**
```bash
pytest tests/test_keepalive_polling_interval.py
```

Let me know if you need adaptation for integration with your actual API/device cloud interface!