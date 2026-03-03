```python
# File: tests/test_power_saving_mode_psm.py

"""
Test Case for:
Requirement ID : TS.34_9.11_REQ_001

Requirement:
The IoT Communications Module SHOULD support Power Saving Mode (PSM) as defined in 3GPP TS 23.682 Release 12,
allowing an IoT Device on LTE to reduce power consumption and signaling by entering/leaving PSM as specified.

References:
- GSMA TS.34 v8.0, Section 9.11, TS.34_9.11_REQ_001
- 3GPP TS 23.682 Release 12 (PSM operation, timer config, signaling)
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf (p. 61)
"""

import pytest
import time

# --- MOCK PLACEHOLDERS. Replace with your LTE module/AT/device/testbench interfaces.
class MockLteNetwork:
    """Simulates/exposes LTE network with PSM support."""
    def __init__(self, psm_enabled=True):
        self.psm_enabled = psm_enabled
        self.last_attach = False

    def enable_psm(self, module):
        if not self.psm_enabled:
            return False
        module.psm_capable = True
        return True

    def attach_module(self, module):
        module.attached = True
        self.last_attach = True
        return True

class MockIoTCommModule:
    """Simulates an LTE IoT module with basic PSM state and AT/DM commands."""
    def __init__(self):
        self.attached = False
        self.psm_capable = False
        self.psm_entered = False
        self.psm_timer = 0
        self.psm_idle_timer = 0
        self.signaling_log = []
        self.power_consumption_log = []
        self.psm_cycles = 0
        self.low_power_mode = False
        self.last_state_was_psm = False

    def configure_psm(self, psm_timer_s):
        self.psm_timer = psm_timer_s
        self.psm_idle_timer = psm_timer_s

    def perform_active_communication(self):
        self.signaling_log.append("Active communication (data report)")
        self.low_power_mode = False

    def idle_and_check_psm(self, seconds):
        """Simulate idle, entering PSM after timer."""
        # Immediately after idle, enter PSM
        if seconds >= self.psm_idle_timer:
            self.psm_entered = True
            self.low_power_mode = True
            self.last_state_was_psm = True
            self.signaling_log.append(f"PSM entered after idle of {seconds}s")
            self.power_consumption_log.append("Low power (PSM)")
    
    def is_psm(self):
        return self.psm_entered and self.low_power_mode

    def try_data_while_in_psm(self):
        """Module in PSM: uplink is not possible until PSM exit."""
        if self.is_psm():
            self.signaling_log.append("Data attempt blocked in PSM (uplink not possible)")
            return False
        self.signaling_log.append("Data sent (PSM not active)")
        return True

    def psm_exit(self, event="timer"):
        """Simulate exit from PSM (timer expiry or scheduled wake-up)"""
        if self.psm_entered:
            self.psm_entered = False
            self.low_power_mode = False
            self.signaling_log.append(f"Exited PSM due to {event}")
            self.psm_cycles += 1

    def confirm_no_detach_reattach(self):
        # Module stays attached (no unnecessary attach/detach in/after PSM)
        return self.attached

    def reset_state(self):
        self.psm_entered = False
        self.low_power_mode = False
        self.psm_cycles = 0
        self.signaling_log = []
        self.power_consumption_log = []
        self.last_state_was_psm = False

    def get_logs(self):
        return {
            "signaling": list(self.signaling_log),
            "power": list(self.power_consumption_log),
        }

    def get_psm_state(self):
        return self.psm_entered, self.low_power_mode

@pytest.fixture
def lte_network():
    return MockLteNetwork(psm_enabled=True)

@pytest.fixture
def module():
    return MockIoTCommModule()

def test_psm_supported_and_functional(lte_network, module):
    """
    TS.34_9.11_REQ_001:
    Complete functional coverage:
    - Configure, enter, maintain, and exit PSM while staying network-attached.
    - Validate signaling activity and low power/logs, repeated cycles.
    """

    # Step 1: Enable and validate PSM on both network and module.
    assert lte_network.enable_psm(module), "Failed to enable PSM in LTE network/module"

    # Step 2: Attach to network, configure PSM timer (e.g. 10s for test speed)
    assert lte_network.attach_module(module)
    module.configure_psm(psm_timer_s=10)
    assert module.attached and module.psm_capable

    # Step 3: Run active comm (data transmission)
    module.perform_active_communication()

    # Step 4: Wait idle (simulate), module should enter PSM
    module.idle_and_check_psm(seconds=11)
    assert module.is_psm(), "Module did not enter PSM after idle period"

    # Step 4b/5: Block comms in PSM, test uplink/downlink
    uplink_allowed = module.try_data_while_in_psm()
    assert not uplink_allowed, "Should not allow comm while in PSM"

    # Step 6: Wake up (timer expiry); PSM exit
    module.psm_exit(event="PSM timer expiry")
    assert not module.is_psm(), "PSM exit did not occur as expected"
    assert module.confirm_no_detach_reattach(), "Module did unwanted detach/reattach during PSM"

    # Step 7: Repeat with longer/shorter PSM timers for coverage
    for t in [5, 20, 15]:
        module.configure_psm(psm_timer_s=t)
        module.perform_active_communication()
        module.idle_and_check_psm(seconds=t + 1)
        assert module.is_psm(), f"Module did not enter PSM after {t+1}s idle."
        module.psm_exit(event="scheduled_wakeup")
        assert not module.is_psm()
        assert module.confirm_no_detach_reattach()
    assert module.psm_cycles >= 3

    # Step 8: Document logs for signaling reduction, state transitions, power savings
    logs = module.get_logs()
    assert any("PSM entered" in m for m in logs["signaling"])
    assert any("Low power" in m for m in logs["power"])
    assert any("Exited PSM" in m for m in logs["signaling"])
    print("PSM entry/exit and signaling log:", logs["signaling"])
    print("Power consumption states:", logs["power"])

    # Criteria (a) Module enters PSM; (b) signaling down/power low in PSM; (c) only one attach; (d) can resume after PSM; (e) logs/traces all evidence
```
---

**How to use/adapt:**  
- Save as `tests/test_power_saving_mode_psm.py`.
- Replace all mock class and method logic with your real LTE module's AT/diagnostic/testbed interface calls.
- Use your device's logs, module state APIs, network trace logs, or power consumption data to complete the traces/validation.
- Run with:
  ```bash
  pytest tests/test_power_saving_mode_psm.py
  ```
- All assertions and prints map directly to the TS.34_9.11_REQ_001 requirement, covering configuration, entry, operation, and exit from PSM, including evidence logging.
Let me know if you need test code that interacts with physical hardware (AT commands, SCPI, UART, etc.) or real network integration!