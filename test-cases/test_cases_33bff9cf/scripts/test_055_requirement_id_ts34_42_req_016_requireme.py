```python
# File: tests/test_esl_avoid_peak_network_concentration.py

"""
Test Case for:
Requirement ID: TS.34_4.2_REQ_016

Requirement:
The IoT Embedded Service Layer SHOULD be designed to ensure the application’s network communication activity is not concentrated during periods of high network utilisation,
and should prefer sending non-urgent data in "off-peak" hours where specified by the Mobile Network Operator.

References:
- GSMA TS.34 v8.0, Section 4.2, Requirement TS.34_4.2_REQ_016
- TS.34_4.0_REQ_016 (Application-level, similar requirement)
"""

import pytest
import random
from datetime import datetime, timedelta

# --- Mock Classes (Replace with live device/ESL integrations for real/hardware/lab tests) ---

class MockOperatorNetworkSchedule:
    """
    Defines simulated/operator-provided peak and off-peak periods.
    For this test, 
        - peak: 8:00 to 20:00 (8am to 8pm)
        - off-peak: 20:00 to next day 8:00
    """
    def __init__(self, peak_start=8, peak_end=20):
        self.peak_start = peak_start
        self.peak_end = peak_end

    def is_peak_hour(self, dt):
        return self.peak_start <= dt.hour < self.peak_end

    def is_offpeak_hour(self, dt):
        return not self.is_peak_hour(dt)

class MockIoTEmbeddedServiceLayer:
    """
    Simulates an Embedded Service Layer that schedules urgent/non-urgent data.
    - Urgent data can be sent at any hour.
    - Non-urgent data should be shifted/spread into off-peak hours whenever possible.
    """
    def __init__(self, operator_schedule):
        self.operator_schedule = operator_schedule
        self.events_log = []  # Each log: (timestamp, 'urgent'|'nonurgent')

    def operate_over_24h(self, urgent_interval_hr=1, nonurgent_interval_hr=2):
        """
        Simulates device activity for 24h with regular urgent and non-urgent data events.
        Non-urgent events try to avoid transmission during peak hours.
        """
        current = datetime(2024, 7, 1, 0, 0, 0)
        end_time = current + timedelta(hours=24)
        while current < end_time:
            # Urgent data goes through immediately
            self.events_log.append((current, 'urgent'))

            # For non-urgent, send only during off-peak; if in peak, shift to random off-peak window
            if self.operator_schedule.is_peak_hour(current):
                # Schedule next non-urgent send into upcoming off-peak slot (simulate distribution)
                offpeak_start_hour = self.operator_schedule.peak_end
                # Randomize within 2h of off-peak start for distribution
                offpeak_time = current.replace(hour=offpeak_start_hour % 24) + timedelta(
                    minutes=random.randint(0, 90)
                )
                # Only send if within this simulated day
                if offpeak_time < end_time:
                    self.events_log.append((offpeak_time, 'nonurgent'))
            else:
                # Off-peak: send non-urgent now
                self.events_log.append((current, 'nonurgent'))

            current += timedelta(hours=1)

    def get_events_log(self):
        return sorted(self.events_log, key=lambda e: e[0])


@pytest.fixture
def operator_schedule():
    return MockOperatorNetworkSchedule(peak_start=8, peak_end=20)

@pytest.fixture
def esl(operator_schedule):
    return MockIoTEmbeddedServiceLayer(operator_schedule)


# --- TEST CASE ---

def test_esl_avoids_network_concentration_on_peak(esl, operator_schedule):
    """
    TS.34_4.2_REQ_016:
    Verify the ESL spreads out communication and prefers sending non-urgent data outside peak hours,
    not clustering non-urgent comms in operator-defined peak periods.
    """
    # Step 1-3: Run embedded service layer for 24h, simulate events and logs
    esl.operate_over_24h()
    events = esl.get_events_log()

    # Step 4: Analyze event logs by timestamp and type
    nonurgent_peak = []
    nonurgent_offpeak = []
    urgent_events = []

    for timestamp, etype in events:
        if etype == "nonurgent":
            if operator_schedule.is_peak_hour(timestamp):
                nonurgent_peak.append(timestamp)
            else:
                nonurgent_offpeak.append(timestamp)
        elif etype == "urgent":
            urgent_events.append(timestamp)

    # Step 5: Assertions and pass/fail criteria

    # a) Most non-urgent events should be shifted/spread into off-peak hours
    ratio_offpeak = len(nonurgent_offpeak) / max(1, (len(nonurgent_peak) + len(nonurgent_offpeak)))
    assert ratio_offpeak >= 0.8, (
        f"Non-urgent transmissions not adequately shifted to off-peak — "
        f"{len(nonurgent_offpeak)} of {len(nonurgent_peak) + len(nonurgent_offpeak)} non-urgent were off-peak"
    )

    # b) There should be minimal clustering of non-urgent comms in peak hours (<20%)
    assert len(nonurgent_peak) <= 0.2 * (len(nonurgent_offpeak) + len(nonurgent_peak)), (
        f"Too many non-urgent messages during peak: {len(nonurgent_peak)}"
    )

    # c) Urgent data can be at any time; non-urgent should be distributed
    assert len(urgent_events) > 0

    # d) Print debug info (optional for CI/log review)
    print(
        f"Total events: {len(events)} | Urgent: {len(urgent_events)} | "
        f"Non-urgent Off-peak: {len(nonurgent_offpeak)} | Non-urgent Peak: {len(nonurgent_peak)}"
    )
    print("Times for non-urgent transmissions during peak (should be minimal):", nonurgent_peak)
    print("Times for non-urgent transmissions during off-peak:", nonurgent_offpeak)
```

---

**Instructions:**
- Save as `tests/test_esl_avoid_peak_network_concentration.py`.
- Replace the mock ESL logic with your actual device/service layer log collection or live scheduling if running on hardware/lab fleet.
- To run:
  ```bash
  pytest tests/test_esl_avoid_peak_network_concentration.py
  ```
- The script checks that non-urgent outbound communication is not clustered in operator-defined peak hours, but instead distributed or shifted to off-peak, in line with GSMA TS.34_4.2_REQ_016 and TS.34_4.0_REQ_016.

Let me know if you want this adapted for real device scheduling/event logs!