```python
# File: tests/test_congestion_control_apn_and_mobility.py

"""
Test Case for:
Requirement ID : TS.34_9.1_REQ_001

Requirement:
The IoT Device SHALL support both APN-based congestion control and mobility management congestion control.
When rejected with a back-off timer (for APN/congestion or mobility management), the device must not retry prior to expiry.

References:
- GSMA TS.34 v8.0, Section 9.1, TS.34_9.1_REQ_001
- 3GPP TS 23.401 (MM/TAU congestion), TS 23.060 (APN/SM congestion)
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest
import time

# -- Mock/Placeholder classes for demonstration. Replace with integration/API hooks for lab/system --

class MockCongestionControlNetwork:
    """Simulates a network that can trigger APN or Mobility Management congestion rejects with back-off timers."""
    def __init__(self):
        self.reject_type = None
        self.backoff_timer = 0  # seconds

    def configure_reject(self, reject_type, backoff_timer):
        """Set up the network to reject with a timer."""
        self.reject_type = reject_type
        self.backoff_timer = backoff_timer

    def receive_request(self, request_type):
        """
        Responds to requests with congestion control reject and timer if configured.
        :param request_type: 'APN' or 'MM' (Mobility Management)
        """
        if request_type == self.reject_type:
            return {"rejected": True, "backoff_timer": self.backoff_timer}
        return {"rejected": False}

class MockIoTDevice:
    """Simulates congestion control logic and session/mobility request handling of an IoT device."""
    def __init__(self, network: MockCongestionControlNetwork):
        self.network = network
        self._now = 0  # Simulated time in seconds (replace with time.time() for real)
        # APN congestion state per APN or all; MM one-shot state
        self.apn_backoff_expiry = {}
        self.mm_backoff_expiry = 0
        self.event_log = []

    def set_time(self, t):
        self._now = t

    def advance_time(self, s):
        self._now += s

    def request_apn_session(self, apn):
        # Honor back-off timer per APN
        expiry = self.apn_backoff_expiry.get(apn, 0)
        if self._now < expiry:
            self.event_log.append(f"APN session request for {apn} BLOCKED until {expiry} (now={self._now})")
            return False
        # Send to network
        resp = self.network.receive_request("APN")
        if resp["rejected"]:
            self.apn_backoff_expiry[apn] = self._now + resp["backoff_timer"]
            self.event_log.append(f"APN session request for {apn} REJECTED, back-off until {self.apn_backoff_expiry[apn]}")
            return False
        self.event_log.append(f"APN session request for {apn} ALLOWED at {self._now}")
        return True

    def request_mobility_management(self):
        # Honor MM back-off timer (all MM requests blocked if active)
        if self._now < self.mm_backoff_expiry:
            self.event_log.append(f"Mobility management request BLOCKED until {self.mm_backoff_expiry} (now={self._now})")
            return False
        # Send to network
        resp = self.network.receive_request("MM")
        if resp["rejected"]:
            self.mm_backoff_expiry = self._now + resp["backoff_timer"]
            self.event_log.append(f"Mobility management request REJECTED, back-off until {self.mm_backoff_expiry}")
            return False
        self.event_log.append(f"Mobility management request ALLOWED at {self._now}")
        return True

    def get_log(self):
        return list(self.event_log)

    def reset(self):
        self.apn_backoff_expiry = {}
        self.mm_backoff_expiry = 0
        self._now = 0
        self.event_log = []

# -- Pytest Fixtures --

@pytest.fixture
def network():
    return MockCongestionControlNetwork()

@pytest.fixture
def device(network):
    dev = MockIoTDevice(network)
    yield dev
    dev.reset()

# --- TEST SCRIPT ---

def test_iot_device_honors_apn_based_congestion_control(network, device):
    """Test for APN-based congestion control: device MUST honor network back-off timer."""
    apn = "apn.data"
    # 1. Network set to reject APN requests for 30 seconds
    network.configure_reject("APN", backoff_timer=30)
    t0 = 100
    device.set_time(t0)

    # 2. Attempt APN session initiation (should be rejected and back-off invoked)
    assert not device.request_apn_session(apn)
    log = device.get_log()
    assert any("REJECTED, back-off" in l for l in log)
    # 3. Re-attempt before expiry – device must block
    device.advance_time(15)
    assert not device.request_apn_session(apn), "Device retried APN session before back-off expiry"
    # 4. After expiry – should allow
    device.advance_time(20)
    assert device.request_apn_session(apn), "Device should allow APN request after back-off expiry"
    print("APN-based congestion control log:", device.get_log())

def test_iot_device_honors_mobility_management_congestion_control(network, device):
    """Test for mobility management congestion control: device MUST honor MM back-off timer."""
    # 1. Network set to reject mobility management (Attach/TAU/RAU) for 45 seconds
    network.configure_reject("MM", backoff_timer=45)
    t0 = 200
    device.set_time(t0)

    # 2. Attempt mobility management (should be rejected and set MM backoff)
    assert not device.request_mobility_management()
    log = device.get_log()
    assert any("REJECTED, back-off" in l for l in log)
    # 3. Attempt before expiry (must be blocked)
    device.advance_time(15)
    assert not device.request_mobility_management(), "Device retried mobility mgmt before back-off expiry"
    device.advance_time(30)
    assert not device.request_mobility_management(), "Still within back-off"
    # 4. After expiry, allow again
    device.advance_time(1)
    assert device.request_mobility_management()
    print("Mobility Management congestion control log:", device.get_log())

def test_iot_device_supports_both_congestion_control_types(network, device):
    """Device recognizes and properly applies both congestion control mechanisms together."""
    apn1, apn2 = "iot.apn", "iot2.apn"
    network.configure_reject("APN", backoff_timer=25)
    t0 = 300
    device.set_time(t0)
    # APN 1 – will be rejected and blocked for 25s
    assert not device.request_apn_session(apn1)
    device.advance_time(10)
    assert not device.request_apn_session(apn1)
    # APN 2 (different) – not blocked
    assert device.request_apn_session(apn2)
    # Now block MM as well
    network.configure_reject("MM", backoff_timer=20)
    device.set_time(t0 + 15)
    assert not device.request_mobility_management()
    device.advance_time(10)
    # Confirm APN1 still blocked until expiry; APN2 allowed; MM still blocked
    assert not device.request_apn_session(apn1)
    assert device.request_apn_session(apn2)
    assert not device.request_mobility_management()
    # Move past both timers, all succeed
    device.advance_time(20)
    assert device.request_apn_session(apn1)
    assert device.request_mobility_management()
    print("Full dual congestion control log:", device.get_log())

@pytest.mark.parametrize(
    "scenario", ["apn", "mm"]
)
def test_multiple_cycles_and_compliance(network, device, scenario):
    """Test multiple cycles, ensure timers are reset and logic holds consistently."""
    if scenario == "apn":
        network.configure_reject("APN", backoff_timer=10)
        device.set_time(500)
        apn = "repeat.data"
        for cycle in range(3):
            assert not device.request_apn_session(apn)  # first is rejected
            for i in range(1, 3):
                device.advance_time(5)
                assert not device.request_apn_session(apn)
            device.advance_time(5)
            assert device.request_apn_session(apn)
    else:
        network.configure_reject("MM", backoff_timer=8)
        device.set_time(1000)
        for cycle in range(3):
            assert not device.request_mobility_management()
            device.advance_time(2)
            assert not device.request_mobility_management()
            device.advance_time(6)
            assert device.request_mobility_management()

    # Output logs for audit
    print(f"Congestion control ({scenario}) cycles log: {device.get_log()}")

```
---

**Instructions:**
- Save as `tests/test_congestion_control_apn_and_mobility.py`.
- Replace mocks with real device/network test integration or log API.
- Run with:
  ```bash
  pytest tests/test_congestion_control_apn_and_mobility.py
  ```
- All assertions map to TS.34_9.1_REQ_001 and 3GPP/GSMA references. The test logs provide clear pass/fail evidence for audit.

Let me know if you want more field/edge cases or AT/log parser hooks for lab automation!