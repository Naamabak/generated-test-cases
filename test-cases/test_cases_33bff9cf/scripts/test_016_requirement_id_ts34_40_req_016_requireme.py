```python
# File: tests/test_avoid_peak_traffic_concentration.py

"""
Test Case for:
Requirement ID: TS.34_4.0_REQ_016
Requirement: IoT Device Application SHOULD avoid concentrating network communication during peak utilisation and, if specified, prefer sending non-urgent data in off-peak hours.

References:
- GSMA TS.34 v8.0, Requirement TS.34_4.0_REQ_016 (page 26, page 70, spreading and randomisation)
"""

import pytest
import random
from datetime import datetime, timedelta

# --- MOCK / PLACEHOLDER CLASSES (Replace with integration to real device/application/logging as available) ---

class MockOperatorSchedule:
    """Defines peak and off-peak periods for testing, as provided by a Mobile Network Operator."""
    def __init__(self, peak_start_hour=8, peak_end_hour=20):
        self.peak_start = peak_start_hour
        self.peak_end = peak_end_hour

    def is_peak_hour(self, dt):
        """Return True if the datetime falls within peak usage hours."""
        return self.peak_start <= dt.hour < self.peak_end

class MockIoTDeviceApp:
    """
    Simulates an IoT Device Application capable of sending both urgent and non-urgent data,
    with logic to avoid peak-hour transmission for non-urgent data.
    """
    def __init__(self, operator_schedule):
        self.operator_schedule = operator_schedule
        self.event_log = []  # Records: (timestamp, data_type)
        self.random = random.Random(42)  # For deterministic test randomness

    def operate_for_24h(self, urgent_interval_min=60, nonurgent_interval_h=2):
        """
        Run a simulation of device operation for 24 hours.
        Urgent data: sent at fixed interval (e.g., hourly).
        Non-urgent data: sent only in off-peak, or scheduled to avoid peak.
        """
        current = datetime(2024, 6, 1, 0, 0, 0)
        end_time = current + timedelta(hours=24)
        # Schedule urgent events every hour, non-urgent every 2h
        while current < end_time:
            # Urgent events distributed regardless of peak
            self.event_log.append((current, "urgent"))
            # For non-urgent, schedule in off-peak
            if self.operator_schedule.is_peak_hour(current):
                # Attempt to delay or skew to off-peak if possible
                # e.g., randomize non-urgent transmission after peak
                next_offpeak_hour = self.operator_schedule.peak_end + self.random.randint(0, 2)
                offpeak_time = current.replace(hour=next_offpeak_hour % 24)
                # Only append if in range of test
                if offpeak_time < end_time:
                    self.event_log.append((offpeak_time, "nonurgent"))
            else:
                # Non-urgent ok to send now
                self.event_log.append((current, "nonurgent"))
            # Step ahead by 1 hour
            current += timedelta(hours=1)

    def get_event_log(self):
        """Return event log sorted by time."""
        return sorted(self.event_log, key=lambda e: e[0])


@pytest.fixture()
def operator_schedule():
    """Operator provides peak hours (8:00 to 20:00) for simulation."""
    return MockOperatorSchedule(peak_start_hour=8, peak_end_hour=20)

@pytest.fixture()
def iot_device_app(operator_schedule):
    """Provides a fresh IoT Device App instance for each test."""
    return MockIoTDeviceApp(operator_schedule)

# --- TEST ---

def test_avoid_network_concentration_on_peak(iot_device_app, operator_schedule):
    """
    TS.34_4.0_REQ_016:
    Verify the app avoids clustering non-urgent communications during peak periods,
    and prefers to transmit such traffic in off-peak hours, as specified.
    """
    # Step 1–3: Run app for 24 hours, create log of both urgent & non-urgent communication
    iot_device_app.operate_for_24h(urgent_interval_min=60, nonurgent_interval_h=2)
    events = iot_device_app.get_event_log()

    # Step 4: For each event, mark if it fell in peak or off-peak, and its type
    peak_nonurgent = []
    offpeak_nonurgent = []
    urgent_events = []
    for timestamp, data_type in events:
        if data_type == "nonurgent":
            if operator_schedule.is_peak_hour(timestamp):
                peak_nonurgent.append(timestamp)
            else:
                offpeak_nonurgent.append(timestamp)
        elif data_type == "urgent":
            urgent_events.append(timestamp)

    # Step 5: Analyze the distribution
    # a) Most non-urgent events should be sent in off-peak (not clustering in peak)
    ratio_nonurgent_offpeak = len(offpeak_nonurgent) / max(1, (len(offpeak_nonurgent) + len(peak_nonurgent)))

    assert ratio_nonurgent_offpeak >= 0.8, (
        f"Non-urgent messages not adequately shifted to off-peak. {len(offpeak_nonurgent)} of "
        f"{len(offpeak_nonurgent)+len(peak_nonurgent)} non-urgent events were off-peak."
    )

    # b) There should be no strong "bursty" cluster of non-urgent sends during peak (e.g., <20% of total non-urgent)
    assert len(peak_nonurgent) <= 0.2 * (len(offpeak_nonurgent) + len(peak_nonurgent)), (
        f"Too many non-urgent messages during peak hours: {len(peak_nonurgent)}"
    )

    # c) Urgent messages are permitted at all hours
    assert len(urgent_events) > 0

    # d) Output for reporting/visual check (can be commented in CI)
    print(f"Total events: {len(events)} | Urgent: {len(urgent_events)} | Non-urgent Off-peak: {len(offpeak_nonurgent)} | Non-urgent Peak: {len(peak_nonurgent)}")
    print("Sample Peak Nonurgent Transmission Times:", peak_nonurgent)
    print("Sample Off-peak Nonurgent Transmission Times:", offpeak_nonurgent)
```

---

**How to Use / Adapt:**
- Save as `tests/test_avoid_peak_traffic_concentration.py`.
- Replace `MockIoTDeviceApp` logic with real device/app event logging for real integration.
- Run with:
  ```bash
  pytest tests/test_avoid_peak_traffic_concentration.py
  ```
- To increase realism, randomize scheduling, fit operator-specific schedules, and use real 24h device logs.

**Covers:**
- Non-urgent traffic shifted to off-peak.
- Avoiding clustered/bursty transmission during peak.
- Explicit timestamp analysis for pass/fail assertion.
- Can be easily adapted for testbed or real logs.