```python
# File: tests/test_embedded_service_layer_keepalive_polling_interval.py

"""
Test Case for:
Requirement ID : TS.34_4.2_REQ_007
Requirement: When 'keep alive' messages are required, the IoT Embedded Service Layer 
SHOULD use:
    - a fixed polling interval specified by the Mobile Network Operator (where available), or
    - a default of 29 minutes for TCP if not specified,
    - remote and/or local configuration capability,
    - for UDP, a network/operator-appropriate polling interval.

References:
- GSMA TS.34 v8.0, Section 4.2, Requirement TS.34_4.2_REQ_007
- GSMA TS.34 v8.0, Section 4.2, Requirement TS.34_4.2_REQ_006
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf, pages 24–25
"""

import pytest
import time

# ---- MOCK IMPLEMENTATION (Replace with your real ESL integration for live testing) ----

class MockEmbeddedServiceLayer:
    """
    Simulates Embedded Service Layer keep-alive logic with configurable intervals
    for both TCP and UDP, supporting operator and remote/local config overrides.
    """
    DEFAULT_TCP_INTERVAL = 29 * 60   # 29 minutes in seconds
    DEFAULT_UDP_INTERVAL = 10 * 60   # Example: 10 minutes (may be operator env specified)
    
    def __init__(self):
        self.protocol = 'TCP'
        self.operator_interval = None
        self.remote_config_interval = None
        self.local_config_interval = None
        self.udp_env_interval = self.DEFAULT_UDP_INTERVAL
        self.keepalive_log = []

    def set_protocol(self, proto):
        self.protocol = proto

    def set_operator_interval(self, secs):
        self.operator_interval = secs

    def set_udp_environment_interval(self, secs):
        self.udp_env_interval = secs

    def configure_interval_remote(self, secs):
        self.remote_config_interval = secs

    def configure_interval_local(self, secs):
        self.local_config_interval = secs

    def get_effective_interval(self):
        # Local overrides remote, which overrides operator, then fallback defaults.
        if self.local_config_interval is not None:
            return self.local_config_interval
        elif self.remote_config_interval is not None:
            return self.remote_config_interval
        elif self.operator_interval is not None:
            return self.operator_interval
        else:
            if self.protocol == 'TCP':
                return self.DEFAULT_TCP_INTERVAL
            elif self.protocol == 'UDP':
                return self.udp_env_interval
            else:
                raise ValueError("Unknown protocol")

    def simulate_keepalive_cycle(self, cycles=3):
        """Simulate keep-alive sending for several cycles according to effective interval."""
        interval = self.get_effective_interval()
        now = time.time()
        self.keepalive_log = []
        for i in range(cycles):
            self.keepalive_log.append(now + i * interval)
        return list(self.keepalive_log)

# ---- TEST FIXTURE ----

@pytest.fixture
def esl():
    return MockEmbeddedServiceLayer()

# ---- TESTS ----

def test_keepalive_operator_specified_tcp(esl):
    """
    Step 1-2: Operator specifies a polling interval, protocol TCP, confirm ESL uses operator value.
    """
    esl.set_protocol('TCP')
    esl.set_operator_interval(15 * 60)  # 15 minutes
    intervals = esl.simulate_keepalive_cycle()
    actual_interval = intervals[1] - intervals[0]
    assert abs(actual_interval - 900) < 2, f"Keepalive not using operator TCP interval (expected 900, got {actual_interval})"

def test_keepalive_default_29min_tcp_on_no_operator_value(esl):
    """
    Step 3: If operator value is missing, protocol TCP, ESL uses 29 minutes.
    """
    esl.set_protocol('TCP')
    esl.set_operator_interval(None)  # Remove operator override
    intervals = esl.simulate_keepalive_cycle()
    default_interval = esl.DEFAULT_TCP_INTERVAL
    actual = intervals[1] - intervals[0]
    assert abs(actual - default_interval) < 2, f"Keepalive not defaulting to 29-min for TCP (expected {default_interval}, got {actual})"

def test_keepalive_remote_and_local_configuration(esl):
    """
    Step 4: ESL allows both remote and local config changes to polling interval.
    """
    esl.set_protocol('TCP')
    esl.set_operator_interval(1800)  # operator provides 30 min

    # Remote config overrides operator
    esl.configure_interval_remote(20 * 60)
    intervals_remote = esl.simulate_keepalive_cycle()
    actual_remote = intervals_remote[1] - intervals_remote[0]
    assert abs(actual_remote - 1200) < 2, f"Remote config not applied (expected 1200, got {actual_remote})"

    # Local config overrides remote
    esl.configure_interval_local(11 * 60)
    intervals_local = esl.simulate_keepalive_cycle()
    actual_local = intervals_local[1] - intervals_local[0]
    assert abs(actual_local - 660) < 2, f"Local config not applied (expected 660, got {actual_local})"

def test_keepalive_udp_uses_env_operator_value(esl):
    """
    Step 5: For UDP, the interval matches operator/environment requirement.
    """
    esl.set_protocol('UDP')
    esl.set_operator_interval(None)
    esl.set_udp_environment_interval(14 * 60)  # simulated operator value, 14 min
    intervals = esl.simulate_keepalive_cycle()
    actual = intervals[1] - intervals[0]
    assert abs(actual - 14 * 60) < 2, f"UDP environment interval not respected (expected {14*60}, got {actual})"

def test_keepalive_interval_configurable_for_udp(esl):
    """
    Both remote and local config APIs must adjust interval for UDP as well.
    """
    esl.set_protocol('UDP')
    esl.set_operator_interval(None)
    esl.set_udp_environment_interval(600)  # 10min baseline

    # Set via remote
    esl.configure_interval_remote(515)
    intervals_remote = esl.simulate_keepalive_cycle()
    actual_remote = intervals_remote[1] - intervals_remote[0]
    assert abs(actual_remote - 515) < 2, f"Remote config interval not applied for UDP (expected 515, got {actual_remote})"

    # Set via local
    esl.configure_interval_local(420)
    intervals_local = esl.simulate_keepalive_cycle()
    actual_local = intervals_local[1] - intervals_local[0]
    assert abs(actual_local - 420) < 2, f"Local config interval not applied for UDP (expected 420, got {actual_local})"

# Optional: output for log/debug
def test_keepalive_timing_and_logs(esl):
    """
    Demonstrates log/interval tracking for coverage review.
    """
    esl.set_protocol('TCP')
    esl.set_operator_interval(900)
    esl.simulate_keepalive_cycle(5)
    print("Keepalive simulated times:", esl.keepalive_log)

```

---

**Instructions:**
- Save as `tests/test_embedded_service_layer_keepalive_polling_interval.py`.
- Replace `MockEmbeddedServiceLayer` with your real embedded service layer or testbed APIs.
- Run with:
  ```bash
  pytest tests/test_embedded_service_layer_keepalive_polling_interval.py
  ```
- All steps and assertions map closely to GSMA TS.34 requirements for keep-alive interval handling and configurability across both protocols and configuration methods.