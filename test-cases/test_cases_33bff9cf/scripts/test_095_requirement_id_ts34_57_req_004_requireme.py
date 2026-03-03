```python
# File: tests/test_comm_module_sim_lock.py

"""
Test Case for:
Requirement ID : TS.34_5.7_REQ_004

Requirement:
The IoT Communications Module SHALL implement a SIM lock function which allows the IoT Device to be locked to
a specific UICC or range of UICCs. The state of the lock SHALL be remotely configurable.

References:
- GSMA TS.34 v8.0, Section 5.7, TS.34_5.7_REQ_004
- 3GPP TS 31.102 (UICC functionality and access conditions)
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest

# --- MOCK CLASSES (Replace with actual device/module API and testbed hooks in deployment) ---

class MockSIMLockModule:
    """
    Simulates an IoT Comm Module with SIM lock/unlock functionality and remote config.
    """
    def __init__(self):
        self.allowed_uiccs = set()      # Set of allowed UICC IDs
        self.sim_lock_active = False
        self.current_uicc = None
        self.operational = False
        self.log = []
        self.remote_mgmt_api = self._remote_mgmt_handler

    def insert_uicc(self, uicc_id):
        self.current_uicc = uicc_id
        self.log.append(f"UICC inserted: {uicc_id}")
        self._evaluate_uicc_lock_status()

    def power_on(self):
        # On power-on, UICC is checked for lock
        if self.current_uicc is None:
            self.operational = False
            self.log.append("Power on: No UICC present")
        else:
            self._evaluate_uicc_lock_status()
            self.log.append(f"Power on: UICC {self.current_uicc}, operational: {self.operational}")

    def power_off(self):
        self.operational = False
        self.log.append("Device powered off")

    def remove_uicc(self):
        self.log.append(f"UICC removed: {self.current_uicc}")
        self.current_uicc = None

    def _evaluate_uicc_lock_status(self):
        # Device operates only if lock is not active or UICC is in allowed set
        if not self.sim_lock_active:
            self.operational = True
        elif self.current_uicc in self.allowed_uiccs:
            self.operational = True
            self.log.append(f"SIM lock active: UICC {self.current_uicc} is allowed")
        else:
            self.operational = False
            self.log.append(f"SIM lock active: UICC {self.current_uicc} is NOT allowed, operation blocked")

    def _remote_mgmt_handler(self, action, data=None):
        """
        Simulate remote (OTA or platform) API to configure lock state and allowed UICCs.
        Supported actions: 'lock', 'unlock', 'set_allowed'
        """
        if action == "lock":
            self.sim_lock_active = True
            self.log.append("SIM lock remotely activated")
        elif action == "unlock":
            self.sim_lock_active = False
            self.log.append("SIM lock remotely deactivated")
        elif action == "set_allowed" and data:
            self.allowed_uiccs = set(data)
            self.log.append(f"SIM lock: allowed UICCs/set remotely configured: {self.allowed_uiccs}")
        else:
            self.log.append(f"Unknown remote management command: {action}")

        # Re-evaluate lock status if UICC is inserted
        if self.current_uicc:
            self._evaluate_uicc_lock_status()

    def get_log(self):
        return list(self.log)

    def get_operational_status(self):
        return self.operational

    def reset(self):
        self.__init__()

# --- TEST FIXTURE ---

@pytest.fixture
def sim_lock_module():
    module = MockSIMLockModule()
    yield module
    module.reset()

# --- TEST CASE ---

def test_sim_lock_functionality_and_remote_configuration(sim_lock_module):
    """
    TS.34_5.7_REQ_004:
    - SIM lock can be remotely enabled/disabled, UICC allowlist remotely configured
    - Device operation allowed/blocked as required by SIM lock and inserted UICC
    - Logs confirm enforcement and remote configurability
    """

    # Test setup: two test UICCs (one allowed, one blocked)
    uicc_allowed = "SIM_AAAAAAAAA"
    uicc_denied = "SIM_BBBBBBBBB"
    third_uicc =  "SIM_CCCCCCCCC"  # for group/range test

    # Step 1: Remotely activate SIM lock and set allowed UICC(s)
    sim_lock_module.remote_mgmt_api("lock")
    sim_lock_module.remote_mgmt_api("set_allowed", [uicc_allowed])

    # Step 2: Insert allowed UICC, power on, expect normal operation
    sim_lock_module.insert_uicc(uicc_allowed)
    sim_lock_module.power_on()
    assert sim_lock_module.get_operational_status(), "Device did not operate with allowed UICC!"
    log = sim_lock_module.get_log()
    assert any("SIM lock active: UICC" in l and "is allowed" in l for l in log)

    # Step 3: Swap for denied UICC, power on, expect blocked operation
    sim_lock_module.power_off()
    sim_lock_module.remove_uicc()
    sim_lock_module.insert_uicc(uicc_denied)
    sim_lock_module.power_on()
    assert not sim_lock_module.get_operational_status(), "Device should block operation with denied UICC!"
    log = sim_lock_module.get_log()
    assert any("SIM lock active: UICC" in l and "NOT allowed" in l for l in log)

    # Step 4: Remotely change lock state to unlocked, verify device operates for any UICC
    sim_lock_module.remote_mgmt_api("unlock")
    sim_lock_module.power_off()
    sim_lock_module.power_on()
    assert sim_lock_module.get_operational_status(), "Device not operational after SIM lock deactivation!"
    # Lock again, set new allowed group/range, verify only those are accepted
    sim_lock_module.remote_mgmt_api("lock")
    sim_lock_module.remote_mgmt_api("set_allowed", [uicc_allowed, third_uicc])
    sim_lock_module.remove_uicc()
    sim_lock_module.insert_uicc(third_uicc)
    sim_lock_module.power_on()
    assert sim_lock_module.get_operational_status(), "Device should operate with new allowed UICC after OTA config"
    sim_lock_module.remove_uicc()
    sim_lock_module.insert_uicc(uicc_denied)
    sim_lock_module.power_on()
    assert not sim_lock_module.get_operational_status(), "Device should be blocked with non-listed UICC after OTA config"

    # Step 5: Check logs for all remote config, lock, unlock, and enforcement events
    log = sim_lock_module.get_log()
    assert any("SIM lock remotely activated" in l for l in log)
    assert any("SIM lock remotely deactivated" in l for l in log)
    assert any("allowed UICCs/set remotely configured" in l for l in log)
    assert any("is allowed" in l or "NOT allowed" in l for l in log)

    # Print all log entries for trace/audit
    print("SIM Lock event log:", log)

```

---

**Instructions:**
- Save as `tests/test_comm_module_sim_lock.py`
- Replace mocks and test-UICC IDs with your real module’s remote management API, UICC enumeration, and log/monitoring interface for integration/hardware tests.
- Run with:
  ```bash
  pytest tests/test_comm_module_sim_lock.py
  ```
- The script asserts correct SIM lock behavior, remote configurability, OTA/unlock, and logs all events for audit and integration compliance.