```python
# File: tests/test_data_volume_monitoring.py

"""
Requirement: TS.34_4.0_REQ_013
Description:
  - The IoT Device Application SHOULD monitor data volume sent/received in a set period,
    stop data when the threshold is exceeded (as set by IoT Service Provider), resume when the period expires,
    and send a report to the IoT Service Platform when exceeded.
  - Correct handling of edge cases, including configuration changes, network interruptions,
    reporting channel contribution, race conditions at period boundary, and simultaneous multiple breaches.
References:
  - GSMA TS.34 v8.0, Section 4.0, TS.34_4.0_REQ_013
"""

import pytest
import time
from threading import Thread, Lock
from unittest.mock import MagicMock

# ---- MOCK/PLACEHOLDER CLASSES ----

class MockIoTServicePlatform:
    """Simulates the IoT Service Platform receiving data volume breach reports."""
    def __init__(self):
        self.reports = []
        self.lock = Lock()

    def receive_report(self, report):
        with self.lock:
            self.reports.append(report)

    def get_reports(self):
        with self.lock:
            return list(self.reports)

    def clear(self):
        with self.lock:
            self.reports.clear()


class MockIoTDeviceApp:
    """
    Simulates a device application monitoring and limiting data usage,
    handling dynamic configuration, period boundaries, and reporting.
    """
    def __init__(self, service_platform):
        self.service_platform = service_platform
        self.max_volume = None           # bytes
        self.period = None               # seconds
        self.current_period_start = time.time()
        self.data_sent = 0
        self.data_received = 0
        self.blocked = False
        self.last_reported_period = None
        self.pending_report = False      # used for offline reporting
        self.reporting_channel_counted = True
        self.lock = Lock()
        self.network_online = True

    def configure(self, max_volume, period, reporting_channel_counted=True):
        """Configure or reconfigure the data limit and monitoring period."""
        with self.lock:
            self.max_volume = max_volume
            self.period = period
            self.reporting_channel_counted = reporting_channel_counted
            # On config change, reevaluate limits and possibly unblock if needed
            self._check_period(force_restart=True)

    def simulate_network_state(self, online):
        """Toggle network online/offline for testing intermittent connectivity."""
        with self.lock:
            self.network_online = online
            # On returning online, try to send any pending reports
            if self.network_online and self.pending_report:
                self._send_report("EXCEEDED_LIMIT")
                self.pending_report = False

    def send_data(self, size):
        """
        Attempt to send data.
        Returns True if sent, False if blocked due to limit.
        """
        with self.lock:
            self._check_period()
            if self.blocked:
                return False
            # Simulate sending
            self.data_sent += size
            if self.data_sent + self.data_received > self.max_volume:
                self.blocked = True
                # Try to send the report when blocked
                self._report_threshold_exceeded()
            return True

    def receive_data(self, size):
        """Attempt to receive data. Returns True if received, otherwise False."""
        with self.lock:
            self._check_period()
            if self.blocked:
                return False
            self.data_received += size
            if self.data_sent + self.data_received > self.max_volume:
                self.blocked = True
                self._report_threshold_exceeded()
            return True

    def _report_threshold_exceeded(self):
        # We report for each monitoring period only once
        period_id = self.current_period_start
        if self.last_reported_period != period_id:
            # Count reporting channel traffic if required
            report_size = 128 if self.reporting_channel_counted else 0
            if self.reporting_channel_counted and \
                self.data_sent + self.data_received + report_size > self.max_volume:
                # Even if report pushes over the limit, must report
                self.data_sent += report_size
            if self.network_online:
                self._send_report("EXCEEDED_LIMIT")
            else:
                self.pending_report = True    # save report for later sending
            self.last_reported_period = period_id

    def _send_report(self, event):
        self.service_platform.receive_report({
            "event": event,
            "period_start": self.current_period_start,
            "total_sent": self.data_sent,
            "total_received": self.data_received
        })

    def _check_period(self, force_restart=False):
        """Checks if period is expired and resumes if so or on forced restart (e.g. config change)."""
        now = time.time()
        if force_restart or now - self.current_period_start >= self.period:
            # Reset counters and unblock device for new period
            self.current_period_start = now
            self.data_sent = 0
            self.data_received = 0
            self.blocked = False
            self.pending_report = False
            self.last_reported_period = None

    def advance_time_boundary(self):
        """Force time boundary to simulate precise period change."""
        with self.lock:
            self.current_period_start -= self.period

    def stats(self):
        with self.lock:
            return dict(
                sent=self.data_sent, 
                received=self.data_received,
                blocked=self.blocked
            )

# ---- FIXTURES ----

@pytest.fixture
def service_platform():
    plat = MockIoTServicePlatform()
    yield plat
    plat.clear()

@pytest.fixture
def device_app(service_platform):
    return MockIoTDeviceApp(service_platform)

# ---- TESTS ----

def test_basic_threshold_and_reporting(device_app, service_platform):
    """Test basic data volume limiting, report, and blocking until period expires."""
    device_app.configure(max_volume=1000, period=5)  # 1000 bytes per 5 seconds

    # Send up to threshold
    assert device_app.send_data(800)   # 800 sent
    assert device_app.send_data(150)   # 950 sent
    assert device_app.receive_data(40) # 990 sent+recv
    # This will exceed allowed volume (990+20=1010 > 1000)
    assert not device_app.send_data(20)
    # Check blocked
    assert device_app.blocked
    # Check report
    reports = service_platform.get_reports()
    assert any(r['event'] == "EXCEEDED_LIMIT" for r in reports), "Report not sent to platform."

    # Test that data sending/receiving is now blocked
    assert not device_app.send_data(1)
    assert not device_app.receive_data(1)

    # After period expires, device resumes
    device_app.advance_time_boundary()
    assert device_app.send_data(200)
    assert not device_app.blocked

def test_dynamic_config_changes(device_app, service_platform):
    """Test changing volume and period mid-period triggers proper recalculation."""
    device_app.configure(max_volume=1000, period=10)
    assert device_app.send_data(950)
    # Increase limit during the period
    device_app.configure(max_volume=1200, period=10)
    assert device_app.send_data(200)  # Now total is 950+200=1150 < 1200

    # Reduce the volume below what is already sent
    device_app.configure(max_volume=1000, period=10)
    # Should block
    assert not device_app.send_data(1)
    # And report sent again for new config/breach
    reports = service_platform.get_reports()
    assert len(reports) >= 1

def test_network_connectivity_and_pending_reports(device_app, service_platform):
    """Test intermittent connectivity and that reports are resent when network returns."""
    device_app.configure(max_volume=500, period=5)
    device_app.simulate_network_state(True)
    assert device_app.send_data(500)
    # Simulate offline
    device_app.simulate_network_state(False)
    # Now try to send more; should block AND schedule report for next online
    assert not device_app.send_data(1)
    # Report NOT SENT YET since offline
    assert service_platform.get_reports() == []
    # Now online; report gets sent
    device_app.simulate_network_state(True)
    assert any(r['event'] == "EXCEEDED_LIMIT" for r in service_platform.get_reports())

def test_race_condition_at_period_boundary(device_app, service_platform):
    """Send data at very end/boundary of period to check race conditions."""
    device_app.configure(max_volume=100, period=3)
    device_app.send_data(90)
    # Simulate time jumps just before boundary
    device_app.current_period_start -= (device_app.period - 0.001)
    # Send should still count in old period and maybe block
    did_send = device_app.send_data(15)
    if did_send:
        assert device_app.data_sent <= device_app.max_volume
        # Should block further
        assert not device_app.send_data(10)
    else:
        assert device_app.blocked
    # After period expires, should resume
    device_app.advance_time_boundary()
    assert device_app.send_data(50)
    assert not device_app.blocked

def test_reporting_channel_is_counted(device_app, service_platform):
    """Test if reporting channel adds to data volume, but reporting must still happen."""
    device_app.configure(max_volume=128, period=2, reporting_channel_counted=True)
    # 120 sent, 8 left, next op would breach
    assert device_app.send_data(120)
    # This will breach and force report (128+report_size)
    assert not device_app.send_data(20)
    # Check block and report
    assert device_app.blocked
    assert any(r['event'] == "EXCEEDED_LIMIT" for r in service_platform.get_reports())

def test_concurrent_threshold_breaches(device_app, service_platform):
    """Simulate multiple threads trying to exceed limits at once."""
    device_app.configure(max_volume=300, period=5)

    def send_stream():
        # try to send several chunks quickly
        for _ in range(6):
            device_app.send_data(60)
            time.sleep(0.01)

    # Start several threads
    t1 = Thread(target=send_stream)
    t2 = Thread(target=send_stream)
    t1.start(); t2.start()
    t1.join(); t2.join()

    # Data sent should not exceed threshold by more than one block/critical section race (should not be > 360)
    stats = device_app.stats()
    assert stats['sent'] <= device_app.max_volume + 60, "Concurrent excess not well contained"
    assert device_app.blocked
    assert any(r['event'] == "EXCEEDED_LIMIT" for r in service_platform.get_reports())

def test_resume_communications_after_period(device_app, service_platform):
    """Device resumes sending/receiving automatically after period expires."""
    device_app.configure(max_volume=100, period=2)
    assert device_app.send_data(100)
    assert not device_app.send_data(10)
    device_app.advance_time_boundary()  # force new period start
    assert device_app.send_data(55)
    assert device_app.receive_data(40)
    assert not device_app.blocked
```

---

**How to use:**
- Save as `tests/test_data_volume_monitoring.py`
- Run: `pytest tests/test_data_volume_monitoring.py`
- To adapt for your real device/app, replace the MockIoTDeviceApp and service platform logic with real API calls and monitoring hooks.

**Covers:**
- Basic threshold and reporting
- Dynamic config and network changes
- Race at period boundary
- Multiple concurrent excess events
- Counting report channel
- Resume after new period