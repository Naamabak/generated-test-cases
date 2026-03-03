```python
# File: tests/test_lapi_and_ewt_support.py

"""
Test Case for:
Requirement ID : TS.34_9.2_REQ_001

Requirement:
The IoT Device SHALL support Low Access Priority Indicated (LAPI) and Extended Wait Timer (EWT).
The device must correctly signal LAPI in RRC/NAS messages and comply with EWT when signaled by the network.
References:
- GSMA TS.34 v8.0, Section 9, TS.34_9.2_REQ_001
- 3GPP TS 36.331 (RRC signaling), TS 24.301 (NAS signaling)
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf, p.58
"""

import pytest

# --- Mock/Placeholder Classes (substitute with integration to real module, SIM/UICC, test network in prod/lab) ---

class MockNetwork:
    def __init__(self):
        self.lapi_supported = True
        self.ewt_supported = True
        self.last_reject_ewt = None
        self.logs = []

    def configure_reject_with_ewt(self, ewt_value):
        """Configures the next access reject to carry an EWT value (in seconds)."""
        self.last_reject_ewt = ewt_value

    def receive_access_request(self, lapi_flag):
        """Returns a reject with EWT (if set), and logs LAPI flag observed in message."""
        self.logs.append(f"Received device access request with LAPI flag: {lapi_flag}")
        if self.last_reject_ewt is not None:
            ewt = self.last_reject_ewt
            self.last_reject_ewt = None
            return {"rejected": True, "ewt": ewt}
        return {"rejected": False, "ewt": None}

    def get_logs(self):
        return list(self.logs)

    def reset(self):
        self.last_reject_ewt = None
        self.logs = []

class MockIoTDevice:
    """Simulates LAPI/EWT behavior for the IoT Device."""
    def __init__(self, network, lapi_config_input="SIM"):
        self.network = network
        self.lapi_active = True  # LAPI indicator enabled (default, can also be forced by SIM/internal/config)
        self.lapi_config_input = lapi_config_input
        self.last_received_ewt = None
        self.next_access_allowed = 0  # Simulated "time", seconds
        self.current_time = 0
        self.log = []
        self.ran_last_with_lapi = None

    def set_lapi_config(self, mode, active=True):
        self.lapi_config_input = mode
        self.lapi_active = active
        self.log.append(f"LAPI configured from {mode}: {'ENABLED' if active else 'DISABLED'}")

    def advance_time(self, seconds):
        self.current_time += seconds

    def attempt_access(self):
        """Attempt network access; LAPI flag set according to configuration."""
        if self.current_time < self.next_access_allowed:
            self.log.append(f"Access request at {self.current_time}s: BLOCKED by EWT, must wait {self.next_access_allowed - self.current_time}s")
            return False

        resp = self.network.receive_access_request(self.lapi_active)
        self.ran_last_with_lapi = self.lapi_active

        if resp["rejected"] and resp["ewt"]:
            self.last_received_ewt = resp["ewt"]
            self.next_access_allowed = self.current_time + resp["ewt"]
            self.log.append(f"Rejected with EWT={resp['ewt']}s at {self.current_time}s. Next allowed at {self.next_access_allowed}s.")
            return False
        self.log.append(f"Access request at {self.current_time}s: ACCEPTED (LAPI: {self.lapi_active})")
        return True

    def get_log(self):
        return list(self.log)

    def get_last_lapi_flag(self):
        return self.ran_last_with_lapi

    def get_last_ewt(self):
        return self.last_received_ewt

    def reset(self):
        self.lapi_active = True
        self.last_received_ewt = None
        self.next_access_allowed = 0
        self.current_time = 0
        self.log = []
        self.ran_last_with_lapi = None

# --- Fixtures ---

@pytest.fixture
def network():
    return MockNetwork()

@pytest.fixture
def device(network):
    d = MockIoTDevice(network)
    yield d
    d.reset()
    network.reset()

# --- Test Script ---

@pytest.mark.parametrize("lapi_mode", ["SIM", "internal", "default"])
@pytest.mark.parametrize("ewt_val", [10, 30, 60])
def test_lapi_signaling_and_extended_wait_timer(device, network, lapi_mode, ewt_val):
    """
    - Device signals LAPI in RRC/NAS messages (for all supported configuration input modes)
    - Network reject with EWT, device waits per timer before re-trying, re-attempt is blocked if premature
    - Logs/traces confirm LAPI indication and EWT handling per 3GPP/GSMA requirements
    """
    # Step 1: Configure LAPI via possible input methods
    device.set_lapi_config(lapi_mode, active=True)
    # Step 2: Attach/initiate to the network
    # Step 3-4: Initiate network connection - should set LAPI flag as configured
    network.configure_reject_with_ewt(ewt_val)
    result = device.attempt_access()
    assert not result, "First access must be rejected (EWT set by network in reject)."
    logs = device.get_log()
    net_logs = network.get_logs()
    assert any("LAPI configured" in l for l in logs)
    assert net_logs and f"LAPI flag: True" in net_logs[-1], "LAPI indicator not present in network message log"

    # Step 5-6: Device must wait the EWT before attempting again; should block re-attempts within EWT window
    for t in range(1, ewt_val):
        device.advance_time(1)
        result = device.attempt_access()
        assert not result, f"Access attempt at t+{t}s should be blocked, must wait full EWT"

    # Jump to EWT expiry, now access allowed
    device.advance_time(ewt_val)
    result = device.attempt_access()
    assert result, "Access request should be allowed after EWT expiry"
    logs = device.get_log()
    assert any(f"EWT={ewt_val}" in l for l in logs), f"EWT={ewt_val}s not reflected in log"

    # Step 7/8: Repeat with different EWTs and LAPI input types
    print(f"LAPI/EWT logs for mode={lapi_mode}, EWT={ewt_val}\n", device.get_log())

def test_lapi_and_ewt_behavior_consistency(device, network):
    """Test multiple cycles and confirm device consistently signals LAPI and honors EWT for various values."""
    # LAPI ON, try for a few values/EWTs
    for ewt_val in [5, 15, 45]:
        network.configure_reject_with_ewt(ewt_val)
        device.set_lapi_config("SIM", True)
        device.attempt_access()
        for _ in range(ewt_val - 2):
            device.advance_time(1)
            assert not device.attempt_access()
        device.advance_time(2)
        assert device.attempt_access()
        device.reset()
    print("Consistency test log for LAPI/EWT:", device.get_log())

def test_no_lapi_when_config_disabled(device, network):
    """If LAPI is disabled, flag should not be set in requests/logs."""
    device.set_lapi_config("internal", False)
    network.configure_reject_with_ewt(20)
    device.attempt_access()
    net_logs = network.get_logs()
    assert any("LAPI flag: False" in l for l in net_logs), "LAPI flag should be False when feature is off"

def test_ewt_operation_with_sim_and_internal_config_modes(device, network):
    for mode in ["SIM", "internal", "default"]:
        device.set_lapi_config(mode, True)
        for ewt_val in [30, 120]:
            network.configure_reject_with_ewt(ewt_val)
            device.attempt_access()
            device.advance_time(ewt_val)
            assert device.attempt_access()
            device.reset()
    print("Tested EWT with all LAPI config input modes.")

def test_logs_and_protocol_traces(documentation):
    """Logs and protocol traces can be presented as evidence of LAPI and EWT support."""
    # Integrated system: supplementary test, document logs/traces for audit.
    # For this mock, print/log would be equivalent.
    print("Consult device and network logs/protocol traces for evidence, per TS.34_9.2_REQ_001.")

```
---

**Instructions/Usage:**

- Save this as `tests/test_lapi_and_ewt_support.py`.
- Replace the mocks with integration to real device, SIM/UICC, and network/protocol analyzer/trace collection for full conformance testing in CI or lab.
- This script asserts LAPI flag/signaling and EWT waiting, with repeat runs and checks as required by GSMA TS.34_9.2_REQ_001 and 3GPP v10+.
- Use `pytest` to run:
  ```bash
  pytest tests/test_lapi_and_ewt_support.py
  ```
- Print/logging is included for audit, traceability, and evidence gathering. Adjust, expand, or wire to live interfaces as required for your lab or deployment.

Let me know if you need extra coverage for protocol trace validation, ASN.1/PDU decode, or SIM/UICC scripting!