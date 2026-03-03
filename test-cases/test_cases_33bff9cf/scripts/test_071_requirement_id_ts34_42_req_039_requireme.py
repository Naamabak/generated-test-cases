```python
# File: tests/test_esl_sensor_actuator_malfunction_handling.py

"""
Test Case for:
Requirement ID : TS.34_4.2_REQ_039

Requirement:
When the IoT Embedded Service Layer (ESL) detects a malfunction in an in-built sensor or actuator (not hosted on the communication module/chipset),
it SHOULD perform diagnostics, reboot only the affected hardware component, and send an alert to the IoT Server Application.

References:
- GSMA TS.34 v8.0, Section 4.2, TS.34_4.2_REQ_039
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
- Section 4.2, Fault and Recovery
"""

import pytest

# -- MOCK/PLACEHOLDER CLASSES (for live testbeds, plug into device APIs or simulation) --

class MockIoTServerApplication:
    """Simulates the IoT Server Application able to receive alerts."""
    def __init__(self):
        self.alerts = []

    def receive_alert(self, alert):
        self.alerts.append(alert)

    def get_last_alert(self):
        return self.alerts[-1] if self.alerts else None

    def clear(self):
        self.alerts.clear()

class MockInbuiltComponent:
    """Simulates an in-built sensor or actuator, capable of showing a malfunction, being diagnosed, and rebooted."""
    def __init__(self, name):
        self.name = name
        self.status = 'ok'
        self.diagnostics_performed = False
        self.rebooted = False
        self.log = []

    def malfunction(self):
        self.status = 'malfunction'
        self.log.append(f"Malfunction detected in {self.name}")

    def perform_diagnostics(self):
        self.diagnostics_performed = True
        self.log.append(f"Diagnostics performed on {self.name}")

    def reboot(self):
        self.rebooted = True
        self.log.append(f"{self.name} rebooted")

    def reset(self):
        self.status = 'ok'
        self.diagnostics_performed = False
        self.rebooted = False
        self.log = []

class MockIoTEmbeddedServiceLayer:
    """Implements ESL logic to handle sensor/actuator malfunction and recovery."""
    def __init__(self, components, server_app):
        self.components = {c.name: c for c in components}
        self.server_app = server_app
        self.log = []

    def detect_and_handle_malfunction(self, component_name):
        # Step 2: Detect malfunction
        comp = self.components[component_name]
        if comp.status == 'malfunction':
            self.log.append(f"Detected malfunction in {component_name}")
            # Step 3: Perform diagnostics
            comp.perform_diagnostics()
            self.log.append(f"Diagnostics initiated on {component_name}")
            # Step 4: Only reboot the affected component
            comp.reboot()
            self.log.append(f"Rebooted {component_name}")
            # Step 5: Send alert to server app
            alert = {
                "event": "malfunction",
                "component": component_name,
                "diagnostics": comp.diagnostics_performed,
                "rebooted": comp.rebooted,
                "details": f"Malfunction -> diagnostics+reboot on {component_name}"
            }
            self.server_app.receive_alert(alert)
            self.log.append(f"Alert sent for {component_name}: {alert}")

    def get_log(self):
        return list(self.log)

    def reset(self):
        for c in self.components.values():
            c.reset()
        self.log.clear()

# -- PYTEST FIXTURES --

@pytest.fixture
def setup_esl_and_server():
    sensor = MockInbuiltComponent("temperature_sensor")
    actuator = MockInbuiltComponent("valve_actuator")
    server_app = MockIoTServerApplication()
    esl = MockIoTEmbeddedServiceLayer([sensor, actuator], server_app)
    yield esl, sensor, actuator, server_app
    esl.reset()
    sensor.reset()
    actuator.reset()
    server_app.clear()

# -- TEST SCRIPT --

def test_esl_sensor_actuator_malfunction_handling(setup_esl_and_server):
    """
    TS.34_4.2_REQ_039:
    - Diagnostics performed for affected component
    - Only affected component is rebooted (not device/module)
    - Alert sent with correct content
    - Actions are all logged and traceable
    """
    esl, sensor, actuator, server_app = setup_esl_and_server

    # Step 1: Simulate malfunction in sensor
    sensor.malfunction()

    # Step 2-3: Let ESL detect and respond
    esl.detect_and_handle_malfunction("temperature_sensor")

    # Step 4a: Diagnostics must be performed on malfunctioning component
    assert sensor.diagnostics_performed, "Diagnostics not performed on affected sensor"

    # Step 4b: Only that sensor rebooted; actuator (other component) remains unaffected
    assert sensor.rebooted, "Malfunctioning component was not rebooted"
    assert not actuator.rebooted, "Non-affected actuator should not be rebooted"
    assert not hasattr(esl, 'device_rebooted'), "Device-level reboot should not occur"
    assert not hasattr(esl, 'module_rebooted'), "Comm module reboot should not occur"

    # Step 4c: Alert sent with detailed content, including event & recovery info
    alert = server_app.get_last_alert()
    assert alert is not None, "No alert sent to server application"
    assert alert["component"] == "temperature_sensor"
    assert alert["diagnostics"] == True
    assert alert["rebooted"] == True
    assert "Malfunction" in alert["details"]

    # Step 4d: All actions are logged by ESL and component
    log = esl.get_log()
    s_log = sensor.log
    assert any("Detected malfunction" in entry for entry in log)
    assert any("Diagnostics initiated" in entry for entry in log)
    assert any("Rebooted temperature_sensor" in entry for entry in log)
    assert any("Malfunction detected" in entry for entry in s_log)
    assert any("Diagnostics performed" in entry for entry in s_log)
    assert any("rebooted" in entry for entry in s_log)
    assert any("Alert sent" in entry for entry in log)

    # Print logs/output for audit/debug (optional)
    print("ESL log:", log)
    print("Sensor log:", s_log)
    print("Server alerts:", server_app.alerts)

def test_esl_actuator_malfunction_handling(setup_esl_and_server):
    """Repeat with actuator malfunction, confirm same correct behavior."""
    esl, sensor, actuator, server_app = setup_esl_and_server
    actuator.malfunction()
    esl.detect_and_handle_malfunction("valve_actuator")
    # Only actuator is fixed/rebooted, not the sensor or device/module
    assert actuator.diagnostics_performed
    assert actuator.rebooted
    assert not sensor.diagnostics_performed
    assert not sensor.rebooted
    alert = server_app.get_last_alert()
    assert alert["component"] == "valve_actuator"
    print("Actuator handling alert:", alert)
```
---

**Instructions:**
- Save as `tests/test_esl_sensor_actuator_malfunction_handling.py`
- Replace mocks with real API/hardware calls as needed
- Run with:
  ```
  pytest tests/test_esl_sensor_actuator_malfunction_handling.py
  ```
- The script covers all required behavior: diagnostics, targeted reboot, alert, logging, and non-affectation of other modules.

Let me know if you need it adapted to your real device environment!