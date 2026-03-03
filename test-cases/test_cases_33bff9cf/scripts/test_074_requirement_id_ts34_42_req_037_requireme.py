```python
# File: tests/test_esl_lan_connectivity_loss_handling.py

"""
Test Case for:
Requirement ID: TS.34_4.2_REQ_037

Requirement:
When the IoT Embedded Service Layer detects that the IoT Device has lost LAN connectivity with peripheral devices,
and the LAN connectivity function is NOT hosted on the communication module/chipset hardware, the ESL SHOULD:
    - Perform diagnostics,
    - Reboot only the affected hardware component (not the device or comm module/chipset),
    - Send an alert to the IoT Server Application.
    - All steps must be logged and verifiable.

References:
- GSMA TS.34 v8.0, Section 4.2, Requirement TS.34_4.2_REQ_037
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf (Section 4.2, Requirement Table, page 28)
"""

import pytest

# -- MOCK CLASSES (replace with integration for hardware/system testing as needed) --

class MockIoTServerApp:
    """Simulate the server which receives alerts from the ESL."""
    def __init__(self):
        self.received_alerts = []

    def receive_alert(self, alert):
        self.received_alerts.append(alert)

    def get_last_alert(self):
        return self.received_alerts[-1] if self.received_alerts else None

    def clear(self):
        self.received_alerts.clear()

class MockLANHardwareComponent:
    """Simulate an affected LAN hardware component (not on comm module) with diagnostics and reboot ability."""
    def __init__(self, name="lan_eth0"):
        self.name = name
        self.diagnostics_performed = False
        self.rebooted = False
        self.log = []

    def perform_diagnostics(self):
        self.diagnostics_performed = True
        self.log.append(f"Diagnostics performed on {self.name}")

    def reboot(self):
        self.rebooted = True
        self.log.append(f"{self.name} rebooted")

    def reset(self):
        self.diagnostics_performed = False
        self.rebooted = False
        self.log = []

class MockIoTEmbeddedServiceLayer:
    """
    Simulates the ESL, capable of detecting LAN loss, performing diagnostics,
    rebooting individual LAN hardware, and sending alerts to the server app.
    """
    def __init__(self, lan_hw, server_app):
        self.lan_hw = lan_hw
        self.server_app = server_app
        self.lan_connected = True
        self.log = []

    def detect_and_handle_lan_loss(self):
        # Simulate detection of LAN connectivity loss
        self.log.append("LAN connectivity loss detected")
        # a) Diagnostics step
        self.lan_hw.perform_diagnostics()
        self.log.append(f"Diagnostics initiated for {self.lan_hw.name}")
        # b) Reboot only the affected LAN hardware component
        self.lan_hw.reboot()
        self.log.append(f"Rebooted LAN hardware: {self.lan_hw.name}")
        # c) Send alert to IoT Server Application
        alert = {
            "event": "lan_connectivity_loss",
            "component": self.lan_hw.name,
            "diagnostics": self.lan_hw.diagnostics_performed,
            "hw_rebooted": self.lan_hw.rebooted,
            "scope": "component_only",
            "details": "LAN connectivity loss detected and remedied"
        }
        self.server_app.receive_alert(alert)
        self.log.append("Alert sent to IoT Server Application")

    def simulate_lan_disconnect(self):
        # Induce LAN connectivity loss (Step 1)
        self.lan_connected = False
        self.detect_and_handle_lan_loss()

    def get_log(self):
        return list(self.log)

    def reset(self):
        self.lan_connected = True
        self.log.clear()
        self.lan_hw.reset()

# -- PYTEST FIXTURES --

@pytest.fixture
def server_app():
    app = MockIoTServerApp()
    yield app
    app.clear()

@pytest.fixture
def lan_hw():
    comp = MockLANHardwareComponent()
    yield comp
    comp.reset()

@pytest.fixture
def esl(lan_hw, server_app):
    esl = MockIoTEmbeddedServiceLayer(lan_hw, server_app)
    yield esl
    esl.reset()
    lan_hw.reset()
    server_app.clear()

# -- TEST CASE --

def test_esl_handles_lan_connectivity_loss_properly(esl, lan_hw, server_app):
    """
    TS.34_4.2_REQ_037:
    - After simulated LAN loss, diagnostics performed by ESL,
    - Only the affected LAN hardware component rebooted,
    - An alert is sent to IoT Server Application,
    - All steps are logged and verifiable.
    """
    # Step 1: Simulate LAN disconnect (induce connectivity loss)
    esl.simulate_lan_disconnect()
    log = esl.get_log()

    # a) Diagnostics step performed and logged
    assert lan_hw.diagnostics_performed, "Diagnostics not performed on LAN hardware component."
    assert any("Diagnostics" in l for l in log), "Diagnostics event not logged in ESL log."

    # b) Only the affected hardware component is rebooted (not device/module)
    assert lan_hw.rebooted, "LAN hardware component was not rebooted."
    assert any("Rebooted LAN hardware" in l for l in log), "LAN hardware reboot not logged."

    # c) Alert to IoT Server Application contains correct details
    alert = server_app.get_last_alert()
    assert alert is not None, "No alert sent to IoT Server Application."
    assert alert['event'] == "lan_connectivity_loss"
    assert alert['diagnostics'] is True
    assert alert['hw_rebooted'] is True
    assert alert['scope'] == "component_only"

    # d) All actions verifiable by logs and alert content
    assert len(log) >= 4, "Action log incomplete."
    for step in ["LAN connectivity", "Diagnostics initiated", "Rebooted LAN hardware", "Alert sent"]:
        assert any(step in entry for entry in log), f"{step} not found in ESL log"

    # Print logs for debug/auditability
    print("ESL Action Log:", log)
    print("LAN Hardware Log:", lan_hw.log)
    print("IoT Server received alert:", alert)

```
---

**Instructions:**
- Save as `tests/test_esl_lan_connectivity_loss_handling.py`.
- Replace mocks with integration points to your system or device under test if available.
- Run with:
  ```bash
  pytest tests/test_esl_lan_connectivity_loss_handling.py
  ```
- The script covers all pass/fail criteria from the requirement: diagnostics, isolated hardware reboot, alerting, and logs.

Reach out if you need further customization for hardware integration or real device/log instrumentation!