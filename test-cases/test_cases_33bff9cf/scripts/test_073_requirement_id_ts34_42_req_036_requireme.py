```python
# File: tests/test_esl_lan_loss_no_reboot.py

"""
Test Case for:
Requirement ID: TS.34_4.2_REQ_036

Requirement:
When the IoT Embedded Service Layer detects that the IoT Device has lost LAN connectivity with peripheral devices,
and the LAN connectivity function is hosted on the communication module/chipset hardware, the ESL SHALL NOT reboot
the IoT Device or the communication module/chipset.

References:
- GSMA TS.34 v8.0, Section 4.2, TS.34_4.2_REQ_036
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf (p. 28)
"""

import pytest
import time
from collections import deque

# --- MOCK IMPLEMENTATION (Replace with real system/device logs and hooks in production/lab tests) ---

class MockSystemLog:
    """
    Simulates logs tracking reboot and reset events for device and module/chipset.
    """
    def __init__(self):
        self.events = deque()

    def log(self, event_type, timestamp=None):
        self.events.append((event_type, timestamp or time.time()))

    def get_reboots(self, source):
        return [evt for evt in self.events if evt[0] == f"{source}_reboot"]

    def clear(self):
        self.events.clear()


class MockIoTDeviceWithESL:
    """
    Simulates an IoT Device with an Embedded Service Layer.
    The LAN function is assumed to be hosted on the comm module/chipset.
    """
    def __init__(self, system_log):
        self.system_log = system_log
        self.lan_hosted_on_module = True
        self.lan_connected = True

    def operate_normally(self):
        # Logs normal operation start
        self.system_log.log('device_operational')
        self.system_log.log('module_operational')

    def simulate_lan_loss(self):
        # Simulate LAN loss; ESL should NOT trigger any resets
        self.lan_connected = False
        self.system_log.log('lan_connectivity_lost')

    def monitor_for_reboot_events(self, observe_window_sec=0.1):
        # Simulate monitoring for reboot events for the duration of LAN loss
        # In a real test, this would run for 30+ min; here we simulate rapid test speed-up
        start = time.time()
        while time.time() - start < observe_window_sec:
            time.sleep(0.01)  # simulate passage of time
        # Return True if any reboots occurred
        dev_reboots = self.system_log.get_reboots('device')
        module_reboots = self.system_log.get_reboots('module')
        return len(dev_reboots) > 0 or len(module_reboots) > 0

    def trigger_uncorrect_reboot(self, source):
        # Simulate a (bad) implementation that triggers a reboot for negative test
        self.system_log.log(f'{source}_reboot')

    def reset(self):
        self.lan_connected = True
        self.system_log.clear()

    def get_log(self):
        return list(self.system_log.events)

# --- FIXTURE ---

@pytest.fixture
def iot_device():
    system_log = MockSystemLog()
    device = MockIoTDeviceWithESL(system_log)
    yield device
    device.reset()

# --- TEST CASES ---

import pytest

@pytest.mark.parametrize("cycle", range(3))  # Do at least three cycles
def test_esl_lan_loss_no_device_or_module_reboot(iot_device, cycle):
    """
    TS.34_4.2_REQ_036:
    For all test cycles, ESL shall NOT trigger a reboot/reset of device/module/chipset on LAN loss condition.
    """
    # Step 1: Confirm LAN is hosted on comms module/chipset (via documentation/inspection)
    assert iot_device.lan_hosted_on_module, "LAN is not hosted on the communication module/chipset as required for this test"

    # Step 2: Run normal operation
    iot_device.operate_normally()

    # Step 3: Simulate/signal loss of LAN connectivity to peripherals
    iot_device.simulate_lan_loss()

    # Step 4: Monitor for any reboots/resets for the required observation window
    reboot_occurred = iot_device.monitor_for_reboot_events(observe_window_sec=0.05)  # short for test speed

    # Step 5: Assert that system/module uptimes are uninterrupted (no reboots)
    assert not reboot_occurred, (
        f"Test cycle {cycle+1}: ESL caused a reboot/reset of device or module after LAN loss—FAIL"
    )
    # Assert no reboot events in the log
    log = iot_device.get_log()
    assert not any(evt[0] in ('device_reboot', 'module_reboot') for evt in log), (
        f"Test cycle {cycle+1}: Reboot event logged unexpectedly: {log}"
    )
    print(f"Cycle {cycle+1}: No device/module reboot occurred (PASS) -- log: {log}")

def test_negative_control_reboot_detection(iot_device):
    """
    Negative test: Ensure the test detects if a device/module reboot is (wrongly) triggered during LAN loss.
    """
    iot_device.operate_normally()
    iot_device.simulate_lan_loss()
    iot_device.trigger_uncorrect_reboot('device')
    reboot_occurred = iot_device.monitor_for_reboot_events(observe_window_sec=0.01)
    assert reboot_occurred, "Reboot triggered but NOT detected by test—should have failed."
```

---

**How to Use**

- Place as `tests/test_esl_lan_loss_no_reboot.py`
- Replace mocks with real device, system log, or network/hardware monitoring logic for actual testbed runs.
- The main test ensures no device/module/chipset reboots occur after LAN loss, even if simulated over multiple cycles.
- Negative control ensures test will fail if a bad implementation inadvertently triggers a reboot.

**Run with:**
```bash
pytest tests/test_esl_lan_loss_no_reboot.py
```

**Coverage:**
- Each cycle confirms no resets are triggered during LAN loss (even under repeated conditions).
- All logs and simulated state changes are auditable for engineer/human review or CI reporting.
