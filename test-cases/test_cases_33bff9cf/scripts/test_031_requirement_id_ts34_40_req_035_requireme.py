```python
# File: tests/test_gnss_coverage_loss_diagnostics_reboot_alert.py

"""
Test Case for:
Requirement ID: TS.34_4.0_REQ_035
Requirement: When GNSS coverage is lost, and the GNSS receiver is NOT hosted on the communication module/chipset hardware,
the IoT Device Application SHOULD perform diagnostics, reboot only the GNSS hardware component, and send an alert to the IoT Server Application.

References:
- GSMA TS.34 v8.0, Section 4.0, Requirement TS.34_4.0_REQ_035
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
- TS.34_4.0_REQ_034 and TS.34_4.0_REQ_036 (for context/contrast)
"""

import pytest
import time

# --- MOCK CLASSES (Replace/extend with real device APIs, GNSS simulators, log interfaces, and test cloud endpoints as needed) ---

class MockIoTServerApp:
    """Simulates the IoT Server Application, receiving and logging alerts from devices."""
    def __init__(self):
        self.received_alerts = []

    def receive_alert(self, payload):
        self.received_alerts.append(payload)

    def clear(self):
        self.received_alerts = []

    def get_alerts(self):
        return list(self.received_alerts)

class MockIoTDeviceApp:
    """
    Simulates the IoT Device Application with an external (non-chipset) GNSS receiver.
    Models detection of GNSS coverage loss, diagnostics, reboot of GNSS receiver, and alerting to server.
    """
    def __init__(self, server_app):
        self.gnss_coverage = True
        self.gnss_on_comm_module = False    # specifically NOT on comm module/chipset
        self.device_rebooted = False
        self.comm_module_rebooted = False
        self.gnss_receiver_rebooted = False
        self.diagnostics_performed = False
        self.server_app = server_app
        self.action_log = []

    def configure_gnss_normal(self):
        self.gnss_coverage = True
        self.gnss_receiver_rebooted = False
        self.diagnostics_performed = False
        self.device_rebooted = False
        self.comm_module_rebooted = False
        self.action_log.clear()

    def simulate_gnss_coverage_loss(self):
        self.gnss_coverage = False
        self.detect_and_handle_gnss_loss()

    def detect_and_handle_gnss_loss(self):
        # Step 3: Detect loss of GNSS coverage
        if not self.gnss_coverage:
            self.action_log.append("GNSS coverage lost")
            # Step 4: Perform diagnostics on GNSS receiver (not whole device)
            self.diagnostics_performed = True
            self.action_log.append("diagnostics on GNSS receiver performed")
            # Step 5: Reboot only GNSS receiver
            self.gnss_receiver_rebooted = True
            self.action_log.append("GNSS receiver rebooted")
            # Step 6: Ensure no improper reboots
            # (If either of the following becomes True, test must fail)
            # self.device_rebooted = True
            # self.comm_module_rebooted = True
            # Step 6: Send alert to IoT Server App
            self.send_gnss_loss_alert()
        # Else: If coverage still present, do nothing (normal ops)

    def send_gnss_loss_alert(self):
        payload = {
            "event": "gnss_coverage_loss",
            "when": time.time(),
            "diagnostics": self.diagnostics_performed,
            "reboot": "gnss_receiver" if self.gnss_receiver_rebooted else None,
            "reboot_device": self.device_rebooted,
            "reboot_comm_module": self.comm_module_rebooted,
            "details": "diagnostics/reboot action taken on GNSS receiver only"
        }
        self.server_app.receive_alert(payload)
        self.action_log.append("alert sent to IoT Server")

    def get_action_log(self):
        return list(self.action_log)
    
    def reset(self):
        self.configure_gnss_normal()

# --- FIXTURES ---

@pytest.fixture
def server_app():
    app = MockIoTServerApp()
    yield app
    app.clear()

@pytest.fixture
def device_app(server_app):
    app = MockIoTDeviceApp(server_app)
    yield app
    app.reset()
    server_app.clear()

# --- TEST CASE ---

def test_gnss_loss_diagnostics_reboot_alert(device_app, server_app):
    """
    TS.34_4.0_REQ_035:
    When GNSS coverage is lost (GNSS NOT on comm module), the Device App:
      - performs diagnostics,
      - ONLY reboots GNSS receiver,
      - sends an alert (with details) to the server,
      - does NOT reboot entire device or comm module.
    """
    # Step 1: Configure device for GNSS normal operation
    device_app.configure_gnss_normal()

    # Step 2: Simulate/induce loss of GNSS coverage
    device_app.simulate_gnss_coverage_loss()

    # Step 3: Check that GNSS coverage loss detected and handled
    log = device_app.get_action_log()
    assert "GNSS coverage lost" in log, "Device did not detect GNSS loss"

    # Step 4: Ensure diagnostics were performed
    assert device_app.diagnostics_performed, "Diagnostics were not performed on GNSS receiver after loss"

    # Step 5: Check that ONLY GNSS receiver was rebooted
    assert device_app.gnss_receiver_rebooted, "GNSS receiver was not rebooted"
    assert not device_app.device_rebooted, "Device should NOT be rebooted"
    assert not device_app.comm_module_rebooted, "Comm module/chipset should NOT be rebooted"

    # Step 6: Verify alert was generated and sent, and content is correct
    alerts = server_app.get_alerts()
    assert len(alerts) > 0, "No alert sent to IoT Server Application"
    alert = alerts[-1]
    assert alert["event"] == "gnss_coverage_loss"
    assert alert["diagnostics"] is True
    assert alert["reboot"] == "gnss_receiver"
    assert alert["reboot_device"] is False
    assert alert["reboot_comm_module"] is False
    assert "diagnostics/reboot action taken on GNSS receiver only" in alert["details"]

    # Step 7: Review log for all actions and alert for content
    print("Device Action Log:", log)
    print("Server Alert:", alert)

```

---

**Instructions:**
- Save as `tests/test_gnss_coverage_loss_diagnostics_reboot_alert.py`.
- Replace mocks with your real IoT device API/log/alert logic for full integration.
- To run:
  ```bash
  pytest tests/test_gnss_coverage_loss_diagnostics_reboot_alert.py
  ```

**What does this verify?**
- On GNSS loss, diagnostics and targeted reboot (only GNSS) are performed.
- No full device or comm module/chipset reboot occurs.
- Alert is sent with accurate context.
- All actions are logged and visible for review.

Let me know if you need this adapted to live device or integration with a real cloud/server API!
