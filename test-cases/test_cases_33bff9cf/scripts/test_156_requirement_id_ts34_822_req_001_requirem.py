```python
# File: tests/test_rpm_operation_management_counters.py

"""
Test Case for:
Requirement ID : TS.34_8.2.2_REQ_001

Requirement:
- RPM Operation Management Counters (C-BR-1, C-R-1, C-PDP-1 to C-PDP-4) are stored in the (U)SIM.
- All functionality related to these counters SHALL be disabled if RPM parameters are not present on the (U)SIM.

References:
- GSMA TS.34 v8.0, Section 8.2.2, TS.34_8.2.2_REQ_001
- Section 8.2.4 for parameter/counter mapping
"""

import pytest

RPM_COUNTER_KEYS = ["C-BR-1", "C-R-1", "C-PDP-1", "C-PDP-2", "C-PDP-3", "C-PDP-4"]

# Placeholder/mock representing a (U)SIM card, provisioned or not with RPM parameters
class MockUSIM:
    def __init__(self, has_rpm_params):
        self.has_rpm_params = has_rpm_params
        # Counter values present in (U)SIM when RPM params are provisioned
        self.rpm_counters = {k: 0 for k in RPM_COUNTER_KEYS} if has_rpm_params else {}
        self.log = []

    def increment_counter(self, name):
        if self.has_rpm_params and name in self.rpm_counters:
            self.rpm_counters[name] += 1
            self.log.append(f"{name} incremented to {self.rpm_counters[name]}")
            return True
        self.log.append(f"{name} increment attempt failed - RPM params missing or counter unavailable")
        return False

    def read_counter(self, name):
        if self.has_rpm_params and name in self.rpm_counters:
            self.log.append(f"{name} read: {self.rpm_counters[name]}")
            return self.rpm_counters[name]
        self.log.append(f"{name} read: inactive - RPM params missing or counter unavailable")
        return "inactive"

    def reset_counters(self):
        for k in self.rpm_counters:
            self.rpm_counters[k] = 0

    def get_log(self):
        return list(self.log)

    def reset_log(self):
        self.log.clear()

# Placeholder mock for communication module interacting with (U)SIM
class MockCommModuleWithRPMCounters:
    def __init__(self, usim):
        self.usim = usim
        self.log = []

    def perform_rpm_events(self):
        # Simulate triggering events that should manipulate counters
        results = {}
        for key in RPM_COUNTER_KEYS:
            inc_result = self.usim.increment_counter(key)
            read_result = self.usim.read_counter(key)
            results[key] = (inc_result, read_result)
        self.log.extend(self.usim.get_log())
        self.usim.reset_log()
        return results

    def get_log(self):
        return list(self.log)

    def reset_log(self):
        self.log.clear()

# --- TEST FIXTURES ---

@pytest.fixture
def usim_with_rpm_params():
    return MockUSIM(has_rpm_params=True)

@pytest.fixture
def usim_without_rpm_params():
    return MockUSIM(has_rpm_params=False)

@pytest.fixture
def module_with_rpm_counters_rpm_params(usim_with_rpm_params):
    return MockCommModuleWithRPMCounters(usim_with_rpm_params)

@pytest.fixture
def module_with_rpm_counters_no_rpm(usim_without_rpm_params):
    return MockCommModuleWithRPMCounters(usim_without_rpm_params)

# --- TEST SCRIPT ---

def test_rpm_counters_active_when_usim_has_rpm_params(module_with_rpm_counters_rpm_params):
    """
    a) When the (U)SIM contains RPM parameters, all RPM Operation Management Counters 
    are stored in the (U)SIM and active (functional).
    """
    result = module_with_rpm_counters_rpm_params.perform_rpm_events()

    for counter in RPM_COUNTER_KEYS:
        inc, value = result[counter]
        assert inc is True, f"Increment of counter {counter} failed (should be available/active)."
        assert isinstance(value, int), f"Read of counter {counter} did not return int value: {value}"
        assert value == 1, f"First increment should bring {counter} to 1; got {value}"

    log = module_with_rpm_counters_rpm_params.get_log()
    print("RPM counters active/log (with RPM params present):")
    for entry in log:
        print(entry)

def test_rpm_counters_disabled_when_usim_has_no_rpm_params(module_with_rpm_counters_no_rpm):
    """
    b) When the (U)SIM does not contain RPM parameters, all RPM Operation Management Counter
    functionalities are fully disabled.
    """
    result = module_with_rpm_counters_no_rpm.perform_rpm_events()

    for counter in RPM_COUNTER_KEYS:
        inc, value = result[counter]
        assert not inc, f"Increment of counter {counter} should be disabled (got {inc})"
        assert value == "inactive", f"Read of counter {counter} should return 'inactive', got {value}"

    log = module_with_rpm_counters_no_rpm.get_log()
    print("RPM counters log (no RPM params present):")
    for entry in log:
        print(entry)

def test_rpm_counter_functionality_clearly_logged_for_both_states(
    module_with_rpm_counters_rpm_params,
    module_with_rpm_counters_no_rpm,
):
    """
    c) Logs and status outputs confirm counter activity when RPM params are present,
    and confirm all counter operations are inactive/disabled with a non-RPM (U)SIM.
    """
    # RPM PARAMS PRESENT
    module_with_rpm_counters_rpm_params.perform_rpm_events()
    log_present = module_with_rpm_counters_rpm_params.get_log()
    assert any("incremented" in l for l in log_present)
    assert any("read:" in l and "inactive" not in l for l in log_present)

    # RPM PARAMS ABSENT
    module_with_rpm_counters_no_rpm.perform_rpm_events()
    log_absent = module_with_rpm_counters_no_rpm.get_log()
    assert all("failed" in l or "inactive" in l for l in log_absent)

    print("Log for RPM param present:", log_present)
    print("Log for RPM param absent:", log_absent)
```
---

**Instructions / Usage:**
- Save as `tests/test_rpm_operation_management_counters.py`.
- Replace mocks with integration to your actual hardware APIs or diagnostic tools as needed.
- Run with:
  ```bash
  pytest tests/test_rpm_operation_management_counters.py
  ```
- All steps, structure, and assertions map directly to GSMA TS.34_8.2.2_REQ_001. 
- Print/log commands provide easy traceability for compliance evidence.