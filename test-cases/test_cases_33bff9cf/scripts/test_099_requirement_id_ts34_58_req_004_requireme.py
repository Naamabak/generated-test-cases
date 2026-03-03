```python
# File: tests/test_comm_module_time_resynchronisation.py

"""
Test Case for:
Requirement ID : TS.34_5.8_REQ_004

Requirement:
The IoT Communications Module SHOULD support “time resynchronisation” via remote and local connection.

References:
- GSMA TS.34 v8.0, Section 5.8, Requirement TS.34_5.8_REQ_004
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
- Time sync procedures within device management protocols (e.g. OMA DM Section 5.10)
"""

import pytest
from datetime import datetime, timedelta

# --------------- MOCKS / PLACEHOLDERS BEGIN ---------------
# Replace these for integration with your real module/device API or testbed interaction

class MockIoTCommModule:
    """
    Simulates an IoT Communication Module with time resynchronisation via remote and local commands.
    """
    def __init__(self, module_id="mod-001"):
        self.device_id = module_id
        self.clock = datetime.utcnow()
        self.log = []
        self.last_resync_source = None  # "remote" | "local"

    def set_clock(self, dt):
        """Manually set the module clock (to simulate error)."""
        self.clock = dt
        self.log.append(f"Clock manually set to {dt}")

    def get_clock(self):
        return self.clock

    def resync_time_remote(self, reference_time):
        """Resync triggered by OTA/management system."""
        self.clock = reference_time
        self.last_resync_source = 'remote'
        self.log.append(f"Remote time resync: {reference_time}")

    def resync_time_local(self, reference_time):
        """Resync triggered by local user, CLI, or UI."""
        self.clock = reference_time
        self.last_resync_source = 'local'
        self.log.append(f"Local time resync: {reference_time}")

    def get_log(self):
        return list(self.log)

    def reset(self):
        self.clock = datetime.utcnow()
        self.log = []
        self.last_resync_source = None

# --------------- FIXTURES ---------------

@pytest.fixture
def comm_module():
    m = MockIoTCommModule(module_id="test01")
    yield m
    m.reset()

# --------------- TEST CASE ---------------

def test_time_resynchronisation_via_remote_and_local(comm_module):
    """
    TS.34_5.8_REQ_004:
    Both remote and local resynchronisation must update the module's clock to the correct reference time.
    Each event must be logged or otherwise observable.
    """

    # Use a known reference time (simulate e.g., NTP or lab time source)
    reference_time = datetime.utcnow()

    # Step 1: Set the module's system clock to a wrong value (simulate drift -6 hours)
    incorrect_time_1 = reference_time - timedelta(hours=6)
    comm_module.set_clock(incorrect_time_1)
    assert abs((comm_module.get_clock() - reference_time).total_seconds()) > 3500, \
        "Module clock should be substantially incorrect before sync"

    # Step 2: Send remote resynchronisation command, module should correct its time
    comm_module.resync_time_remote(reference_time)
    delta_remote = abs((comm_module.get_clock() - reference_time).total_seconds())
    assert delta_remote < 2, f"Remote resync failed, clock delta: {delta_remote:.2f}s"
    assert comm_module.last_resync_source == 'remote'
    assert any("Remote time resync" in entry for entry in comm_module.get_log())

    # Step 3: Set clock wrong again (simulate drift +4 hours)
    incorrect_time_2 = reference_time + timedelta(hours=4)
    comm_module.set_clock(incorrect_time_2)
    assert abs((comm_module.get_clock() - reference_time).total_seconds()) > 3500, \
        "Module clock should again be incorrect for local sync test"

    # Step 4: Initiate local resynchronisation (user/CLI/physical)
    comm_module.resync_time_local(reference_time)
    delta_local = abs((comm_module.get_clock() - reference_time).total_seconds())
    assert delta_local < 2, f"Local resync failed, clock delta: {delta_local:.2f}s"
    assert comm_module.last_resync_source == 'local'
    assert any("Local time resync" in entry for entry in comm_module.get_log())

    # Step 5: Both resync events in log and no residual errors remain
    log = comm_module.get_log()
    assert all(
        abs((reference_time - comm_module.get_clock()).total_seconds()) < 2
        for event in ["Remote time resync", "Local time resync"]
    ), "No deviation should remain after either resync"
    assert "Clock manually set" in log[0] or "Clock manually set" in log[2]
    assert any("Remote time resync" in entry for entry in log)
    assert any("Local time resync" in entry for entry in log)

    # Print the action/log sequence for audit/debug
    print("Resynchronisation event log:", log)

```
---

**Instructions:**  
- Save as `tests/test_comm_module_time_resynchronisation.py`.
- Replace the mock class with your real module/device API if available.
- Reference time and result tolerances may be adjusted for hardware clock drift or lab delays.
- Run with:  
  ```bash
  pytest tests/test_comm_module_time_resynchronisation.py
  ```

**Covers:**  
- Both local and remote resync paths.
- Error setup and recovery for clock.
- Full log/audit for verification.
- Strict mapping to GSMA TS.34_5.8_REQ_004 requirement.