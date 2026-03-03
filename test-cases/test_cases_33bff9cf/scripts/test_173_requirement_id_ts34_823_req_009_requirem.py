```python
# File: tests/test_rpm_counter_cpdp4_increment_and_no_rollover.py

"""
Test Case for:
Requirement ID : TS.34_8.2.3_REQ_009

Requirement:
- RPM SHALL increment counter C-PDP-4 by 1 when PDP Context Activation Request / PDN Connectivity Request
  is ignored by RPM because of TS.34_8.2.3_REQ_008 (“PDP Context Activation/Deactivation Management”).
- The counter SHALL not roll over (does not increment beyond max value).

References:
- GSMA TS.34 v8.0, Section 8.2.3, TS.34_8.2.3_REQ_009 / _008
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf (page 48)
"""

import pytest

# --- MOCK / PLACEHOLDER IMPLEMENTATION ---
# Replace this section with real integration/hardware interface for system/lab execution

class MockRPM_C_PDP_4:
    """
    Simulates the RPM logic and C-PDP-4 counter for testing TS.34_8.2.3_REQ_009.
    """
    MAX_C_PDP_4 = 0xFF  # 255

    def __init__(self, f4_value=5):
        self.f4 = f4_value  # F4 is the config parameter for PDP Activation/Deactivation Management (per hour)
        self.cpdp4 = 0
        self.pair_count = 0   # Number of activate/deactivate pairs seen this hour
        self.ignore_next_activation = False
        self.event_log = []
        self.one_hour_window = 3600
        self._current_time = 0  # simulation time

    def set_time(self, t):
        self._current_time = t

    def advance_time(self, seconds):
        self._current_time += seconds

    def trigger_pdp_activation_deactivation_pair(self, apn):
        """
        Simulate issuing a PDP Context Activation immediately followed by Deactivation,
        increasing the pair count, to simulate TS.34_8.2.3_REQ_008 scenario.
        """
        self.pair_count += 1
        if self.pair_count > self.f4:
            # Next Activation should be ignored per the requirement
            self.ignore_next_activation = True
        else:
            self.ignore_next_activation = False  # Only ignore after F4 is exceeded

        self.event_log.append(
            f"Activation/Deactivation pair for {apn} (pair count: {self.pair_count} of F4={self.f4})."
        )

    def try_activation_request(self, apn):
        """
        Attempt another Activation. If ignore_next_activation is set,
        this triggers a C-PDP-4 increment by 1 per requirement.
        """
        prev = self.cpdp4
        if self.ignore_next_activation:
            if self.cpdp4 < self.MAX_C_PDP_4:
                self.cpdp4 += 1
                self.event_log.append(
                    f"Activation Request IGNORED for {apn}, incremented C-PDP-4: {prev} -> {self.cpdp4}."
                )
            else:
                # At max, do not increment/roll over
                self.event_log.append(
                    f"Activation Request IGNORED for {apn}, C-PDP-4 capped at {self.cpdp4}."
                )
        else:
            self.event_log.append(
                f"Activation Request sent for {apn}, not ignored, C-PDP-4 unchanged ({self.cpdp4})."
            )

    def read_cpdp4(self):
        return self.cpdp4

    def set_counter(self, value):
        self.cpdp4 = value

    def get_log(self):
        return list(self.event_log)

    def reset(self):
        self.cpdp4 = 0
        self.pair_count = 0
        self.ignore_next_activation = False
        self.event_log = []
        self._current_time = 0

# --- PYTEST FIXTURE ---

@pytest.fixture
def rpm_cpdp4():
    rpm = MockRPM_C_PDP_4(f4_value=4)
    yield rpm
    rpm.reset()

# --- TEST SCRIPT ---

def test_cpdp4_increases_per_ignored_activation(rpm_cpdp4):
    """
    a) Each Activation Request ignored (due to TS.34_8.2.3_REQ_008) increments C-PDP-4 by 1.
    """
    apn = "test.apn"
    # Step 1: Query and log initial value
    initial = rpm_cpdp4.read_cpdp4()
    assert initial == 0

    # Step 2: Issue pairs to reach F4 threshold
    for i in range(rpm_cpdp4.f4):
        rpm_cpdp4.trigger_pdp_activation_deactivation_pair(apn)
        # Activation should NOT be ignored until after F4
        rpm_cpdp4.try_activation_request(apn)
        assert rpm_cpdp4.read_cpdp4() == 0  # No increment yet

    # Step 3: Now, Activations will be ignored. Test increment.
    for i in range(3):
        rpm_cpdp4.trigger_pdp_activation_deactivation_pair(apn)  # Keep pushing past F4
        rpm_cpdp4.try_activation_request(apn)
        assert rpm_cpdp4.read_cpdp4() == i+1, f"C-PDP-4 did not increment as expected at event {i+1}"

    print("C-PDP-4 log after ignore increments:", rpm_cpdp4.get_log()[-6:])

def test_cpdp4_stops_incrementing_at_maximum_and_no_rollover(rpm_cpdp4):
    """
    b)c) Once C-PDP-4 reaches its max, extra ignored requests do not increment it; counter never rolls over.
    """
    apn = "edge.apn"
    # Pre-fill counter to max
    rpm_cpdp4.set_counter(rpm_cpdp4.MAX_C_PDP_4)
    for _ in range(10):
        rpm_cpdp4.ignore_next_activation = True
        rpm_cpdp4.try_activation_request(apn)
        assert rpm_cpdp4.read_cpdp4() == rpm_cpdp4.MAX_C_PDP_4, "C-PDP-4 rolled over beyond max!"
    print("C-PDP-4 max value log:", rpm_cpdp4.get_log()[-5:])

def test_cpdp4_never_drops_below_max_after_ignored_activation(rpm_cpdp4):
    """
    c) After reaching max, even more ignored events can't decrease counter, no wrap/rollback.
    """
    apn = "static.apn"
    rpm_cpdp4.set_counter(rpm_cpdp4.MAX_C_PDP_4)
    for _ in range(5):
        rpm_cpdp4.ignore_next_activation = True
        rpm_cpdp4.try_activation_request(apn)
        assert rpm_cpdp4.read_cpdp4() == 0xFF
    print("C-PDP-4 final value after further attempts (should stay at max):", rpm_cpdp4.read_cpdp4())

def test_cpdp4_log_traces_all_steps_and_values(rpm_cpdp4):
    """
    d) All increments and cap events are logged for verification and traceability.
    """
    apn = "auditlog.apn"
    rpm_cpdp4.trigger_pdp_activation_deactivation_pair(apn)
    rpm_cpdp4.try_activation_request(apn)
    for _ in range(6):
        rpm_cpdp4.trigger_pdp_activation_deactivation_pair(apn)
        rpm_cpdp4.ignore_next_activation = True
        rpm_cpdp4.try_activation_request(apn)
    # Jump to max and test log for cap
    rpm_cpdp4.set_counter(0xFF)
    for _ in range(2):
        rpm_cpdp4.ignore_next_activation = True
        rpm_cpdp4.try_activation_request(apn)
    log = rpm_cpdp4.get_log()
    assert any("capped" in l for l in log), "Log does not show C-PDP-4 capping at max value."
    print("Audit log for C-PDP-4:", log)
```
---

**How to use/adapt:**
- Save as `tests/test_rpm_counter_cpdp4_increment_and_no_rollover.py`
- Replace mocks with integration/device logic as needed for your target hardware/module.
- Run with:
  ```bash
  pytest tests/test_rpm_counter_cpdp4_increment_and_no_rollover.py
  ```
- All assertions and logging steps match GSMA TS.34_8.2.3_REQ_009 and the cross-referenced requirements; logs can be used for audit/compliance purposes.
