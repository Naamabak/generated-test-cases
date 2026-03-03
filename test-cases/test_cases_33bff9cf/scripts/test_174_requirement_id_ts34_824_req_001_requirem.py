```python
# File: tests/test_rpm_t1_within_window.py

"""
TestCase for:
Requirement ID : TS.34_8.2.4_REQ_001

Requirement:
The value of RPM parameter T1 SHALL be within a time window of [-10%, +10%] of the average value specified in
default parameters stored in the IoT Communications Module and on the (U)SIM card.

References:
- GSMA TS.34 v8.0, Section 8.2.4, TS.34_8.2.4_REQ_001
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
- TS.34_8.2.4_REQ_010
"""

import pytest

# -------- MOCK/PLACEHOLDER IMPLEMENTATION ---------------
# Replace with integration to actual device/UICC APIs/logs in lab/production if available

class MockIoTCommModule:
    """Simulates ability to read the module's default and active T1 parameter."""
    def __init__(self, t1_default, t1_active):
        self.t1_default = t1_default   # Default value stored in firmware (seconds)
        self.t1_active = t1_active     # Current (active) T1 in use (seconds)
    def get_t1_default(self):
        return self.t1_default
    def get_t1_active(self):
        return self.t1_active

class MockUICC:
    """Simulates a UICC card holding the default T1 parameter value."""
    def __init__(self, t1_default):
        self.t1_default = t1_default
    def get_t1_default(self):
        return self.t1_default

# ------ TEST FIXTURE: Configurable for various module/UICC/defaults/actives ------
@pytest.fixture(params=[
    {"mod": 60, "uicc": 60,  "active": 60},      # exact match
    {"mod": 50, "uicc": 70,  "active": 66},      # inside window
    {"mod": 40, "uicc": 60,  "active": 53},      # inside window
    {"mod": 100, "uicc": 80, "active": 105},     # just outside upper bound (should fail)
    {"mod": 120, "uicc": 80, "active": 85},      # just outside lower bound (should fail)
], ids=[
    "exact_match",
    "in_range_higher",
    "in_range_lower",
    "out_of_range_high",
    "out_of_range_low"
])
def rpm_params_case(request):
    vals = request.param
    module = MockIoTCommModule(t1_default=vals["mod"], t1_active=vals["active"])
    uicc = MockUICC(t1_default=vals["uicc"])
    return module, uicc

# ------ TEST SCRIPT ------

def compute_window_bounds(t1_module, t1_uicc):
    """Step 2-3: Calculate average and [-10%, +10%] window."""
    t1_avg = (t1_module + t1_uicc) / 2.0
    lower = t1_avg * 0.9
    upper = t1_avg * 1.1
    return t1_avg, lower, upper

def test_t1_within_10_percent_window(rpm_params_case):
    """
    TS.34_8.2.4_REQ_001:
    The active T1 must be within [-10%, +10%] of the average of module/UICC defaults.
    """
    module, uicc = rpm_params_case

    # Step 1: Retrieve default T1 from module and UICC
    t1_module = module.get_t1_default()
    t1_uicc = uicc.get_t1_default()
    t1_active = module.get_t1_active()

    # Step 2-3: Calculate average T1 and permissible range
    t1_avg, t1_lower, t1_upper = compute_window_bounds(t1_module, t1_uicc)

    print(f"Defaults -- Module: {t1_module}, UICC: {t1_uicc}, Average: {t1_avg}")
    print(f"Allowed window: [{t1_lower:.2f}, {t1_upper:.2f}]")
    print(f"Active T1: {t1_active}")

    # Step 5: Assert active T1 within allowed window
    if t1_lower <= t1_active <= t1_upper:
        assert True    # Pass
    else:
        pytest.fail(f"Active T1 ({t1_active}) OUTSIDE allowed window [{t1_lower:.2f}, {t1_upper:.2f}] (defaults: {t1_module}, {t1_uicc})")

@pytest.mark.parametrize('mod,uicc,active,should_pass', [
    (37, 41, 39, True),
    (120, 100, 105, True),
    (53, 53, 60, False),   # Out of window (too high)
    (110, 110, 88, False), # Out of window (too low)
], ids=['ok_example', 'ok_high', 'fail_high', 'fail_low'])
def test_t1_range_with_manual_values(mod, uicc, active, should_pass):
    """
    Additional direct-value test for boundary/edge conditions.
    """
    t1_avg, lower, upper = compute_window_bounds(mod, uicc)
    msg = f"T1 active={active} | window=[{lower:.2f},{upper:.2f}] (avg={t1_avg:.2f})"
    print(msg)
    if should_pass:
        assert lower <= active <= upper, f"SHOULD PASS but failed: {msg}"
    else:
        assert not (lower <= active <= upper), f"SHOULD FAIL but passed: {msg}"

```
---

**How to use/adapt:**
- Save as `tests/test_rpm_t1_within_window.py`
- Replace the mock class logic with your device/UICC/firmware APIs or logs.
- Run with:
  ```bash
  pytest tests/test_rpm_t1_within_window.py
  ```
- This script covers all steps, edge cases, and is commented for evidence/logging. Adjust for your lab/integration harness as needed.