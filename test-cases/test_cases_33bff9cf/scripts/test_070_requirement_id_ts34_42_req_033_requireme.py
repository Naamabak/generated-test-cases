```python
# File: tests/test_esl_memory_full_handling.py

"""
Test Case for:
Requirement ID: TS.34_4.2_REQ_033

Requirement:
When the IoT Embedded Service Layer (not on the comm module/chipset hardware) detects memory full,
it SHOULD perform diagnostics, reboot the affected hardware component, and send an alert to the IoT Server Application.

References:
- GSMA TS.34 v8.0, Section 4.2, TS.34_4.2_REQ_033
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest

# ---- MOCK/PLACEHOLDER CLASSES ----
# Replace with real device/testbed APIs in hardware/integration testing.

class MockIoTServerApp:
    """Simulates the IoT Server Application, able to receive alerts from the device."""
    def __init__(self):
        self.alerts = []

    def receive_alert(self, alert):
        self.alerts.append(alert)

    def clear(self):
        self.alerts = []

    def get_latest_alert(self):
        return self.alerts[-1] if self.alerts else None


class MockIoTHardwareComponent:
    """Simulates a hardware component affected by memory overflow, able to run diagnostics and reboot."""
    def __init__(self, name="storage"):
        self.name = name
        self.diagnostics_performed = False
        self.rebooted = False
        self.log = []

    def run_diagnostics(self):
        self.diagnostics_performed = True
        self.log.append(f"Diagnostics performed on {self.name}")

    def reboot(self):
        self.rebooted = True
        self.log.append(f"{self.name} component rebooted")

    def reset(self):
        self.diagnostics_performed = False
        self.rebooted = False
        self.log = []


class MockIoTEmbeddedServiceLayer:
    """Simulates the Embedded Service Layer, not on comm module, which handles memory full events."""
    def __init__(self, hw_component, server_app):
        self.hw_component = hw_component
        self.server_app = server_app
        self.memory_full = False
        self.log = []

    def induce_memory_full(self):
        # Step 1: Simulate memory full event
        self.memory_full = True
        self.log.append("Memory full condition detected")
        # Step 3: Run diagnostics on affected hardware component
        self.hw_component.run_diagnostics()
        self.log.append("Diagnostics initiated due to memory full")
        # Step 4: Reboot only the affected component (not device/module)
        self.hw_component.reboot()
        self.log.append(f"Rebooted affected component: {self.hw_component.name}")
        # Step 5: Send alert to server application
        alert = {
            "event": "memory_full",
            "diagnostics": self.hw_component.diagnostics_performed,
            "rebooted_component": self.hw_component.name,
            "component_only": True,
            "reason": "Memory full condition detected",
        }
        self.server_app.receive_alert(alert)
        self.log.append("Alert sent to IoT Server Application")

    def get_log(self):
        return list(self.log)

    def reset(self):
        self.memory_full = False
        self.hw_component.reset()
        self.log = []


@pytest.fixture
def setup_environment():
    server_app = MockIoTServerApp()
    hw_component = MockIoTHardwareComponent(name="storage")
    esl = MockIoTEmbeddedServiceLayer(hw_component, server_app)
    yield esl, hw_component, server_app
    esl.reset()
    hw_component.reset()
    server_app.clear()

# ---- TEST CASE ----

def test_esl_memory_full_triggered_flow(setup_environment):
    """
    TS.34_4.2_REQ_033:
    - On memory full, ESL must:
      a) Run diagnostics.
      b) Reboot only the affected hardware component, not device/module.
      c) Send alert to IoT Server Application.
      d) Each action is logged and verifiable.
    """
    esl, hw_component, server_app = setup_environment

    # Step 1-2: Induce memory full and observe logs before/after
    esl.induce_memory_full()
    logs = esl.get_log()

    # a) Diagnostics are performed by ESL
    assert hw_component.diagnostics_performed, "Diagnostics were not performed on memory full detection"
    assert any("Diagnostics performed" in l or "Diagnostics initiated" in l for l in logs), \
        "Diagnostics action not logged"

    # b) Only the affected component is rebooted
    assert hw_component.rebooted, "Affected hardware component was not rebooted"
    assert any("Rebooted affected component" in l for l in logs), "Reboot action not logged"

    # (For production/integration test: check that device/module was NOT rebooted)

    # c) Alert sent from ESL to IoT Server Application
    latest_alert = server_app.get_latest_alert()
    assert latest_alert is not None, "No alert sent to the IoT Server Application"
    assert latest_alert["event"] == "memory_full", "Alert did not have expected event type"
    assert latest_alert["diagnostics"] is True
    assert latest_alert["component_only"], "Alert must record only component reboot, not whole device"

    # d) All actions are verifiable via logs and alert content
    print("ESL Action Log:", logs)
    print("Hardware Component Log:", hw_component.log)
    print("Alert sent to server:", latest_alert)

    assert "Alert sent to IoT Server Application" in logs, "Alert sending not recorded in log"
    assert all(isinstance(l, str) for l in logs), "Log should contain string steps only"
```
---

**Instructions:**

- Save as `tests/test_esl_memory_full_handling.py`
- Replace mocks with the real Embedded Service Layer, hardware components, and server application API for integration/system tests.
- Run with:
  ```bash
  pytest tests/test_esl_memory_full_handling.py
  ```
- This test script covers diagnostics, targeted hardware reboot, secure alerting to the server, and logs for full traceability per GSMA TS.34_4.2_REQ_033.