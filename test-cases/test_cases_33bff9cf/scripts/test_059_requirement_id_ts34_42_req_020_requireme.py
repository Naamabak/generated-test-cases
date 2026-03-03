```python
# File: tests/test_esl_low_power_mode.py

"""
Test Case for:
Requirement ID : TS.34_4.2_REQ_020

Requirement:
When an IoT Device Application does not need to perform regular data transmissions
and can tolerate some latency for its IoT Service, the IoT Embedded Service Layer
SHOULD implement a ‘low power’ mode where the device and its Communication Module
is effectively powered down between data transmissions.

References:
- GSMA TS.34 v8.0, Section 4.2, Requirement TS.34_4.2_REQ_020
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf (page 20, 61–62)
- GSMA White Paper “Improving Energy Efficiency for Mobile IoT” [18]
"""

import pytest
import time

# --------------------
# MOCK IMPLEMENTATION
# --------------------
# Replace these with actual device/ESL APIs/loggers/meters for integration/lab tests

class MockCommModule:
    """Simulate a Communication Module that can enter and resume from low power state."""
    def __init__(self):
        self.state = "active"   # "active" | "low_power"
        self.state_log = []

    def enter_low_power(self, t=None):
        self.state = "low_power"
        self.state_log.append(("low_power", t or time.time()))
    
    def activate(self, t=None):
        self.state = "active"
        self.state_log.append(("active", t or time.time()))

    def get_state(self):
        return self.state

    def get_state_log(self):
        return self.state_log[:]

    def reset(self):
        self.state = "active"
        self.state_log = []

class MockIoTEmbeddedServiceLayer:
    """
    Simulate ESL supporting low power mode and transmission resumption.
    """
    def __init__(self, comm_module, idle_timeout=120):
        self.comm_module = comm_module
        self.idle_timeout = idle_timeout   # time (seconds) to enter low power after tx
        self.last_tx_time = None
        self.esl_log = []
        self.current_time = [time.time()]  # Use list for easy simulation time advancing

    def now(self):
        return self.current_time[0]

    def advance_time(self, seconds):
        self.current_time[0] += seconds

    def operate_latency_tolerant(self):
        # Step 1: Initial transmission
        self.send_data("first payload")
        # Step 2: Wait (simulate long idle interval)
        self._check_idle_state()
        # Step 3: ESL/Comm module should enter low power after idle timeout
        self.advance_time(self.idle_timeout + 1)
        self._check_idle_state()
        # Step 4: Simulated trigger for next scheduled transmission
        self.send_data("second payload")
        self._check_idle_state()
        # Step 6: Device/module should return to low power again after another idle interval
        self.advance_time(self.idle_timeout + 1)
        self._check_idle_state()

    def send_data(self, payload):
        # Activate on demand if not already
        if self.comm_module.get_state() != "active":
            self.comm_module.activate(self.now())
            self.esl_log.append({"event": "comm_module_resume", "at": self.now(), "payload": payload})
        # Simulate transmission
        self.last_tx_time = self.now()
        self.esl_log.append({"event": "tx", "payload": payload, "at": self.now()})

    def _check_idle_state(self):
        # Enter low power if past idle timeout since last tx
        if self.last_tx_time is None:
            return
        if self.comm_module.get_state() == "active" and self.now() - self.last_tx_time > self.idle_timeout:
            self.comm_module.enter_low_power(self.now())
            self.esl_log.append({"event": "comm_module_low_power", "at": self.now()})

    def get_log(self):
        return list(self.esl_log)

    def reset(self):
        self.comm_module.reset()
        self.last_tx_time = None
        self.esl_log = []
        self.current_time = [time.time()]

@pytest.fixture
def esl_and_comm_module():
    comm = MockCommModule()
    esl = MockIoTEmbeddedServiceLayer(comm_module=comm, idle_timeout=120)
    yield esl, comm
    esl.reset()
    comm.reset()

# --------------------
# THE TEST CASE
# --------------------

def test_esl_low_power_mode_operation(esl_and_comm_module):
    """
    TS.34_4.2_REQ_020:
    - Device/CommModule should enter low power between infrequent (latency-tolerant) transmissions.
    - Resume transmission on demand, log/observe power state transitions, and ensure return to
      low power after each tx.
    """
    esl, comm = esl_and_comm_module

    # Step 1-6: Operate device in latency-tolerant scenario and simulate behavior across idle/active/low-power states
    esl.operate_latency_tolerant()
    log = esl.get_log()
    state_log = comm.get_state_log()

    # a) Device and CommModule enter low power between transmissions
    assert any(event[0] == "low_power" for event in state_log), \
        "Comm module never entered low power state between transmissions"

    # b) Network signalling during these periods is minimal
    # (in this mock, 'tx' events are only during transmission, so no log during low power)
    tx_times = [e["at"] for e in log if e["event"] == "tx"]
    low_power_times = [e[1] for e in state_log if e[0] == "low_power"]
    # No 'tx' between 'low_power' and next 'active'
    for i in range(len(low_power_times)):
        after_lp = None
        for (st, t) in state_log:
            if st == "active" and t > low_power_times[i]:
                after_lp = t
                break
        period_txs = [tx for tx in tx_times if low_power_times[i] < tx < (after_lp or (low_power_times[i] + 3600))]
        assert len(period_txs) == 0, (
            "Unexpected network activity (tx) during low power period detected"
        )

    # c) Device/module resume, transmit, and then return to low power
    transitions = [e[0] for e in state_log]
    assert transitions.count("active") >= 2 and transitions.count("low_power") >= 2, \
        "Expected multiple transitions between active<->low_power"

    # d) All behaviors observable in log/state logs
    print("ESL activity log:", log)
    print("CommModule power/log state:", state_log)
    print("Transitions sequence:", transitions)
```

---

**Instructions:**
- Save as `tests/test_esl_low_power_mode.py`.
- Replace mocks with real hardware APIs, logs, or metering as needed.
- Run with:
  ```bash
  pytest tests/test_esl_low_power_mode.py
  ```
- The script covers all key points:
    - Idle → Enter low power,
    - Wake → Resume for scheduled/evented transmission,
    - Confirm power/network events and logs are consistent with GSMA TS.34_4.2_REQ_020 low power requirement.
