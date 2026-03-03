```python
# File: tests/test_rpm_counter_reset_on_ota_refresh.py

"""
Test Case for:
Requirement ID : TS.34_8.2.2_REQ_002

Requirement:
All RPM Operation Management counters SHALL be reset to 0 if “RPM parameters”
or “RPM Operational Management Counters Leak Rate” is updated by OTA, as indicated
by a REFRESH command containing a FILE LIST TLV object.

References:
- GSMA TS.34 v8.0, Section 8.2.2, TS.34_8.2.2_REQ_002
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest

# --- MOCK/PLACEHOLDER CLASSES FOR SYSTEM/EMBEDDED INTEGRATION ---

class MockRPMCounters:
    """Simulates storage and inspection of RPM Operation Management Counters."""
    def __init__(self, counter_names):
        self.counters = {name: 10 * (i + 1) for i, name in enumerate(counter_names)}  # Non-zero initial values

    def get_all(self):
        return dict(self.counters)

    def set_all(self, value):
        for k in self.counters:
            self.counters[k] = value

class MockModule:
    """
    Simulates an IoT Device/Module under test, including:
    - RPM Operation Management counters
    - Method to apply OTA updates and process REFRESH/FILE LIST TLV
    """
    def __init__(self, rpm_counter_names):
        self.rpm_counters = MockRPMCounters(rpm_counter_names)
        self.event_log = []

    def ota_update_with_file_list_refresh(self, update_target):
        """
        Simulates OTA update (for RPM params or "Leak Rate") and processes REFRESH
        with FILE LIST TLV (which should reset all counters to 0).
        """
        # update_target: 'parameters' or 'leak_rate' (just for log detail)
        self.event_log.append(f"OTA update: {update_target} (trigger REFRESH w/ FILE LIST TLV)")
        # -- In production, check REFRESH/FILE LIST TLV parsing here --
        self.rpm_counters.set_all(0)
        self.event_log.append("All RPM Operation Management counters reset to 0 on REFRESH (FILE LIST TLV)")

    def get_rpm_counters(self):
        return self.rpm_counters.get_all()

    def get_log(self):
        return list(self.event_log)

    def set_random_nonzero_counters(self):
        # Re-randomize nonzero state between rounds (for repeatability)
        for k in self.rpm_counters.counters:
            self.rpm_counters.counters[k] = 50  # Set some consistent nonzero state

@pytest.fixture
def rpm_module():
    counter_list = [
        "counter_attempts", "counter_success", "counter_leak_rate", "counter_errors"
    ]
    mod = MockModule(counter_list)
    yield mod
    # No teardown for this mock

# --- TEST SCRIPT ---

def test_rpm_counters_reset_to_zero_on_ota_param_update(rpm_module):
    """
    TS.34_8.2.2_REQ_002:
    RPM Operation Management counters should be reset to 0 if "RPM parameters" or
    "RPM Operational Management Counters Leak Rate" is updated by OTA via REFRESH
    w/ FILE LIST TLV.
    """
    # Step 1: Ensure RPM counters start with non-zero values
    init_counters = rpm_module.get_rpm_counters()
    assert all(v != 0 for v in init_counters.values()), \
        f"Counters must be non-zero for test start, got: {init_counters}"

    # Record the state before update
    print("Counter values before OTA update:", init_counters)

    # Step 2: OTA update that changes RPM parameters (simulate REFRESH with FILE LIST TLV)
    rpm_module.ota_update_with_file_list_refresh(update_target="RPM_parameters")

    # Step 3: After REFRESH, all counters should be zero
    after_refresh_1 = rpm_module.get_rpm_counters()
    assert all(v == 0 for v in after_refresh_1.values()), \
        f"After REFRESH, all counters MUST be 0 - got: {after_refresh_1}"

    print("Counter values after OTA param update & REFRESH:", after_refresh_1)

    # Step 4: For robustness, set counters nonzero again, repeat for "Leak Rate" scenario
    rpm_module.set_random_nonzero_counters()
    before_refresh_2 = rpm_module.get_rpm_counters()
    assert all(v != 0 for v in before_refresh_2.values()), \
        "For second round, all counters should be set nonzero again"

    rpm_module.ota_update_with_file_list_refresh(update_target="LeakRate")

    after_refresh_2 = rpm_module.get_rpm_counters()
    assert all(v == 0 for v in after_refresh_2.values()), \
        f"All counters should again be 0 after Leak Rate update/refresh - got: {after_refresh_2}"

    print("Counter values after OTA leak rate update & REFRESH:", after_refresh_2)

    # Step 5: Print/log step-by-step state and actions for evidence/audit
    log = rpm_module.get_log()
    print("OTA/REFRESH Test Log:")
    for entry in log:
        print("    ", entry)

@pytest.mark.parametrize("update_target", ["RPM_parameters", "LeakRate"])
def test_counters_consistently_reset_on_multiple_updates(rpm_module, update_target):
    """
    Optionally, repeat REFRESH for both update scenarios and multiple trials.
    """
    rpm_module.set_random_nonzero_counters()
    rpm_module.ota_update_with_file_list_refresh(update_target)
    assert all(v == 0 for v in rpm_module.get_rpm_counters().values()), \
        f"All counters reset to 0 after OTA update for {update_target}"

```
---

**Usage:**
- Save as `tests/test_rpm_counter_reset_on_ota_refresh.py`
- Replace the mock class with your device/OTA integration as needed.
- Run with:
  ```bash
  pytest tests/test_rpm_counter_reset_on_ota_refresh.py
  ```
- Each step and assertion maps directly to TS.34_8.2.2_REQ_002. Test covers both parameter/leak rate OTA updates, REFRESH/FILE LIST TLV, repeated behavior, and logs evidence for audit.