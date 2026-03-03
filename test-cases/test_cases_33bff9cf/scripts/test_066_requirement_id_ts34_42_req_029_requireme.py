```python
# File: tests/test_esl_higher_layer_failure_handling.py

"""
Test Case for:
Requirement ID: TS.34_4.2_REQ_029

Requirement:
The IoT Device Application SHALL check that communication issues to the server are not caused by higher layer protocols 
(such as TCP/IP, UDP, ATM) before resetting the communication module or re-establishing the RRC (radio) connection. 
Higher layer mechanisms SHALL then try to re-establish the connection with the server.

References:
- GSMA TS.34 v8.0, Section 4.2, Requirement TS.34_4.2_REQ_029
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
- TS.34_4.0_REQ_029 (functionally equivalent)
"""

import pytest

# --- MOCK IMPLEMENTATION (Replace with real device/ESL API for integration/lab test) ---

class MockIoTDeviceAppESL:
    """
    Simulates an IoT Device Application with Embedded Service Layer that:
    - Diagnoses root cause of comms failure
    - First attempts higher layer recovery before triggering module reset or RRC re-establishment
    """
    def __init__(self):
        self.log = []
        self.state = "idle"    # idle | connected | higher_layer_fail | all_down
        self.tcp_retry_limit = 3
        self.udp_retry_limit = 2
        self.tcp_retries = 0
        self.udp_retries = 0
        self.module_reset_performed = False
        self.rrc_reestablished = False

    def start_communication(self):
        self.state = "connected"
        self.log.append("Comm: Established to IoT Service Platform")

    def simulate_higher_layer_failure(self, layer="TCP"):
        self.state = "higher_layer_fail"
        self.log.append(f"Comm: Higher layer ({layer}) protocol failed")

    def attempt_higher_layer_recovery(self, layer="TCP"):
        # Try up to retry limit for specified protocol layer
        if layer == "TCP":
            for i in range(self.tcp_retry_limit):
                self.tcp_retries += 1
                self.log.append(f"TCP Recovery attempt {i+1}")
            self.log.append("TCP: All retries failed")
        elif layer == "UDP":
            for i in range(self.udp_retry_limit):
                self.udp_retries += 1
                self.log.append(f"UDP Recovery attempt {i+1}")
            self.log.append("UDP: All retries failed")
        else:
            self.log.append("Unknown protocol layer failure")
        self.state = "all_down"
        return False

    def reset_module_or_rrc(self):
        if self.state == "all_down":
            self.module_reset_performed = True
            self.rrc_reestablished = True
            self.log.append("LOWER LAYER: Module reset & RRC re-establishment performed")
        else:
            self.log.append("LOWER LAYER: [ERROR] Reset/re-establish called before higher layer recovery attempts")

    def get_log(self):
        return list(self.log)

    def reset(self):
        self.__init__()

# --- TEST FIXTURE ---

@pytest.fixture
def device_esl():
    app = MockIoTDeviceAppESL()
    yield app
    app.reset()

# --- TEST CASES ---

@pytest.mark.parametrize("fail_layer, retry_limit", [
    ("TCP", 3),
    ("UDP", 2)
])
def test_esl_higher_layer_failure_handling(device_esl, fail_layer, retry_limit):
    """
    End-to-end verification of correct sequence on comms issue per TS.34_4.2_REQ_029:
    - Attempt higher layer recovery before module/RRC reset
    - Only reset if upper layers cannot restore connectivity
    - Logs/steps confirm sequence
    """
    # Step 1: Start in normal operation
    device_esl.start_communication()

    # Step 2: Simulate higher layer protocol failure
    device_esl.simulate_higher_layer_failure(layer=fail_layer)

    # Step 3: Observe and confirm attempt to recover at higher protocol layer first
    recovered = device_esl.attempt_higher_layer_recovery(layer=fail_layer)
    assert recovered is False  # Simulated failures exhaust all retries

    # Step 4: Only after all retries exhausted, reset comms module/re-establish RRC
    device_esl.reset_module_or_rrc()

    # Step 5: Check and analyze logs for correct order and completeness
    log = device_esl.get_log()

    # Must attempt higher layer recovery BEFORE low-level reset
    higher_layer_attempts = [msg for msg in log if "Recovery attempt" in msg]
    assert len(higher_layer_attempts) == retry_limit, (
        f"Expected {retry_limit} higher layer recovery attempts, got {len(higher_layer_attempts)}"
    )
    reset_msg_index = next((i for i, msg in enumerate(log) if "LOWER LAYER: Module reset" in msg), None)
    last_recovery_index = max(i for i, msg in enumerate(log) if "Recovery attempt" in msg)
    assert reset_msg_index > last_recovery_index, "Module reset/RRC re-establishment occurred before exhausting higher layer recovery"
    assert device_esl.module_reset_performed, "Module reset not performed after higher layer recovery failed"
    assert device_esl.rrc_reestablished, "RRC re-establishment not triggered after higher layer retries failed"

    # Step 6: Confirm log contains adequate evidence for detection, recovery, escalation
    assert any("protocol failed" in msg.lower() for msg in log), "No log entry for higher layer failure"
    assert any("LOWER LAYER: Module reset & RRC re-establishment performed" in msg for msg in log), "No log entry for reset/escalation"
    print("Complete log trace:", log)

def test_no_premature_lower_layer_reset(device_esl):
    """
    Negative test: Module reset or RRC re-establishment cannot happen before higher layer attempts.
    """
    device_esl.start_communication()
    device_esl.simulate_higher_layer_failure(layer="TCP")
    # Try to reset immediately, without attempted higher layer recovery
    device_esl.reset_module_or_rrc()
    log = device_esl.get_log()
    assert "before higher layer recovery attempts" in log[-1], "Premature reset not detected/logged"

def test_repeat_for_multiple_higher_layer_failures(device_esl):
    """
    Repeat end-to-end test for multiple failure types (TCP/IP, UDP).
    """
    failure_types = ["TCP", "UDP"]
    for fail_layer in failure_types:
        device_esl.reset()
        device_esl.start_communication()
        device_esl.simulate_higher_layer_failure(layer=fail_layer)
        device_esl.attempt_higher_layer_recovery(layer=fail_layer)
        device_esl.reset_module_or_rrc()
        log = device_esl.get_log()
        assert any("LOWER LAYER: Module reset & RRC re-establishment performed" in msg for msg in log)

```

---

**Usage:**
- Save as `tests/test_esl_higher_layer_failure_handling.py`
- Replace the mocks (`MockIoTDeviceAppESL`) with your embedded service layer/device API in system/integration test.
- Run with:
  ```sh
  pytest tests/test_esl_higher_layer_failure_handling.py
  ```
- All steps, assertions, and log checks correspond directly to GSMA TS.34_4.2_REQ_029 entry/exit criteria and recovery sequence requirements.

Let me know if you need this customized for your hardware, logs, or test harness!