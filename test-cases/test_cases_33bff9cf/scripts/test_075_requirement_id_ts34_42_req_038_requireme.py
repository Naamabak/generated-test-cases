```python
# File: tests/test_esl_sensor_actuator_malfunction_no_reboot.py

"""
Test Case for:
Requirement ID: TS.34_4.2_REQ_038

Requirement:
When the IoT Embedded Service Layer detects that an in-built sensor or actuator malfunctions,
it SHALL NOT reboot the IoT Device or the communication module/chipset.

References:
- GSMA TS.34 v8.0, Section 4.2, Requirement TS.34_4.2_REQ_038
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest
import time

# --- MOCK CLASSES FOR TESTING ---
# Replace these mocks with actual device/ESL APIs and real system logging in integration/system test.

class MockSystemLog:
    """Collects and provides access to all device/module reboot or reset logs."""
    def __init__(self):
        self.events = []

    def log_event(self, evt, t=None):
        self.events.append((evt, t or time.time()))

    def clear(self):
        self.events.clear()

    def filter_reboots(self, source):
        """Returns all (source)_reboot events for 'device' or 'module'"""
        return [e for e in self.events if e[0] == f"{source}_reboot"]

class MockSensorActuator:
    """Simulates an in-built sensor/actuator with a fault injection interface."""
    def __init__(self, name="SENSOR_A"):
        self.name = name
        self.malfunction = False

    def induce_malfunction(self):
        self.malfunction = True

    def reset(self):
        self.malfunction = False

class MockEmbeddedServiceLayer:
    """
    Simulates the ESL, handling detection of malfunction and logging,
    but NEVER reboots the device or module (compliant design).
    """
    def __init__(self, system_log, sensor_actuator):
        self.system_log = system_log
        self.sensor_actuator = sensor_actuator
        self.event_log = []

    def run_normal_operation(self):
        """Device runs normally, no faults."""
        self.system_log.log_event('device_operational')
        self.system_log.log_event('module_operational')
        self.event_log.append("normal_operation")

    def monitor_and_handle_malfunction(self):
        """Checks for malfunction, logs event but does NOT reboot device/module."""
        if self.sensor_actuator.malfunction:
            self.event_log.append(f"malfunction_detected:{self.sensor_actuator.name}")
            self.system_log.log_event(f"malfunction_detected_{self.sensor_actuator.name}")
            # ESL performs diagnostics and alert logic as applicable (not tested here)
            # No call to reboot system/module!

    def maintain_for_observation(self, seconds=0.05):
        """Hold system in monitoring state for test duration."""
        start = time.time()
        while time.time() - start < seconds:
            time.sleep(0.001)

    def get_log(self):
        return self.event_log[:]

    def reset(self):
        self.sensor_actuator.reset()
        self.event_log = []
        self.system_log.clear()

# --- PYTEST FIXTURES ---
@pytest.fixture
def setup_device():
    log = MockSystemLog()
    sensor = MockSensorActuator(name="TEMP_SENSOR")
    esl = MockEmbeddedServiceLayer(log, sensor)
    yield esl, sensor, log
    esl.reset()
    sensor.reset()
    log.clear()

# --- TEST SCRIPT ---

@pytest.mark.parametrize("test_cycle", range(3))  # Multiple cycles for consistency
def test_sensor_actuator_malfunction_no_reboot(setup_device, test_cycle):
    """
    TS.34_4.2_REQ_038:
    ESL must NOT reboot the IoT Device or comms module when a sensor/actuator malfunctions.
    """
    esl, sensor, log = setup_device

    # Step 1: Operate under normal conditions - baseline
    esl.run_normal_operation()

    # Step 2: Induce a sensor/actuator malfunction
    sensor.induce_malfunction()

    # Step 3: Observe ESL response to malfunction
    esl.monitor_and_handle_malfunction()

    # Step 4: Maintain this state for a simulated monitoring period
    esl.maintain_for_observation(seconds=0.02)

    # Step 5: Check logs for any device or module reboots (there should be NONE)
    device_reboots = log.filter_reboots("device")
    module_reboots = log.filter_reboots("module")
    assert not device_reboots, f"Cycle {test_cycle+1}: Device rebooted unexpectedly after sensor malfunction!"
    assert not module_reboots, f"Cycle {test_cycle+1}: Module rebooted unexpectedly after sensor malfunction!"

    # Confirm malfunction was detected/logged
    evlog = esl.get_log()
    assert any("malfunction_detected" in e for e in evlog), "Malfunction detection not logged by ESL"

    # Optional: Print log for debug/review
    print(f"Cycle {test_cycle + 1}: Logs:", evlog)
    print(f"Cycle {test_cycle + 1}: System log:", log.events)

def test_negative_control_reboot_detected(setup_device):
    """
    Negative control: If ESL triggers a reboot, test should fail.
    """
    esl, sensor, log = setup_device
    esl.run_normal_operation()
    sensor.induce_malfunction()
    esl.monitor_and_handle_malfunction()
    # Simulate a (bad) implementation that triggers a device reboot:
    log.log_event("device_reboot")
    esl.maintain_for_observation(seconds=0.01)
    assert not log.filter_reboots("device"), "Reboot detected: This must FAIL as ESL is not allowed to reboot device."

```

---

**How to Use:**
- Save as `tests/test_esl_sensor_actuator_malfunction_no_reboot.py`.
- Replace mock classes with real system APIs, logs, and testbed logic for live/integration tests.
- Run with:
  ```bash
  pytest tests/test_esl_sensor_actuator_malfunction_no_reboot.py
  ```

**Coverage:**
- Ensures NO device or module reboots on sensor/actuator malfunction.
- Direct mapping to GSMA TS.34_4.2_REQ_038 entry/exit criteria, covers repeated test cycles and negative scenario.
- All logs and results are printed for review in CI/human analysis.
