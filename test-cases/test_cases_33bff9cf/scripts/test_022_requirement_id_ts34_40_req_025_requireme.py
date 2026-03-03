```python
# File: tests/test_time_resynchronisation.py

"""
Test Case for:
Requirement ID: TS.34_4.0_REQ_025
Requirement: The IoT Device Application SHOULD support “time resynchronisation” via remote and local connection.

References:
    - GSMA TS.34 v8.0, Section 4.0, TS.34_4.0_REQ_025
    - a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
    - TS.34_4.2_REQ_025 (Embedded Service Layer function)
"""

import pytest
import time
from datetime import datetime, timedelta

# ---- MOCK IMPLEMENTATION (Replace this with your real device interface or SDK) ----

class MockIoTDeviceApp:
    """
    Simulates an IoT Device Application with a system clock, remote/local time resynchronization methods,
    and log output.
    """
    def __init__(self, device_id="iotdev-001"):
        self.device_id = device_id
        self.clock = datetime.utcnow()
        self.log = []
        self.last_sync_source = None

    def set_clock(self, target_time):
        """Manually set the device clock (to simulate clock drift)."""
        self.clock = target_time
        self.log.append(f"Clock manually set to {self.clock}")

    def get_clock(self):
        """Return the current device clock value."""
        return self.clock

    def sync_time_remote(self, reference_time):
        """Simulate time resynchronization via remote command."""
        self.clock = reference_time
        self.last_sync_source = 'remote'
        self.log.append(f"Remote time sync: {self.clock}")

    def sync_time_local(self, reference_time):
        """Simulate time resynchronization via local command/UI."""
        self.clock = reference_time
        self.last_sync_source = 'local'
        self.log.append(f"Local time sync: {self.clock}")

    def get_log(self):
        return list(self.log)

    def reset(self):
        self.clock = datetime.utcnow()
        self.log.clear()
        self.last_sync_source = None

# ---- FIXTURE ----

@pytest.fixture
def device_app():
    """Yields a fresh device sim (with independently controllable clock) for each test."""
    app = MockIoTDeviceApp()
    yield app
    app.reset()

# ---- TEST CASE(S) ----

def test_time_resynchronisation_remote_and_local(device_app):
    """
    TS.34_4.0_REQ_025:
    Verify both remote and local time resynchronisations result in clock matching the accurate reference time.
    """
    # Reference: use "now" as the accurate time source
    accurate_reference_time = datetime.utcnow()

    # Step 1: Manually alter device clock to an incorrect time (drifted by -5 hours)
    incorrect_time_1 = accurate_reference_time - timedelta(hours=5)
    device_app.set_clock(incorrect_time_1)
    assert abs((device_app.get_clock() - accurate_reference_time).total_seconds()) > 3600, \
        "Device clock should initially deviate significantly."

    # Step 2: Initiate remote time resynchronisation
    device_app.sync_time_remote(accurate_reference_time)

    # Step 3: Verify device clock matches accurate reference time within a few seconds
    delta_remote = abs((device_app.get_clock() - accurate_reference_time).total_seconds())
    assert delta_remote < 2, f"Remote time sync failed (delta: {delta_remote:.2f}s)"
    assert device_app.last_sync_source == 'remote'
    assert any("Remote time sync" in e for e in device_app.get_log()), "Remote sync should be logged"

    # Step 4: Introduce a new (different) clock drift (+8 hours)
    incorrect_time_2 = accurate_reference_time + timedelta(hours=8)
    device_app.set_clock(incorrect_time_2)
    assert abs((device_app.get_clock() - accurate_reference_time).total_seconds()) > 3600, \
        "Device clock should show a new large drift before local sync."

    # Step 5: Initiate local time resynchronisation
    device_app.sync_time_local(accurate_reference_time)

    # Step 6: Verify the local reset corrected the time accurately
    delta_local = abs((device_app.get_clock() - accurate_reference_time).total_seconds())
    assert delta_local < 2, f"Local time sync failed (delta: {delta_local:.2f}s)"
    assert device_app.last_sync_source == 'local'
    assert any("Local time sync" in e for e in device_app.get_log()), "Local sync should be logged"

    # Step 7: Both methods should show successful time sync in log, and final state must be correct
    log = device_app.get_log()
    print("Device Log:", log)
    assert any("Remote time sync" in entry for entry in log)
    assert any("Local time sync" in entry for entry in log)

```

---

**Instructions:**
- Place as `tests/test_time_resynchronisation.py`.
- Replace the mock class with your actual device API or lower-layer SDK for resynchronization (if available).
- The test covers both remote ("over-the-air/OTA") and local (UI/CLI/API) resynchronization procedures.
- Adjust timing tolerances as needed for real hardware.
- Run with:
  ```bash
  pytest tests/test_time_resynchronisation.py
  ```

**Coverage:**
- Simulates clock drift.
- Verifies remote and local resync against accurate reference.
- Ensures both functionalities are logged and correct per TS.34_4.0_REQ_025.
