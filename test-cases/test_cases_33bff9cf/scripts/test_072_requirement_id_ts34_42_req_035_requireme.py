```python
# File: tests/test_esl_gnss_coverage_loss_handling.py

"""
Test Case for:
Requirement ID : TS.34_4.2_REQ_035

Requirement:
When the IoT Embedded Service Layer detects GNSS coverage loss,
it SHOULD perform diagnostics, reboot the affected GNSS hardware component (not the device or module),
and send an alert to the IoT Server Application. All actions should be traceable in logs.

References:
- GSMA TS.34 v8.0, Section 4.2, TS.34_4.2_REQ_035
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest

# ----------- MOCK/PLACEHOLDER CLASSES ---------
# Replace these with real device/hardware APIs or your test lab’s integration hooks.

class MockIoTServerApplication:
    """Simulates the IoT Server Application able to receive alerts."""
    def __init__(self):
        self.alerts = []

    def receive_alert(self, alert):
        self.alerts.append(alert)

    def get_alerts(self):
        return list(self.alerts)

    def clear(self):
        self.alerts.clear()

    def get_latest_alert(self):
        return self.alerts[-1] if self.alerts else None


class MockGNSSComponent:
    """Simulates an external GNSS receiver (not on comms chipset) with diagnostics and reboot."""
    def __init__(self):
        self.operational = True
        self.diagnostics_performed = False
        self.rebooted = False
        self.log = []

    def perform_diagnostics(self):
        self.diagnostics_performed = True
        self.log.append("GNSS diagnostics performed")

    def reboot(self):
        self.rebooted = True
        self.log.append("GNSS component rebooted")

    def reset(self):
        self.operational = True
        self.diagnostics_performed = False
        self.rebooted = False
        self.log.clear()


class MockEmbeddedServiceLayer:
    """Simulates the Embedded Service Layer that handles GNSS coverage loss."""
    def __init__(self, gnss_component, server_app):
        self.gnss_component = gnss_component
        self.server_app = server_app
        self.gnss_coverage = True
        self.log = []

    def operate_normally(self):
        self.gnss_coverage = True
        self.log.append("GNSS normal operation confirmed")

    def simulate_gnss_coverage_loss(self):
        # Step 2: Simulate/induce GNSS loss
        self.gnss_coverage = False
        self.log.append("GNSS coverage loss detected")
        # Step 3: Run diagnostics
        self.gnss_component.perform_diagnostics()
        self.log.append("Diagnostics requested due to GNSS coverage loss")
        # Step 4: Reboot only the GNSS receiver component
        self.gnss_component.reboot()
        self.log.append("GNSS component reboot requested (not device/module)")
        # Step 5: Send alert to server
        self.send_alert_on_gnss_loss()

    def send_alert_on_gnss_loss(self):
        alert = {
            "event": "gnss_coverage_loss",
            "diagnostics": self.gnss_component.diagnostics_performed,
            "rebooted_component": "GNSS receiver",
            "scope": "component_only",
            "info": "Diagnostics and reboot performed for GNSS on loss event"
        }
        self.server_app.receive_alert(alert)
        self.log.append("Alert sent to server about GNSS loss event")

    def get_log(self):
        return list(self.log)

    def reset(self):
        self.gnss_component.reset()
        self.log = []
        self.gnss_coverage = True

# ----------- PYTEST FIXTURE -----------

@pytest.fixture
def setup_environment():
    server_app = MockIoTServerApplication()
    gnss_component = MockGNSSComponent()
    esl = MockEmbeddedServiceLayer(gnss_component, server_app)
    yield esl, gnss_component, server_app
    esl.reset()
    gnss_component.reset()
    server_app.clear()

# ----------- TEST SCRIPT -----------

def test_esl_gnss_coverage_loss_prompts_diagnostics_reboot_and_alert(setup_environment):
    """
    TS.34_4.2_REQ_035:
    - On GNSS coverage loss, ESL initiates diagnostics,
      reboots only the GNSS hardware component,
      and sends an alert to the server.
    - All actions are traceable and logged.
    """
    esl, gnss_component, server_app = setup_environment

    # Step 1: Operate device and check GNSS is working
    esl.operate_normally()
    assert gnss_component.operational
    original_log_len = len(esl.get_log())

    # Step 2: Simulate GNSS coverage loss
    esl.simulate_gnss_coverage_loss()

    # Step 3: Diagnostics are performed
    assert gnss_component.diagnostics_performed
    assert "Diagnostics requested due to GNSS coverage loss" in esl.get_log()

    # Step 4: Only the GNSS hardware component is rebooted (not device/module!)
    assert gnss_component.rebooted
    assert not any("device reboot" in log for log in esl.get_log())
    assert any("GNSS component reboot requested" in entry for entry in esl.get_log())

    # Step 5: Alert is sent to IoT Server Application
    alerts = server_app.get_alerts()
    assert alerts, "No alert was sent to the server"
    latest_alert = alerts[-1]
    assert latest_alert["event"] == "gnss_coverage_loss"
    assert latest_alert["diagnostics"] is True
    assert latest_alert["rebooted_component"] == "GNSS receiver"
    assert latest_alert["scope"] == "component_only"

    # Step 6: All actions are logged and traceable
    esl_log = esl.get_log()
    gnss_log = gnss_component.log
    assert esl_log[-1] == "Alert sent to server about GNSS loss event"
    assert any("diagnostics" in l.lower() or "reboot" in l.lower() for l in gnss_log + esl_log)

    # Print for debug/review (optional)
    print("Embedded Service Layer log:", esl_log)
    print("GNSS Component log:", gnss_log)
    print("Latest alert:", latest_alert)

# Optionally, add a negative test to ensure only GNSS is rebooted (not entire device/module)
def test_no_device_or_module_reboot_on_gnss_loss(setup_environment):
    esl, gnss_component, server_app = setup_environment
    esl.simulate_gnss_coverage_loss()
    logs = esl.get_log()
    # Simulate that comms module/device is never rebooted due to GNSS loss
    assert not any("device rebooted" in log or "module rebooted" in log for log in logs)

```
---

**How to Use/Customize:**
- Place as tests/test_esl_gnss_coverage_loss_handling.py.
- Replace mocks with your real device, ESL, GNSS and alert APIs.
- Integrate with real logs, event monitors, and cloud/server hooks if available.
- Run with:
  ```bash
  pytest tests/test_esl_gnss_coverage_loss_handling.py
  ```
- Coverage:
  - Diagnostics and GNSS-receiver-only reboot upon loss.
  - Alert with context.
  - Proper logging and traceability.
  - No device/module-level reboots triggered by GNSS loss.
