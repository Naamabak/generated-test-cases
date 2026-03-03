```python
# File: tests/test_sensor_actuator_malfunction_handling.py

"""
Test Case for:
Requirement ID : TS.34_4.0_REQ_039
Requirement: When the IoT Device Application detects that an in-built sensor or actuator malfunctions, 
it SHOULD perform diagnostics, reboot the affected hardware component, and send an alert to the IoT Server Application.

References:
- GSMA TS.34 v8.0, Section 4.0, Requirement TS.34_4.0_REQ_039
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest

# --- MOCK CLASSES (replace with hooks to live device, comms layer, and server APIs where available) ---

class MockIoTServerApp:
    """Simulate the IoT Server Application receiving alerts."""
    def __init__(self):
        self.received_alerts = []

    def receive_alert(self, alert):
        self.received_alerts.append(alert)

    def get_last_alert(self):
        return self.received_alerts[-1] if self.received_alerts else None

    def clear(self):
        self.received_alerts.clear()


class MockIoTDeviceApp:
    """
    Simulate IoT Device Application with in-built sensor/actuator,
    diagnosic/reboot routines and alerting to a server.
    """
    def __init__(self, server):
        self.server = server
        self.sensors = {
            "sensor_A": {"status": "ok", "malfunction": False, "diagnosed": False, "rebooted": False},
            "actuator_X": {"status": "ok", "malfunction": False, "diagnosed": False, "rebooted": False}
        }
        self.device_rebooted = False  # Whole device reboot (should NOT happen)
        self.com_module_rebooted = False  # Comm module reboot (should NOT happen)
        self.logs = []

    def induce_malfunction(self, hw_id):
        """Simulate a detectable malfunction on a sensor/actuator."""
        if hw_id in self.sensors:
            self.sensors[hw_id]["malfunction"] = True
            self.logs.append(f"Malfunction detected on {hw_id}")

    def monitor_and_respond(self):
        """Device app checks for malfunctions and takes action per requirement."""
        for hw_id, hw in self.sensors.items():
            if hw["malfunction"]:
                # Step 3: Perform diagnostics
                hw["diagnosed"] = True
                self.logs.append(f"Diagnostics performed on {hw_id}")
                # Step 4: Targeted reboot of only the affected component
                hw["rebooted"] = True
                self.logs.append(f"Component {hw_id} rebooted")
                # Step 5: Alert transmission
                alert = {
                    "event": "hw_malfunction",
                    "component": hw_id,
                    "diagnostic": "performed",
                    "action": "rebooted",
                    "status": "malfunction_detected_and_recovered"
                }
                self.server.receive_alert(alert)
                self.logs.append(f"Alert sent for {hw_id}: {alert}")
                # Reset malfunction flag after handling
                self.sensors[hw_id]["malfunction"] = False

    def reboot_device(self):
        """(Should NOT be called in normal requirement flow)"""
        self.device_rebooted = True
        self.logs.append("WHOLE DEVICE REBOOTED")

    def reboot_com_module(self):
        """(Should NOT be called in normal requirement flow)"""
        self.com_module_rebooted = True
        self.logs.append("COMM MODULE REBOOTED")

    def get_logs(self):
        return list(self.logs)

    def reset(self):
        for k in self.sensors:
            self.sensors[k] = {
                "status": "ok", "malfunction": False, "diagnosed": False, "rebooted": False
            }
        self.device_rebooted = False
        self.com_module_rebooted = False
        self.logs.clear()

# --- FIXTURES ---

@pytest.fixture
def iot_server():
    server = MockIoTServerApp()
    yield server
    server.clear()

@pytest.fixture
def iot_device_app(iot_server):
    app = MockIoTDeviceApp(iot_server)
    yield app
    app.reset()

# --- TEST CASE ---

def test_sensor_actuator_malfunction_handling(iot_device_app, iot_server):
    """
    TS.34_4.0_REQ_039: Test handling of sensor/actuator malfunction,
    with diagnostics, targeted reboot, and alert/logging.
    """

    # Step 1: Simulate a malfunction on sensor_A
    iot_device_app.induce_malfunction("sensor_A")
    # Step 2: Trigger application response (simulate periodic monitor/check)
    iot_device_app.monitor_and_respond()

    # Step 3: Verify diagnostics executed on sensor_A
    sensor = iot_device_app.sensors["sensor_A"]
    assert sensor["diagnosed"], "Diagnostics not performed on sensor_A."

    # Step 4: Only the affected component rebooted, not the whole device/module
    assert sensor["rebooted"], "Only affected sensor should be rebooted."
    assert not iot_device_app.device_rebooted, "Full device reboot should NOT occur."
    assert not iot_device_app.com_module_rebooted, "Comm module reboot should NOT occur."

    # Step 5: Alert is sent to IoT Server Application
    last_alert = iot_server.get_last_alert()
    assert last_alert is not None, "No alert sent to server upon malfunction."
    assert last_alert["component"] == "sensor_A"
    assert last_alert["diagnostic"] == "performed"
    assert last_alert["action"] == "rebooted"
    assert last_alert["status"] == "malfunction_detected_and_recovered"

    # Step 6: Logs contain all relevant actions
    logs = iot_device_app.get_logs()
    expected = [
        "Malfunction detected on sensor_A",
        "Diagnostics performed on sensor_A",
        "Component sensor_A rebooted",
        "Alert sent for sensor_A"
    ]
    for fragment in expected:
        assert any(fragment in log for log in logs), f"'{fragment}' not found in logs"
    
    print("Device/application logs:", logs)
    print("Server alerts:", iot_server.received_alerts)

# Optionally, negative test to ensure no whole-device or comm module reboot occurs
def test_malfunction_does_not_reboot_full_device_or_comm_module(iot_device_app):
    iot_device_app.induce_malfunction("actuator_X")
    iot_device_app.monitor_and_respond()
    assert not iot_device_app.device_rebooted, "Device should not be rebooted for actuator malfunction!"
    assert not iot_device_app.com_module_rebooted, "Comms module should not be rebooted for actuator malfunction!"
```

---

**How to Use/Customize:**
- Place as `tests/test_sensor_actuator_malfunction_handling.py`
- Replace mocks with your device/control system or hardware API if available.
- Replace monitoring code with real logs, diagnostics, and alert checking.
- Run with:  
  ```bash
  pytest tests/test_sensor_actuator_malfunction_handling.py
  ```
- Covers: diagnostics, targeted reboot, alert, and no excessive resets, with all actions logged and verifiable.