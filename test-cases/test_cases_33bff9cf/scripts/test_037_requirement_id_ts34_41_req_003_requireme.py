```python
# File: tests/test_priority_classification_and_comm_to_embedded_layer.py

"""
Test Case for:
Requirement ID: TS.34_4.1_REQ_003
Requirement:
Each time there is a need to send data over the mobile network the IoT Device Application SHOULD:
  - classify the priority of each communication (per Mobile Network Operator / MNO rules)
  - distinguish between 'instantaneous' and 'delay-tolerant' data
  - communicate the priority to the IoT Embedded Service Layer
  - queue/schedule for off-peak if required by MNO specification

References:
- GSMA TS.34 v8.0, Section 4.1, TS.34_4.1_REQ_003 (pages 25-26)
- TS.34_4.2_REQ_018 (Embedded Service Layer handling)
"""

import pytest

# --- MOCK CLASSES (Replace with device/SDK when running in system/lab integration) ---

class MockOperatorPolicy:
    """Defines operator priority classifications and off-peak config (for test only)."""
    def __init__(self, delay_tolerant_classification="delay_tolerant", offpeak_enabled=True):
        self.instant_classification = "instantaneous"
        self.delay_tolerant_classification = delay_tolerant_classification
        self.offpeak_enabled = offpeak_enabled  # May affect scheduling of delay-tolerant messages

class MockIoTEmbeddedServiceLayer:
    """
    Simulates the Embedded Service Layer which should receive every outgoing communication with its classified priority.
    Records all received messages with priorities for test verification.
    """
    def __init__(self):
        self.received_messages = []  # Log of (payload, priority, scheduling)
    
    def receive_message(self, payload, priority, scheduled_for=None):
        self.received_messages.append({
            "payload": payload,
            "priority": priority,
            "scheduled_for": scheduled_for
        })
    
    def get_log(self):
        return list(self.received_messages)
    
    def reset(self):
        self.received_messages.clear()

class MockIoTDeviceApp:
    """
    Simulates an IoT Device App that classifies data events and communicates with the Embedded Service Layer.
    """
    def __init__(self, embedded_sl, operator_policy):
        self.embedded_sl = embedded_sl
        self.operator_policy = operator_policy
        self.log = []

    def send_data(self, payload, kind):
        """
        kind: 'instantaneous' or 'delay_tolerant'
        - For delay_tolerant, may schedule for off-peak based on operator policy
        """
        if kind == 'instantaneous':
            priority = self.operator_policy.instant_classification
            scheduled_for = "immediate"
        elif kind == 'delay_tolerant':
            priority = self.operator_policy.delay_tolerant_classification
            # If off-peak is enabled by MNO, mark for off-peak scheduling
            scheduled_for = "off-peak" if self.operator_policy.offpeak_enabled else "immediate"
        else:
            raise ValueError("Unknown data kind: " + str(kind))

        # Log the classification
        self.log.append({
            "payload": payload,
            "classification": priority,
            "scheduled_for": scheduled_for
        })
        # Communicate with the Embedded Service Layer
        self.embedded_sl.receive_message(payload, priority, scheduled_for)
    
    def get_classification_log(self):
        return list(self.log)
    
    def reset(self):
        self.log.clear()

# --- FIXTURES ---

@pytest.fixture
def operator_policy():
    """Returns the operator's policy object."""
    # In a real integration, fetch from test configuration or operator API
    return MockOperatorPolicy(delay_tolerant_classification="delay_tolerant", offpeak_enabled=True)

@pytest.fixture
def embedded_service_layer():
    """Simulates the Embedded Service Layer log."""
    layer = MockIoTEmbeddedServiceLayer()
    yield layer
    layer.reset()

@pytest.fixture
def iot_device_app(embedded_service_layer, operator_policy):
    app = MockIoTDeviceApp(embedded_service_layer, operator_policy)
    yield app
    app.reset()
    embedded_service_layer.reset()

# --- TEST CASES ---

def test_priority_classification_and_communication(iot_device_app, embedded_service_layer, operator_policy):
    """
    Covers:
     - (a) Each outgoing data is classified by priority per operator instruction
     - (b) Classification is logged and communicated to Embedded Service Layer
     - (c) Delay-tolerant data is properly queued/scheduled for off-peak if specified
    """
    # Step 1: Trigger two types of outgoing communications
    urgent_payload = {"type": "alarm", "msg": "critical temp exceed"}
    delay_payload = {"type": "telemetry", "msg": "hourly report"}

    # a. Send instantaneous data
    iot_device_app.send_data(urgent_payload, kind="instantaneous")
    # b. Send delay-tolerant, which by policy should be scheduled for off-peak
    iot_device_app.send_data(delay_payload, kind="delay_tolerant")

    # Step 2: Check classification decisions in device log
    log = iot_device_app.get_classification_log()
    assert log[0]["classification"] == operator_policy.instant_classification
    assert log[1]["classification"] == operator_policy.delay_tolerant_classification
    # Check scheduling for off-peak on delay-tolerant
    assert log[1]["scheduled_for"] == ("off-peak" if operator_policy.offpeak_enabled else "immediate")

    # Step 3: Check if Embedded Service Layer received correct priority info for each message
    esl_log = embedded_service_layer.get_log()
    assert len(esl_log) == 2
    assert esl_log[0]["priority"] == operator_policy.instant_classification
    assert esl_log[1]["priority"] == operator_policy.delay_tolerant_classification

    # Step 4: Ensure the delay-tolerant message is queued or marked for off-peak if policy enabled
    if operator_policy.offpeak_enabled:
        assert esl_log[1]["scheduled_for"] == "off-peak"
    else:
        assert esl_log[1]["scheduled_for"] == "immediate"

    # Optional: Print logs for test visibility
    print("Device classification log:", log)
    print("Embedded Service Layer received log:", esl_log)

def test_classification_consistency_multiple_events(iot_device_app, embedded_service_layer, operator_policy):
    """
    Repeat classification and transmission multiple times to ensure consistent behavior.
    """
    for i in range(5):
        iot_device_app.send_data({"seq": i, "kind": "urgent"}, kind="instantaneous")
        iot_device_app.send_data({"seq": i, "kind": "background"}, kind="delay_tolerant")
    esl_log = embedded_service_layer.get_log()
    # Confirm there are 10 entries (5 of each kind)
    assert len(esl_log) == 10
    # Odd entries: delay_tolerant, Even: instantaneous
    priorities = [entry["priority"] for entry in esl_log]
    inst_count = priorities.count(operator_policy.instant_classification)
    delay_count = priorities.count(operator_policy.delay_tolerant_classification)
    assert inst_count == 5 and delay_count == 5

    # Check that all "delay_tolerant" are marked as off-peak if enabled
    if operator_policy.offpeak_enabled:
        for idx, entry in enumerate(esl_log):
            if entry["priority"] == "delay_tolerant":
                assert entry["scheduled_for"] == "off-peak"

    print("Classified priorites over multiple events:", priorities)

```
---
**How to use:**
- Save as `tests/test_priority_classification_and_comm_to_embedded_layer.py`
- Replace mocks with your real application, priority assignment, and API calls for Embedded Service Layer integration
- Run with:
  ```bash
  pytest tests/test_priority_classification_and_comm_to_embedded_layer.py
  ```
- The scripts:
  - Cover both instantaneous and delay-tolerant priority classification and embedding
  - Check transmission to the embedded layer and scheduling for off-peak
  - Fully covers TS.34_4.1_REQ_003 for priority/behavior assurance

Let me know if you need it adapted for your live SDK or test harness!