```python
# File: tests/test_esl_time_resynchronisation.py

"""
Test Case for:
Requirement ID : TS.34_4.2_REQ_025

Requirement:
The IoT Embedded Service Layer SHOULD support “time resynchronisation” via remote and local connection.

References:
- GSMA TS.34 v8.0, Section 4.2, Requirement TS.34_4.2_REQ_025
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
- TS.34_4.0_REQ_025 (related Application requirement)
"""

import pytest
from datetime import datetime, timedelta

# ---------- MOCK IMPLEMENTATION (Replace with device API/integration for real/testbed environment) ----------

class MockIoTEmbeddedServiceLayer:
    """
    Simulates the IoT Embedded Service Layer with local and remote time resynchronisation capability.
    All time actions and adjustments are logged for verification.
    """
    def __init__(self, device_id="iotdev001"):
        self.device_id = device_id
        self.clock = datetime.utcnow()
        self.log = []
    
    def set_clock(self, clock_value):
        """Manually sets device clock - for simulating drift/misconfiguration."""
        self.clock = clock_value
        self.log.append({
            "event": "manual_set",
            "new_clock": self.clock,
        })
    
    def get_clock(self):
        """Return current device clock."""
        return self.clock

    def resync_time_remote(self, reference_time):
        """Simulate a remote-triggered time resynchronisation, e.g., via OTA/remote API."""
        self.clock = reference_time
        self.log.append({
            "event": "time_resync_remote",
            "new_clock": self.clock,
        })

    def resync_time_local(self, reference_time):
        """Simulate a local (manual/physical) time resynchronisation."""
        self.clock = reference_time
        self.log.append({
            "event": "time_resync_local",
            "new_clock": self.clock,
        })

    def get_log(self):
        return list(self.log)

    def reset(self):
        self.clock = datetime.utcnow()
        self.log = []

# ---------- FIXTURES ----------

@pytest.fixture
def esl():
    esl = MockIoTEmbeddedServiceLayer()
    yield esl
    esl.reset()

# ---------- TEST SCRIPT ----------

def test_esl_time_resynchronisation_remote_and_local(esl):
    """
    TS.34_4.2_REQ_025
    - Supports clock resynchronisation via both remote and local interfaces.
    - Each method must set clock accurately and be logged.
    """
    # Use a known accurate reference time
    accurate_ref_time = datetime.utcnow()

    # Step 1: Set the IoT Device's clock to an incorrect value (simulate drift)
    wrong_time_1 = accurate_ref_time - timedelta(hours=6)
    esl.set_clock(wrong_time_1)
    assert abs((esl.get_clock() - accurate_ref_time).total_seconds()) > 3500, (
        "Device clock not significantly drifted after manual set."
    )
    
    # Step 2: Initiate a remote resynchronisation and verify correction
    esl.resync_time_remote(accurate_ref_time)
    new_time_remote = esl.get_clock()
    delta_remote = abs((new_time_remote - accurate_ref_time).total_seconds())
    assert delta_remote < 2, (
        f"After remote sync, clock mismatch: {delta_remote} seconds."
    )
    assert any(e["event"] == "time_resync_remote" for e in esl.get_log()), "Remote resync not logged."

    # Step 3: Alter device clock again (simulate new drift)
    wrong_time_2 = accurate_ref_time + timedelta(hours=4)
    esl.set_clock(wrong_time_2)
    assert abs((esl.get_clock() - accurate_ref_time).total_seconds()) > 3500, (
        "Device clock not significantly drifted after 2nd manual set."
    )

    # Step 4: Initiate a local resynchronisation and verify correction
    esl.resync_time_local(accurate_ref_time)
    new_time_local = esl.get_clock()
    delta_local = abs((new_time_local - accurate_ref_time).total_seconds())
    assert delta_local < 2, (
        f"After local sync, clock mismatch: {delta_local} seconds."
    )
    assert any(e["event"] == "time_resync_local" for e in esl.get_log()), "Local resync not logged."

    # Step 5: Both logs should show the sequence and time adjustments with proper method tags
    logs = esl.get_log()
    remote_log = next((e for e in logs if e["event"] == "time_resync_remote"), None)
    local_log  = next((e for e in logs if e["event"] == "time_resync_local"), None)
    assert remote_log is not None and local_log is not None, "Missing method-specific resync logs."
    assert remote_log["new_clock"] == accurate_ref_time and local_log["new_clock"] == accurate_ref_time

    # (Optional) Print logs for reporting/debug
    print("ESL Time Resync Log:", logs)

```

---

**Usage/Integration**:
- Add this as `tests/test_esl_time_resynchronisation.py`.
- Replace the mock class with your actual Embedded Service Layer/device API in your system.
- All test steps and assertions correspond directly to the GSMA TS.34_4.2_REQ_025 time resync requirement and pass criteria.
- Run with:
  ```bash
  pytest tests/test_esl_time_resynchronisation.py
  ```

**Coverage:**
- Both remote and local resync paths.
- Accurate/atomic update check.
- Full method/actuation logging for each resync.
- Verifies sequence, accuracy, and auditable event records.