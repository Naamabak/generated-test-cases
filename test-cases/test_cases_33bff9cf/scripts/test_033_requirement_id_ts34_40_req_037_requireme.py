```python
# File: tests/test_lan_connectivity_loss_handling.py

"""
Test Case for:
Requirement ID : TS.34_4.0_REQ_037
Requirement: When the IoT Device Application detects that LAN connectivity with peripheral devices is lost 
(and the LAN function is NOT hosted on the comm module/chipset), the application should:
- perform diagnostics,
- reboot only the affected LAN hardware component,
- send an alert to the IoT Server Application.

References:
- GSMA TS.34 v8.0, Section 4.0, Requirement TS.34_4.0_REQ_037
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf (Section 4.0, page 22)
"""

import pytest

# --- MOCK/PLACEHOLDER CLASSES (replace with device/testbed APIs for integration/system testing) ---

class MockIoTServerApp:
    """Simulate the IoT Server Application receiving alerts."""
    def __init__(self):
        self.received_alerts = []

    def receive_alert(self, alert):
        self.received_alerts.append(alert)

    def last_alert(self):
        if not self.received_alerts:
            return None
        return self.received_alerts[-1]

    def clear(self):
        self.received_alerts.clear()


class MockLANHardwareComponent:
    """Simulates the LAN hardware component (not on comms module)."""
    def __init__(self, component_id="lan-eth0"):
        self.component_id = component_id
        self.rebooted = False
        self.diagnostics_run = False

    def perform_diagnostics(self):
        self.diagnostics_run = True

    def reboot(self):
        self.rebooted = True

    def reset(self):
        self.rebooted = False
        self.diagnostics_run = False


class MockIoTDeviceApp:
    """
    Simulates the IoT Device Application, able to detect LAN loss,
    run diagnostics, reboot specific LAN component, and send alerts to server app.
    """
    def __init__(self, lan_hw, server_app):
        self.lan_hw = lan_hw
        self.server_app = server_app
        self.lan_connected = True
        self.log = []

    def detect_lan_connectivity(self):
        # Detects if LAN is disconnected, and takes corrective action per TS.34_4.0_REQ_037
        if not self.lan_connected:
            # Step 3: Run diagnostics on LAN hardware component
            self.lan_hw.perform_diagnostics()
            self.log.append({
                "event": "lan_diagnostics",
                "component": self.lan_hw.component_id,
                "status": "started"
            })
            # Step 4: Reboot only the affected LAN hardware component
            self.lan_hw.reboot()
            self.log.append({
                "event": "lan_hw_reboot",
                "component": self.lan_hw.component_id,
                "status": "rebooted"
            })
            # Step 5: Send alert to IoT Server Application
            alert = {
                "type": "lan_connectivity_loss",
                "component": self.lan_hw.component_id,
                "diagnostics": "performed",
                "action": "component_rebooted"
            }
            self.server_app.receive_alert(alert)
            self.log.append({
                "event": "alert_sent",
                "details": alert
            })

    def simulate_lan_disconnect(self):
        # Step 1: Simulate disconnecting the LAN peripheral/device
        self.lan_connected = False
        self.log.append({"event": "lan_disconnect_detected"})
        self.detect_lan_connectivity()

    def get_log(self):
        return list(self.log)

    def reset(self):
        self.lan_connected = True
        self.log.clear()
        self.lan_hw.reset()

# --- TEST FIXTURES ---

@pytest.fixture
def server_app():
    app = MockIoTServerApp()
    yield app
    app.clear()

@pytest.fixture
def lan_hw_component():
    comp = MockLANHardwareComponent()
    yield comp
    comp.reset()

@pytest.fixture
def device_app(lan_hw_component, server_app):
    app = MockIoTDeviceApp(lan_hw_component, server_app)
    yield app
    app.reset()
    server_app.clear()
    lan_hw_component.reset()

# --- TEST CASE ---

def test_lan_connectivity_loss_handling(device_app, lan_hw_component, server_app):
    """
    TS.34_4.0_REQ_037:
    When LAN connectivity is lost to peripherals (with LAN managed outside comm module),
    the app should perform diagnostics, reboot only the LAN HW, and send alert to IoT Server Application.
    """
    # Step 1: Simulate LAN loss by disconnecting peripheral
    device_app.simulate_lan_disconnect()
    log = device_app.get_log()

    # Step 2: Confirm diagnostics were run on affected LAN hardware
    assert lan_hw_component.diagnostics_run, "Diagnostics not performed on LAN hardware component."
    assert any(e["event"] == "lan_diagnostics" for e in log), "Diagnostics event not logged."

    # Step 3: Confirm ONLY the LAN hardware component (not whole device/comm module) was rebooted
    assert lan_hw_component.rebooted, "LAN hardware component was not rebooted after diagnostics."
    # Assume in integration: add checks to log/system status of comm module/device to verify NO reboot/reset for them

    # Step 4: Verify alert to IoT Server Application contains proper details
    last_alert = server_app.last_alert()
    assert last_alert is not None, "No alert sent to server application."
    assert last_alert["type"] == "lan_connectivity_loss"
    assert last_alert["component"] == lan_hw_component.component_id
    assert last_alert["diagnostics"] == "performed"
    assert last_alert["action"] == "component_rebooted"

    # Step 5: All actions are logged and verifiable
    for event in ["lan_diagnostics", "lan_hw_reboot", "alert_sent"]:
        assert any(e["event"] == event for e in log), f"{event} not logged in device actions."
    print("Device action log:", log)
    print("Server application's last alert:", last_alert)

```

---

**How to Use / Customize:**
- Save as `tests/test_lan_connectivity_loss_handling.py`.
- Replace the mocks with integration to your real device application, LAN interface APIs, alert/diagnostic mechanisms, and server.
- Add/extend checks to verify the comm module/chipset did NOT reboot (integration: parse device/event logs).
- Run with:
  ```bash
  pytest tests/test_lan_connectivity_loss_handling.py
  ```

**Coverage:**
- Simulates detection of LAN loss (outside comm module).
- Checks diagnostics run, LAN hardware reboot (only), alert sent with details.
- Ensures actions are logged for traceability/audit.

Let me know if you need adaptation for your backend APIs or lab integration!