```python
# File: tests/test_rpm_control_number_of_reset.py

"""
Test Case for:
Requirement ID : TS.34_8.2.2_REQ_003

Requirement:
- In permanent MM/GMM/EMM reject scenarios (see TS.34_8.2.2_REQ_006),
  RPM SHALL allow up to N1 IoT Device Application initiated software resets per hour.
- If N1 is set to 0, no software resets are allowed.
- RPM-initiated resets and user-initiated hardware resets are excluded from N1 count and always allowed.
- EMM Reject cases apply only to E-UTRAN capable devices.

References:
- GSMA TS.34 v8.0, Section 8.2.2, TS.34_8.2.2_REQ_003
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest
import time

# --- MOCK/PLACEHOLDER CLASSES (replace with integration for real module/device/firmware in lab/system tests) ---

class MockRPMResetController:
    """
    Simulates the RPM reset logic and counting per TS.34_8.2.2_REQ_003 in an IoT device/module.
    """
    def __init__(self, n1_value=3, e_utran_capable=True):
        self.n1 = n1_value  # Maximum allowed app resets per hour (settable)
        self.e_utran_capable = e_utran_capable
        self._ts_reset_attempts = []  # (timestamp, reset_type, source)
        self._track_start = time.time()
        self._one_hour = 60*60  # 1 hour in seconds
        self.log = []

    def _purge_old_attempts(self, now=None):
        now = now or time.time()
        # Keep attempts in last hour only
        self._ts_reset_attempts = [
            (ts, t, src) for ts, t, src in self._ts_reset_attempts
            if now - ts < self._one_hour
        ]

    def can_reset(self, reset_type, cause='permanent_reject', source='app'):
        """
        Checks if the reset is permissible by RPM, given type/source/N1. Logs all attempts and outcomes.
        """
        if not self.e_utran_capable and "EMM" in cause:
            self.log.append(f"Reset ({reset_type}/{source}) denied: Not E-UTRAN capable.")
            return False

        now = time.time()
        self._purge_old_attempts(now)
        # User/hardware or RPM-initiated: always allowed, never counted in N1
        if source in ('user', 'hardware'):
            self.log.append(f"User/HW reset allowed (source={source}).")
            return True
        if source == 'rpm':
            self.log.append(f"RPM initiated reset allowed and NOT counted toward N1.")
            return True
        # Application initiated (software)
        if source == 'app':
            if self.n1 == 0:
                self.log.append("Application software reset denied (N1=0)")
                return False
            app_resets = [1 for ts, typ, src in self._ts_reset_attempts if src == "app"]
            if len(app_resets) < self.n1:
                self.log.append(f"Application software reset allowed (N1={self.n1}, used={len(app_resets)})")
                return True
            else:
                self.log.append(f"Application software reset denied (N1={self.n1}, used={len(app_resets)})")
                return False
        self.log.append(f"Unknown reset source/type: {reset_type}/{source}")
        return False

    def perform_reset(self, reset_type, cause='permanent_reject', source='app'):
        """
        Attempts to perform a reset. If permitted, logs and records the reset. Returns True if reset occurs.
        """
        allowed = self.can_reset(reset_type=reset_type, cause=cause, source=source)
        if allowed:
            self._ts_reset_attempts.append((time.time(), reset_type, source))
            self.log.append(f"Reset performed: type={reset_type}, source={source}")
        else:
            self.log.append(f"Reset BLOCKED: type={reset_type}, source={source}")
        return allowed

    def resets_in_last_hour(self, source='app'):
        self._purge_old_attempts()
        return sum(1 for ts, t, src in self._ts_reset_attempts if src == source)

    def reset_controller(self, n1_value=None):
        if n1_value is not None:
            self.n1 = n1_value
        self._ts_reset_attempts.clear()
        self._track_start = time.time()
        self.log = []

    def get_log(self):
        return list(self.log)

# --- PYTEST FIXTURE ---    
@pytest.fixture
def rpm_reset_ctrl():
    ctrl = MockRPMResetController()
    yield ctrl
    ctrl.reset_controller()

# --- TEST SCRIPT ---    
def test_allowance_and_blocking_of_app_resets_per_n1(rpm_reset_ctrl):
    """
    a) System allows up to exactly N1 software resets per hour in scenario;
    b) Blocks further app resets; c) Allows user/hardware or RPM resets always.
    """
    # Step 1: Set N1=3
    rpm_reset_ctrl.reset_controller(n1_value=3)

    # Step 2-3: Trigger N1=3 app resets (should all succeed)
    for i in range(3):
        allowed = rpm_reset_ctrl.perform_reset('soft', cause='permanent_reject', source='app')
        assert allowed, f"App initiated reset #{i+1} should be allowed under N1 limit."
    # Step 4: Try additional software reset (should be denied)
    allowed = rpm_reset_ctrl.perform_reset('soft', cause='permanent_reject', source='app')
    assert not allowed, "4th app software reset within 1h must be denied (N1=3)"
    # Step 5: RPM-initiated resets should always be allowed and NOT counted
    for _ in range(5):
        allowed = rpm_reset_ctrl.perform_reset('soft', cause='permanent_reject', source='rpm')
        assert allowed, "RPM-initiated resets should not be blocked or counted in N1 limit."
    # Step 6: User/hardware resets should always be allowed and NOT counted
    for _ in range(3):
        allowed = rpm_reset_ctrl.perform_reset('hard', cause='manual', source='user')
        assert allowed, "User-initiated hardware resets should always be allowed (not counted in N1)."
    # Step 7: Set N1=0, no app resets allowed (but not blocking RPM/user/hw)
    rpm_reset_ctrl.reset_controller(n1_value=0)
    allowed = rpm_reset_ctrl.perform_reset('soft', cause='permanent_reject', source='app')
    assert not allowed, "App-initiated resets must be denied when N1=0."
    # RPM and user resets must still be allowed:
    assert rpm_reset_ctrl.perform_reset('soft', source='rpm')
    assert rpm_reset_ctrl.perform_reset('hard', source='user')
    # Step 8: Check logs for correct exclusion/inclusion logic
    logs = rpm_reset_ctrl.get_log()
    print("Reset control and allowance/blocking log:", logs)
    assert any("allowed" in l for l in logs if "rpm" in l or "user" in l)
    assert any("denied" in l for l in logs if "app" in l)
    assert sum("allowed" in l for l in logs if "app" in l) <= 3
    assert sum("allowed" in l for l in logs if "rpm" in l) >= 1

def test_emm_reject_applies_to_e_utran_only():
    """
    e) EMM reject control logic is only checked for E-UTRAN capable devices.
    """
    # Not E-UTRAN capable: resets should always be denied for EMM causes
    rpm_ctrl = MockRPMResetController(e_utran_capable=False)
    res = rpm_ctrl.perform_reset("soft", cause="EMM-PERMANENT", source="app")
    assert not res, "EMM reject-based resets must be blocked for non-E-UTRAN devices."
    print("Non-E-UTRAN control logic log:", rpm_ctrl.get_log())

def test_n1_can_be_configured_and_reset_timestamps_are_rolled():
    """
    Test that resets can be performed again after hour window rolls over
    and that N1 is configurable.
    """
    rpm_ctrl = MockRPMResetController(n1_value=1)
    rpm_ctrl.perform_reset("soft", source="app")
    # Next reset within hour should be blocked
    assert not rpm_ctrl.perform_reset("soft", source="app")

    # Simulate time passage (go 3700s later = 1h+100s)
    base_time = rpm_ctrl._track_start
    rpm_ctrl._ts_reset_attempts = [(base_time-3500, "soft", "app")]  # ~1h ago
    assert rpm_ctrl.perform_reset("soft", source="app"), "Should allow reset after 1h"
    print("N1 rolling window test log:", rpm_ctrl.get_log())
```
---

**How to use/adapt:**
- Save as `tests/test_rpm_control_number_of_reset.py`
- Replace mocks with integration to your reset control logic or logs for real device/module/system testing.
- Run:
  ```bash
  pytest tests/test_rpm_control_number_of_reset.py
  ```
- Script covers app, RPM, and user/hardware resets, logs evidence, N1 configuration, and E-UTRAN checks, as per TS.34_8.2.2_REQ_003.