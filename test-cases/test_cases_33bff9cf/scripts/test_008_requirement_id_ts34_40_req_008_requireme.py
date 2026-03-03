```python
# File: tests/test_network_speed_latency_tolerance.py

"""
Requirement:
- TS.34_4.0_REQ_008: IoT Device Application should cope with variances in mobile network data speed and latency
  across different technologies (2G, 3G, LTE, LTE-M, NB-IoT).

Purpose:
- Ensure the IoT Device Application performs its normal functions, adapts, and does not fail under various
  network data speeds/latencies.

References:
- GSMA TS.34 v8.0, Section 4.0, TS.34_4.0_REQ_008
"""

import pytest
import time
from unittest.mock import MagicMock

# --- MOCKS/PLACEHOLDERS ---
# Replace these with integration to your actual device test harness/network simulator

NETWORK_PROFILES = [
    # (Name, Download kbps, Upload kbps, Latency ms)
    ("2G",      100,   50,  350),
    ("3G",    1500,  500,  100),
    ("LTE",  10000, 3000,   50),
    ("LTE-M",  500,  200,  200),
    ("NB-IoT",  60,   30, 1500),
]

class NetworkEmulator:
    """Mock network emulator/context manager for bandwidth & latency profiles."""
    def __init__(self, down_kbps, up_kbps, latency_ms):
        self.down_kbps = down_kbps
        self.up_kbps = up_kbps
        self.latency_ms = latency_ms
    def __enter__(self):
        # Placeholders for starting network shaping/emulation
        print(f"Applying network profile: down={self.down_kbps}kbps, up={self.up_kbps}kbps, latency={self.latency_ms}ms")
    def __exit__(self, et, ev, tb):
        # Placeholders to remove/restore network settings
        print("Restoring default network profile.")

class IoTDeviceApplication:
    """Mock device app with simple service/data/signaling ops."""
    def __init__(self):
        self.error_log = []
        self.result_log = []

    def perform_data_operation(self):
        """Simulated data upload/download, expected to account for latency."""
        try:
            # Simulate operation logic (replace this with actual test harness code)
            time.sleep(0.1)     # Simulating time taken for an operation
            self.result_log.append("data_transfer_success")
            return True
        except Exception as e:
            self.error_log.append(str(e))
            return False

    def perform_service_operation(self):
        try:
            time.sleep(0.05)
            self.result_log.append("service_operation_success")
            return True
        except Exception as e:
            self.error_log.append(str(e))
            return False

    def perform_signaling(self):
        try:
            time.sleep(0.02)
            self.result_log.append("signaling_success")
            return True
        except Exception as e:
            self.error_log.append(str(e))
            return False

    def clear_logs(self):
        self.error_log.clear()
        self.result_log.clear()

    def get_errors(self):
        return self.error_log

    def get_results(self):
        return self.result_log

# --- FIXTURE ---

@pytest.fixture()
def iot_device_app():
    """Fixture: Provides a fresh IoT Device Application per test."""
    return IoTDeviceApplication()

# --- TEST ---

@pytest.mark.parametrize("profile", NETWORK_PROFILES)
def test_iot_app_handles_various_network_conditions(iot_device_app, profile):
    """
    For each mobile network profile, verify IoT Device Application adaptation &
    tolerance to speed and latency variations for all normal operations.
    """
    profile_name, down_kbps, up_kbps, latency_ms = profile

    # STEP 1: Enter the emulated network condition context
    with NetworkEmulator(down_kbps, up_kbps, latency_ms):
        # STEP 2 & 5: Operate the App under test conditions; repeat for all major ops
        iot_device_app.clear_logs()
        
        # Data Transfer (Upload/Download Simulation)
        result_data = iot_device_app.perform_data_operation()
        # Service Operation (e.g. config/operation)
        result_service = iot_device_app.perform_service_operation()
        # Signaling (e.g. lightweight heartbeat, registration)
        result_signal = iot_device_app.perform_signaling()
        
        # STEP 3: Observe and ensure no critical error/failure in any profile
        errors = iot_device_app.get_errors()
        assert not errors, (
            f"Application failed critical ops for network '{profile_name}' "
            f"with errors: {errors}"
        )

        # STEP 4: Optionally, verify App logs adaptation (here: just results, in real test: retry/queue/adapt)
        results = iot_device_app.get_results()
        assert result_data is True, f"{profile_name}: Data operation failed"
        assert result_service is True, f"{profile_name}: Service operation failed"
        assert result_signal is True, f"{profile_name}: Signaling failed"
        assert all(r.endswith("success") for r in results), f"{profile_name}: Not all operations succeeded: {results}"

        # Optional: If logs for retrying/queueing present, check for adaptation (extend mock/real handler as needed)
        # Example (if app had a 'was_queued' or 'was_retried' log): assert app.adapted_to_latency == True

        print(f"[{profile_name}] All operations succeeded under specified latency/data speed.")

```

---

**How to use:**
- Place this file in your `tests/` directory.
- Integrate the `IoTDeviceApplication` logic with actual device APIs or test harness.
- Integrate the `NetworkEmulator` context into your network emulation setup (e.g., Linux tc/netem, hardware network emulator, cloud network profiles).
- Run the test with pytest:  
  ```bash
  pytest tests/test_network_speed_latency_tolerance.py
  ```

---

**What is covered:**
- Exhaustive simulation of all major mobile network technology conditions (2G, 3G, LTE, LTE-M, NB-IoT).
- Per-profile functional testing of data transfer, signaling, and service ops.
- Assertion of robust, error-free execution under adverse speed/latency.
- Placeholder for adaptation logic to be checked (queues, retries, etc).

**To adapt for your environment:** Replace mocks with device comms and real network shaping/instrumentation.

Let me know if you want (or wish to automate) integration with real network emulation tools or device testbeds!
```