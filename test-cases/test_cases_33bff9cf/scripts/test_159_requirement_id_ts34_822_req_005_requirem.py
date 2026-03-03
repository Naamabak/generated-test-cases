```python
# File: tests/test_n1_counter_and_cbr1_reset_on_registration.py

"""
Test Case for:
Requirement ID : TS.34_8.2.2_REQ_005

Requirement:
- UE internal counter/timer related to N1 SHALL be reset when UE successfully registers on CS & PS domain.
- C-BR-1 SHALL not be reset.

References:
- GSMA TS.34 v8.0, Section 8.2.2, Requirement TS.34_8.2.2_REQ_005
- TS.34_8.2.2_REQ_003, TS.34_8.2.2_REQ_004 (counter/timer behavior)
- 3GPP TS 24.008, TS 23.122 (CS/PS registration)
"""

import pytest

# --- MOCK IMPLEMENTATION --- 
# Replace with real device API, diagnostic CLI, or hardware-in-the-loop test code

class MockUE:
    """
    Mock UE/Device representing counters/timers for N1 and C-BR-1.
    Methods simulate the required behavior for registering on CS and PS.
    """

    def __init__(self):
        self.n1_counter = 0               # N1-related counter/timer (to be reset on reg)
        self.cbr1_counter = 0             # C-BR-1 counter (NOT to be reset on reg)
        self.logs = []
        self.cs_registered = False
        self.ps_registered = False

    def simulate_registration_failures(self, n1_increment, cbr1_increment):
        """Artificially increment counters to non-zero values."""
        self.n1_counter += n1_increment
        self.cbr1_counter += cbr1_increment
        self.logs.append(f"Simulated failures: N1={self.n1_counter}, C-BR-1={self.cbr1_counter}")

    def read_counters(self):
        """Return a tuple of the current (N1, C-BR-1) counter/timer values."""
        return self.n1_counter, self.cbr1_counter

    def reset_registration(self):
        """Reset CS/PS registration flags (for repeated test cycles)."""
        self.cs_registered = False
        self.ps_registered = False

    def register_on_cs_and_ps(self):
        """Simulate successful registration on both CS & PS domains."""
        self.cs_registered = True
        self.ps_registered = True
        self.logs.append("Successful registration on both CS & PS domains")
        # Requirement: Reset N1 counter/timer, retain C-BR-1
        self.n1_counter = 0
        # C-BR-1 remains unchanged

    def log_state(self):
        state = {
            'n1_counter': self.n1_counter,
            'cbr1_counter': self.cbr1_counter,
            'cs_reg': self.cs_registered,
            'ps_reg': self.ps_registered
        }
        self.logs.append(f"State: {state}")
        return state

    def reset_all(self):
        self.n1_counter = 0
        self.cbr1_counter = 0
        self.reset_registration()
        self.logs = []

    def get_logs(self):
        return self.logs[:]

# --- TEST FIXTURE ---

@pytest.fixture
def ue_device():
    ue = MockUE()
    yield ue
    ue.reset_all()

# --- TEST SCRIPT ---

@pytest.mark.parametrize("cycles", [3])
def test_n1_and_cbr1_counters_reset_on_successful_registration(ue_device, cycles):
    """
    Main test:
      - Simulate non-zero N1 and C-BR-1 counter/timer values.
      - After successful registration on CS & PS, N1 is reset, C-BR-1 unchanged.
      - Repeat for multiple cycles to confirm persistent behavior.
    """
    for cycle in range(1, cycles + 1):
        # Step 1: Simulate incrementing counters to non-zero values
        ue_device.simulate_registration_failures(n1_increment=5 * cycle, cbr1_increment=7 * cycle)

        # Step 2: Read and log counters before registration
        n1_before, cbr1_before = ue_device.read_counters()
        assert n1_before > 0 and cbr1_before > 0, \
            f"Cycle {cycle}: Precondition failed: counters not incremented!"

        ue_device.log_state()

        # Step 3: Restore normal network conditions and register on CS and PS
        ue_device.register_on_cs_and_ps()

        # Step 4: Read and log counters after successful registration
        n1_after, cbr1_after = ue_device.read_counters()
        ue_device.log_state()

        # Step 5: Check counters / timers according to requirement
        assert n1_after == 0, \
            f"Cycle {cycle}: N1-related counter/timer was NOT reset after CS+PS registration! (was {n1_before})"
        assert cbr1_after == cbr1_before, \
            f"Cycle {cycle}: C-BR-1 value was incorrectly reset (before: {cbr1_before}, after: {cbr1_after})"

        # Prepare for next cycle: reset registration, leave counters non-zero
        ue_device.reset_registration()
        # Optionally increment for next round (simulate failures)

    # Step 6: Output logs for traceability and audit
    print("--- N1 and C-BR-1 Counter Behavior Logs ---")
    for entry in ue_device.get_logs():
        print(entry)

def test_counters_reset_behavior_consistency_multiple_cycles(ue_device):
    """
    Repeat for several cycles, varying initial values,
    and confirm that C-BR-1 is never reset, N1 is always cleared after successful registration.
    """
    initial_values = [(3, 10), (17, 7), (1, 1)]
    for i, (n1_start, cbr1_start) in enumerate(initial_values, start=1):
        ue_device.n1_counter = n1_start
        ue_device.cbr1_counter = cbr1_start
        ue_device.register_on_cs_and_ps()
        n1_after, cbr1_after = ue_device.read_counters()
        assert n1_after == 0, f"Cycle {i}: N1 counter not reset"
        assert cbr1_after == cbr1_start, f"Cycle {i}: C-BR-1 changed unexpectedly"
        print(f"Cycle {i}: N1 reset, C-BR-1 preserved ({cbr1_after})")
        ue_device.reset_registration()

def test_n1_reset_and_cbr1_persistence_audit_log(ue_device):
    """
    Verifies audit/behavior logs capture correct before/after counter states and actions.
    """
    ue_device.simulate_registration_failures(n1_increment=9, cbr1_increment=12)
    ue_device.log_state()
    ue_device.register_on_cs_and_ps()
    ue_device.log_state()
    logs = ue_device.get_logs()
    assert any("Simulated failures" in l for l in logs)
    assert any("Successful registration" in l for l in logs)
    assert any("n1_counter': 0" in l for l in logs)
    print("Audit log output for test review:")
    for line in logs:
        print(line)
```
---

**Usage:**  
- Save as `tests/test_n1_counter_and_cbr1_reset_on_registration.py`.
- Replace the mock class and diagnostic logic with real device API, register monitoring, and counter/timer access commands for your system.
- Run with:
  ```bash
  pytest tests/test_n1_counter_and_cbr1_reset_on_registration.py
  ```
- The script covers simulation of failures, verification of counter/timer reset on registration, and repeated/consistent behavior as required.

Let me know if you need test hooks for real AT/diagnostic CLI or integration for device logs!