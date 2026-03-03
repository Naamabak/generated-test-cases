```python
# File: tests/test_esl_priority_handling.py

"""
Test Case for:
Requirement ID: TS.34_4.2_REQ_018

Requirement:
Each time there is a need to send data over the mobile network the IoT Embedded Service Layer SHOULD
take into account priority information (importance/urgency) communicated by the IoT Device Application,
distinguishing between data needing immediate transmission and delay-tolerant data—such that the network
is not negatively impacted (including scheduling for off-peak).

References:
- GSMA TS.34 v8.0, Section 4.2, TS.34_4.2_REQ_018
- TS.34_4.1_REQ_003 (priority classification)
"""

import pytest
from datetime import datetime, timedelta
import random

# ---- MOCK CLASSES (Replace with your real application/service layer/harness for live/integration) ----

class MockOperatorPolicy:
    """
    Configures MNO priority policy and off-peak hours.
    For this test:
        - peak: 8:00 to 20:00
        - off-peak: 20:00 to 8:00
    """
    def __init__(self, peak_start=8, peak_end=20, offpeak_enabled=True):
        self.peak_start = peak_start
        self.peak_end = peak_end
        self.offpeak_enabled = offpeak_enabled

    def is_peak_hour(self, dt):
        return self.peak_start <= dt.hour < self.peak_end

    def is_offpeak_hour(self, dt):
        return not self.is_peak_hour(dt)


class MockIoTEmbeddedServiceLayer:
    """
    Simulates the Embedded Service Layer handling data prioritization and scheduling/aggregation.
    """
    def __init__(self, operator_policy):
        self.operator_policy = operator_policy
        self.transmit_log = []  # Each entry: (timestamp, payload, priority, send_time)
        self.aggregation_buffer = []
        self.last_time = datetime(2024, 7, 1, 0, 0, 0)  # Start of a simulated day

    def receive_from_app(self, payload, priority, event_time=None):
        """
        Receives data and priority information from the IoT Device Application.
        Priority: 'instantaneous' or 'delay_tolerant'
        """
        event_time = event_time or self.last_time
        if priority == "instantaneous":
            # Urgent: transmit immediately
            self._transmit(payload, priority, event_time)
        elif priority == "delay_tolerant":
            # Delay-tolerant: aggregate or schedule for off-peak
            if self.operator_policy.offpeak_enabled and self.operator_policy.is_peak_hour(event_time):
                # Schedule for nearest off-peak in buffer
                self.aggregation_buffer.append((payload, priority, event_time))
            else:
                # Off-peak now or no operator policy: send now, with aggregation if any
                self._flush_aggregation(event_time)
                self._transmit(payload, priority, event_time)
        else:
            raise ValueError("Unknown priority type")

    def _flush_aggregation(self, send_time):
        if self.aggregation_buffer:
            # Aggregate all buffered payloads for off-peak send
            payloads = [item[0] for item in self.aggregation_buffer]
            payload = f"AGGREGATED:{','.join(payloads)}"
            send_time_actual = send_time
            self.transmit_log.append((send_time_actual, payload, "delay_tolerant", send_time_actual))
            self.aggregation_buffer = []

    def advance_time(self, hours=1):
        # Simulates the passage of time for scheduling tests
        self.last_time = self.last_time + timedelta(hours=hours)
        # If we're now in off-peak, flush any buffered delay-tolerant data
        if self.operator_policy.is_offpeak_hour(self.last_time):
            self._flush_aggregation(self.last_time)

    def get_transmit_log(self):
        # Returns the log with each sent data: (timestamp, payload, priority, send_time)
        return list(self.transmit_log)

    def reset(self):
        self.transmit_log.clear()
        self.aggregation_buffer = []
        self.last_time = datetime(2024, 7, 1, 0, 0, 0)

# ---- FIXTURES ----

@pytest.fixture
def operator_policy():
    return MockOperatorPolicy(peak_start=8, peak_end=20, offpeak_enabled=True)

@pytest.fixture
def esl(operator_policy):
    layer = MockIoTEmbeddedServiceLayer(operator_policy)
    yield layer
    layer.reset()

# ---- TEST CASES ----

def test_esl_handles_priority_and_offpeak_scheduling(esl, operator_policy):
    """
    - High-priority (instantaneous) data is sent immediately.
    - Delay-tolerant data is aggregated or delayed for off-peak as per operator MNO policy.
    - No excessive network concentration in peak periods.
    """

    # Step 1: Trigger high-priority data events during peak and off-peak
    # Peak hour: 9:00
    time_peak = datetime(2024, 7, 1, 9, 0, 0)
    esl.receive_from_app("emergency_event", "instantaneous", event_time=time_peak)

    # Step 2: Immediate transmission for instantaneous
    log = esl.get_transmit_log()
    assert log[-1][1] == "emergency_event"
    assert log[-1][2] == "instantaneous"

    # Step 3: Trigger delay-tolerant data during peak hours, should buffer
    esl.receive_from_app("batch_telemetry_1", "delay_tolerant", event_time=time_peak)
    esl.receive_from_app("batch_telemetry_2", "delay_tolerant", event_time=time_peak)

    # Step 4: Advance time into off-peak (after 20:00), triggers buffered send
    esl.advance_time(hours=12)  # Move to 21:00 (off-peak)
    log = esl.get_transmit_log()
    aggregated_found = False
    for entry in log:
        if entry[1].startswith("AGGREGATED:"):
            chunks = entry[1].split(':', 1)[1].split(',')
            assert "batch_telemetry_1" in chunks and "batch_telemetry_2" in chunks
            assert entry[2] == "delay_tolerant"
            aggregated_found = True
    assert aggregated_found, "Buffered delay-tolerant data not aggregated and sent during off-peak."

    # Step 5: Trigger more events in off-peak, should send instantly (no need to buffer)
    time_offpeak = esl.last_time
    esl.receive_from_app("nightly_upload", "delay_tolerant", event_time=time_offpeak)
    log = esl.get_transmit_log()
    found = False
    for entry in log:
        if entry[1] == "nightly_upload" and entry[2] == "delay_tolerant":
            found = True
            break
    assert found, "Delay-tolerant data during off-peak should be sent immediately, not buffered."

    # Step 6: Edge case under congested (peak) network, ensure prioritization
    # (simulate by checking that all 'instantaneous' messages are never delayed/buffered)
    esl.receive_from_app("alarm_flood", "instantaneous", event_time=time_peak)
    latest_entry = esl.get_transmit_log()[-1]
    assert latest_entry[1] == "alarm_flood" and latest_entry[2] == "instantaneous", \
        "High-priority message not sent immediately during peak."

    print("Transmit log:", esl.get_transmit_log())

def test_esl_priority_logic_consistent_in_multiple_cycles(esl, operator_policy):
    """
    Repeat the logic across multiple cycles and varying times; behavior is consistent.
    """
    # Cycle 1: Peak hour inputs (delay-tolerant, should aggregate)
    time_peak = datetime(2024, 7, 1, 10, 0, 0)
    for i in range(3):
        esl.receive_from_app(f"batch_peak_{i}", "delay_tolerant", event_time=time_peak)
    # No send yet…
    assert not any("AGGREGATED:" in entry[1] for entry in esl.get_transmit_log())

    # Cycle 2: Advance into off-peak and check buffered data is sent/aggregated
    esl.advance_time(hours=12)  # to 22:00
    log = esl.get_transmit_log()
    agg_entry = [entry for entry in log if "AGGREGATED:" in entry[1]]
    assert agg_entry and all(f"batch_peak_{i}" in agg_entry[0][1] for i in range(3))

    # Cycle 3: High-priority, new period
    time_day2 = datetime(2024, 7, 2, 9, 0, 0)
    esl.receive_from_app("urgent_day2", "instantaneous", event_time=time_day2)
    log2 = esl.get_transmit_log()
    assert any(entry[1] == "urgent_day2" and entry[2] == "instantaneous" for entry in log2)

    print("Multi-cycle transmit log:", log2)

```

---

**How to Use/Customize:**
- Save this as `tests/test_esl_priority_handling.py`.
- Replace mocks with real IoT Device App and Embedded Service Layer API/integration if available.
- `pytest tests/test_esl_priority_handling.py` to run in your test environment.

**Coverage:**
- Verifies urgent vs. delay-tolerant prioritization and scheduling.
- Checks aggregation and off-peak transmission.
- Confirms logic is consistent over multiple cycles/periods.
- Prints logs for debug or human review.

Let me know if you'd like this adapted to your APIs or with more advanced timing/network event logic!