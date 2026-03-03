```python
# File: tests/test_ping_pong_protection.py

"""
Test Case for:
Requirement ID : TS.34_4.0_REQ_026
Requirement: If the IoT Device supports more than one family of communications access technology 
(for example 3GPP, TD-SCDMA, Wireless LAN), the IoT Device Application SHOULD implement a protection mechanism to prevent frequent ‘Ping-Pong’ switching.

References:
- GSMA TS.34 v8.0, Section 4.0, TS.34_4.0_REQ_026
- Section 4.2, Application-level Protection and Network Technology Switching
"""

import pytest
import time

# --- MOCK IMPLEMENTATION (Replace with actual device APIs/logs if running against real hardware) ---

class MockIoTDeviceApp:
    """
    Simulates an IoT Device Application supporting multiple tech families with anti-Ping-Pong protection.
    """

    FAMILY_LIST = ["3GPP", "WLAN"]
    MIN_DWELL_TIME = 10  # seconds; the minimum time before allowing another switch

    def __init__(self):
        self.current_family = "3GPP"
        self.switch_log = []  # Each entry: (timestamp, from_family, to_family)
        self.last_switch_time = time.time()
        self.last_family = self.current_family

    def get_time(self):
        # You may substitute this in tests to control simulated time
        return time.time()

    def force_network_preference(self, preferred_family, now=None):
        """
        Simulate network conditions changing in favor of a tech family.
        Protection: If a switch to a different family is requested, 
        it only switches if enough time has passed since last change (dwell).
        """
        if now is None:
            now = self.get_time()
        if self.current_family != preferred_family:
            if now - self.last_switch_time >= self.MIN_DWELL_TIME:
                self.switch_log.append((now, self.current_family, preferred_family))
                self.last_switch_time = now
                self.last_family = self.current_family
                self.current_family = preferred_family
            # Otherwise: switch request is ignored as anti-ping-pong
        # else: no change required (already preferred)
    
    def get_switch_log(self):
        return list(self.switch_log)

    def get_current_family(self):
        return self.current_family

    def reset(self):
        self.current_family = "3GPP"
        self.switch_log = []
        self.last_switch_time = time.time()
        self.last_family = self.current_family

# --- TEST FIXTURE ---

@pytest.fixture
def iot_device_app(monkeypatch):
    app = MockIoTDeviceApp()

    # For fast test, patch time with simulated progression
    time_ref = [time.time()]
    def fake_time():
        return time_ref[0]
    app.get_time = fake_time

    def advance_time(seconds):
        time_ref[0] += seconds
    app.advance_time = advance_time

    return app

# --- TEST CASE ---

def test_ping_pong_protection_mechanism(iot_device_app):
    """
    TS.34_4.0_REQ_026: Device must not rapidly switch ('ping-pong') between access tech families.
    """
    app = iot_device_app

    # Step 1: Device under normal (3GPP) condition
    assert app.get_current_family() == "3GPP"
    start_time = app.get_time()

    # Step 2: Favor WLAN, cause switch
    app.force_network_preference("WLAN")
    log1 = app.get_switch_log()
    assert app.get_current_family() == "WLAN"
    assert len(log1) == 1

    # Step 3: Rapidly alternate preference back-and-forth within MIN_DWELL_TIME
    app.advance_time(2) # 2s later
    app.force_network_preference("3GPP")
    assert app.get_current_family() == "WLAN", "Should not switch immediately due to dwell time"

    app.advance_time(3) # 5s from first
    app.force_network_preference("3GPP")
    assert app.get_current_family() == "WLAN", "Should still not switch within dwell time"

    # Step 4: Sufficient time passed, now allow switch
    app.advance_time(app.MIN_DWELL_TIME) # total now > dwell
    app.force_network_preference("3GPP")
    log2 = app.get_switch_log()
    assert app.get_current_family() == "3GPP"
    assert len(log2) == 2

    # Step 5: Try to alternate rapidly again (should not switch until dwell time elapsed)
    app.advance_time(3)
    app.force_network_preference("WLAN")
    assert app.get_current_family() == "3GPP"
    assert len(app.get_switch_log()) == 2

    # Step 6: Elapse dwell, switch should occur
    app.advance_time(app.MIN_DWELL_TIME)
    app.force_network_preference("WLAN")
    assert app.get_current_family() == "WLAN"
    assert len(app.get_switch_log()) == 3

    # Verification: ensure minimum dwell between EACH switch in log
    log = app.get_switch_log()
    for idx in range(1, len(log)):
        prev_time = log[idx-1][0]
        curr_time = log[idx][0]
        assert curr_time - prev_time >= app.MIN_DWELL_TIME, \
            f"Ping-pong detected: Switched twice within {curr_time - prev_time:.2f}s, protection failed."

    # Print for debug/logging
    print("Switch log (timestamp, from, to):")
    for entry in log:
        print(entry)
```

---

**How to Use / Adapt:**
- Save as `tests/test_ping_pong_protection.py`.
- Integrate with your actual device API or network logs as needed.
- Adjust timing constants and switching logic to match your real application's anti-ping-pong mechanisms (minimum dwell, hysteresis, etc).
- Run with:
  ```bash
  pytest tests/test_ping_pong_protection.py
  ```
- This script simulates "ping-pong" network conditions and asserts that frequent switching is prevented by the IoT Device Application logic.