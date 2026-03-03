```python
# File: tests/test_embedded_service_layer_network_adaptation.py

"""
Test Case for:
Requirement ID : TS.34_4.2_REQ_009

Requirement:
The IoT Embedded Service Layer SHOULD be capable of adapting to changes in mobile network type and data speed at any given time,
ensuring reliable device operation and service delivery.

References:
- GSMA TS.34 v8.0, Section 4.2, Requirement TS.34_4.2_REQ_009
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest

# --- MOCK CLASS/PLACEHOLDER FOR EMBEDDED SERVICE LAYER (Replace for system integration) ---

class MockEmbeddedServiceLayer:
    """
    Simulates the IoT Embedded Service Layer, adapting to network RAT and speed changes.
    Logs how it adapts protocol use, timing, batching, or transmission intervals.
    """

    # Supported network environments/scenarios
    NETWORK_PROFILES = [
        {"rat": "LTE",    "speed": "high"},
        {"rat": "3G",     "speed": "medium"},
        {"rat": "2G",     "speed": "low"},
        {"rat": "LTE-M",  "speed": "medium"},
        {"rat": "NB-IoT", "speed": "low"},
    ]

    def __init__(self):
        self.current_network = None
        self.adaptation_log = []
        self.running = False

    def connect_to_network(self, rat_type, speed):
        """
        Context switch to a new RAT type and network speed.
        Logs all adaptations for the test.
        """
        self.current_network = {"rat": rat_type, "speed": speed}
        if speed == "high":
            self.adaptation_log.append(
                f"Switched to {rat_type} ({speed}): using standard protocol, normal TX interval."
            )
        elif speed == "medium":
            self.adaptation_log.append(
                f"Switched to {rat_type} ({speed}): reducing payload size, batching when possible."
            )
        elif speed == "low":
            self.adaptation_log.append(
                f"Switched to {rat_type} ({speed}): batching, compressing, and increasing TX interval."
            )
        else:
            self.adaptation_log.append(
                f"Switched to {rat_type} (unknown speed): fallback adaptation."
            )

    def trigger_data_flow(self):
        """Trigger a data operation (just logs the operation for demonstration)."""
        rat = self.current_network["rat"] if self.current_network else None
        self.adaptation_log.append(f"Data transmission operation (RAT={rat})")

    def get_adaptation_log(self):
        return list(self.adaptation_log)

    def reset(self):
        self.current_network = None
        self.adaptation_log = []
        self.running = False

# --- FIXTURE ---

@pytest.fixture
def esl():
    """Returns a new Embedded Service Layer for each test."""
    layer = MockEmbeddedServiceLayer()
    yield layer
    layer.reset()

# --- TEST CASES ---

@pytest.mark.parametrize("profile", MockEmbeddedServiceLayer.NETWORK_PROFILES)
def test_embedded_service_layer_adapts_to_all_rat_and_speed(esl, profile):
    """
    Verify ESL adapts to each RAT/speed profile, modifies operation, logs adaptation.
    """
    rat_type = profile["rat"]
    speed = profile["speed"]

    # Step 1: Connect to initial network type and log baseline behavior
    esl.connect_to_network(rat_type, speed)

    # Step 2: Trigger data flow to ensure system is operating in that profile
    esl.trigger_data_flow()

    # Step 3: Analyze logs and adaptation after connecting to profile
    log = esl.get_adaptation_log()
    assert any(rat_type in x for x in log), "No evidence of RAT adaptation in log"
    assert any(speed in x for x in log), "Network speed not logged in adaptation"
    # Should reference the correct type of adaptation for speed
    if speed == "high":
        assert "normal TX interval" in log[0]
    elif speed == "medium":
        assert "reducing payload" in log[0] or "batching" in log[0]
    elif speed == "low":
        assert (
            "batching" in log[0]
            and ("compress" in log[0] or "increasing TX" in log[0])
        )
    else:
        assert "fallback" in log[0]
    # Should always log a data transmission operation
    assert any("Data transmission" in x for x in log)

    print(f"Profile: {rat_type}/{speed} | Adaptation log: {log}")

def test_embedded_service_layer_handles_sequential_and_random_network_changes(esl):
    """
    Test fast transitions between random RAT types and speed profiles and see that ESL adapts each time.
    """
    import random
    transitions = random.sample(MockEmbeddedServiceLayer.NETWORK_PROFILES, len(MockEmbeddedServiceLayer.NETWORK_PROFILES))
    for profile in transitions:
        esl.connect_to_network(profile["rat"], profile["speed"])
        esl.trigger_data_flow()

    log = esl.get_adaptation_log()
    rat_mentions = [p["rat"] for p in transitions]
    found_mentions = [rat for rat in rat_mentions if any(rat in l for l in log)]
    assert len(found_mentions) == len(rat_mentions), "Not all RAT transitions logged/adapted"
    print("Sequential/random network change adaptation log:", log)

def test_embedded_service_layer_recovers_from_multiple_changes_without_errors(esl):
    """
    Ensure all transitions occur with no error, loss of function, or excessive retries.
    """
    for profile in MockEmbeddedServiceLayer.NETWORK_PROFILES:
        esl.connect_to_network(profile["rat"], profile["speed"])
        esl.trigger_data_flow()

    log = esl.get_adaptation_log()
    # Check no error or 'retry storm' present in the adaptation log
    assert not any("error" in l.lower() or "fail" in l.lower() for l in log), \
        f"Found error or failure in adaptation log: {log}"
    assert not any("retry" in l.lower() and "excess" in l.lower() for l in log)
    print("Successful, error-free adaptation transitions logged:", log)

```

---

**How to Use/Customize:**
- Save as `tests/test_embedded_service_layer_network_adaptation.py`.
- Replace the mocked class with your real Embedded Service Layer or SDK/API for integration/system test.
- Add further detailed log analysis or metrics as needed for your device/certification procedures.
- Run with:
  ```bash
  pytest tests/test_embedded_service_layer_network_adaptation.py
  ```
- All transitions and adaptation behaviors are asserted & logged for CI or lab test reporting.