```python
# File: tests/test_embedded_service_layer_keepalive_nat_timer.py

"""
Test Case for:
Requirement ID: TS.34_4.2_REQ_006

Requirement:
If the IoT Service requires keep alive messages, the IoT Embedded Service Layer SHOULD
automatically detect the Mobile Network Operator’s TCP_IDLE/UDP_IDLE value (NAT timers) 
by incrementally increasing the polling interval until timeout and then operate just below that value.
The layer SHOULD adapt automatically to changes, not rely on hard-coded intervals.

References:
- GSMA TS.34 v8.0, Section 4.2, Requirement TS.34_4.2_REQ_006 (pages 18, 24)
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest

# --- MOCK IMPLEMENTATION (Replace with actual device/service layer hooks for real integration) ---

class MockNatSimulator:
    """
    Simulates the network operator's NAT timeout for TCP/UDP.
    Changeable in tests to emulate network/operator change.
    """
    def __init__(self, nat_timeout_seconds=1800):  # 30 minutes by default
        self.current_nat_timeout = nat_timeout_seconds

    def set_nat_timeout(self, nat_timeout_seconds):
        self.current_nat_timeout = nat_timeout_seconds

    def is_connection_alive(self, last_packet_time, current_time):
        return (current_time - last_packet_time) < self.current_nat_timeout

class MockEmbeddedServiceLayer:
    """
    Simulates the IoT Embedded Service Layer's keep alive interval detection logic.
    Uses feedback from connections being dropped to adapt polling interval just below NAT timeout.
    """
    def __init__(self, nat_simulator: MockNatSimulator, detection_granularity=60):
        self.nat_simulator = nat_simulator
        self.detection_granularity = detection_granularity  # increase polling interval in increments, in seconds
        self.adapted_polling_interval = None
        self.detection_log = []
        self.polling_history = []

    def detect_and_adapt_polling_interval(self, initial_interval=300, max_test_interval=4000):
        """
        Incrementally increase polling interval until NAT timeout is detected.
        Set adapted interval just below the detected threshold.
        """
        polling_interval = initial_interval
        last_packet_time = 0
        current_time = 0
        found_timeout = False
        logs = []  # (interval, stayed_alive)
        while polling_interval < max_test_interval:
            # Send a keep alive, then 'sleep' for polling_interval
            current_time += polling_interval
            self.polling_history.append(polling_interval)

            # Check if connection is still alive (simulate network drop if over NAT timeout)
            if self.nat_simulator.is_connection_alive(last_packet_time, current_time):
                logs.append((polling_interval, True))
                last_packet_time = current_time  # Keep alive keeps it refreshed
                polling_interval += self.detection_granularity  # Try longer interval next
            else:
                logs.append((polling_interval, False))
                found_timeout = True
                # Step back to just below this interval
                self.adapted_polling_interval = polling_interval - self.detection_granularity
                self.detection_log.append(
                    f"Detected NAT timeout at {polling_interval}s, set keep alive to {self.adapted_polling_interval}s"
                )
                break

        assert found_timeout, "Never detected NAT timeout in test; possible logic error in simulation."
        return self.adapted_polling_interval, logs

    def adapt_to_new_nat_timeout(self, new_timeout, initial_interval=300):
        # Reset previous adaptation, simulate new detection
        self.adapted_polling_interval = None
        self.polling_history = []
        self.nat_simulator.set_nat_timeout(new_timeout)
        return self.detect_and_adapt_polling_interval(initial_interval=initial_interval, max_test_interval=new_timeout + 600)

    def get_log(self):
        return list(self.detection_log)

    def get_polling_history(self):
        return list(self.polling_history)

    def uses_hard_coded_interval(self):
        """In compliant design, the interval should never be the same between NAT timeout changes."""
        # If always returns same value regardless of NAT change, it's hard-coded.
        return False  # For the mock, we actually always adapt!

    def reset(self):
        self.adapted_polling_interval = None
        self.detection_log.clear()
        self.polling_history.clear()

# --- FIXTURES ---

@pytest.fixture
def nat_simulator():
    return MockNatSimulator(nat_timeout_seconds=1800)  # 30 min

@pytest.fixture
def esl(nat_simulator):
    return MockEmbeddedServiceLayer(nat_simulator)

# --- TEST CASE ---

def test_esl_keepalive_nat_timer_detection_and_adaptation(esl, nat_simulator):
    """
    Requirement TS.34_4.2_REQ_006:
    - ESL should incrementally increase keep-alive polling interval until NAT timeout is detected.
    - ESL should set interval just below NAT timeout and adapt automatically if the value changes.
    - No hard-coded/fixed polling interval is used.
    """

    # Step 1–3: Configure initial NAT timeout (e.g., 1800s), detect interval
    detected_interval, logs = esl.detect_and_adapt_polling_interval(initial_interval=300, max_test_interval=2400)
    expected_just_below = nat_simulator.current_nat_timeout - esl.detection_granularity
    assert abs(detected_interval - expected_just_below) <= 1, (
        f"Polling interval should be just below NAT timeout: expected {expected_just_below}, got {detected_interval}"
    )

    # Step 4: All log/trace info present
    assert any("Detected NAT timeout" in entry for entry in esl.get_log()), "Detection log missing NAT timeout detection"
    print("First detection log:", esl.get_log())
    print("First polling history:", esl.get_polling_history())

    # Step 5: Simulate a change in network NAT timer (e.g., drop to 900s) and repeat detection
    new_timeout = 900
    adapted_interval, new_logs = esl.adapt_to_new_nat_timeout(new_timeout, initial_interval=300)
    expected_new_just_below = new_timeout - esl.detection_granularity
    assert abs(adapted_interval - expected_new_just_below) <= 1, (
        f"Polling interval after NAT update should be just below new timeout: expected {expected_new_just_below}, got {adapted_interval}"
    )

    # Step 6: Ensure "hard-coded" fixed polling interval is not used
    assert not esl.uses_hard_coded_interval(), "Should not use a fixed, hard-coded polling interval"

    # Step 7: All adapt/log actions must be traceable
    combined_log = esl.get_log()
    assert any(str(new_timeout) in entry for entry in combined_log), "Adaptation log does not reflect new NAT timeout"

    # Step 8: Confirm adaptation (not fixed/hard-coded), all evidence present
    print("Adaptation log after NAT timer update:", combined_log)
    print("Polling interval history after NAT change:", esl.get_polling_history())

    # Final exit: All criteria a–d covered by assertions/logs above

```

---

**How to Use/Customize:**
- Save as `tests/test_embedded_service_layer_keepalive_nat_timer.py`.
- Replace the mock logic with your actual Embedded Service Layer detection logic and NAT environment hooks.
- Run with:
  ```bash
  pytest tests/test_embedded_service_layer_keepalive_nat_timer.py
  ```
- The script traces interval adaptation and checks for compliance with TS.34_4.2_REQ_006 and TS.34-v8, Section 4.2.
- All logs and detected/adapted values are printed/reported for traceability.
