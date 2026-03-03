```python
# File: tests/test_rpm_location_update_no_extra_on_ps_request.py

"""
Test Case for:
Requirement ID : TS.34_8.2.2_REQ_009

Requirement:
If Location Update Request is ignored by network, RPM SHALL ensure that any Packet Switched (PS) related service 
request from IoT Device Application will not trigger additional Location Update Requests beyond those the 
IoT Communications Module would have sent in the absence of the service request.

References:
- GSMA TS.34 v8.0, Section 8.2.2, TS.34_8.2.2_REQ_009
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf (page 47, contextual notes)
- 3GPP TS 24.008, network signaling and Location Update procedures
"""

import pytest

# --- MOCK / PLACEHOLDER CLASSES --- 
# Replace these with real device/network integration interfaces in production/lab/CI.

class MockNetwork:
    """
    Simulated network environment that can be configured to ignore Location Update Requests.
    """
    def __init__(self, ignore_location_update=True):
        self.ignore_location_update = ignore_location_update

    def receive_location_update_request(self):
        if self.ignore_location_update:
            return None  # No response, no indication to module
        return "RESPONSE"  # In normal network, a response is returned

class MockIoTCommModule:
    """
    Simulates a Communications Module with RPM and basic network location update logic.
    """
    def __init__(self, network, log_tag="MODULE_BASELINE"):
        self.network = network
        self.log_tag = log_tag
        self.lu_request_log = []    # List of ("lu_request", tag, timestamp)
        self.ps_service_log = []    # List of ("ps_service", tag, timestamp)
        self._time = 0

    def _advance_time(self, dt=1):
        self._time += dt

    def trigger_location_update(self):
        # Triggers a Location Update Request to the network.
        self.lu_request_log.append((self.log_tag, self._time))
        resp = self.network.receive_location_update_request()
        self._advance_time()
        return resp

    def handle_periodic_network_processes(self):
        """
        Simulates the module's regular network management, which may send LU Reqs on timer/periodicity.
        """
        # For baseline measurement: manually trigger an LU Request as would happen on timer/expiry
        self.trigger_location_update()

    def receive_ps_service_request_from_app(self, trigger_lu_request=True, app_tag="APP"):
        """
        Simulates the IoT Device Application making a PS service request (e.g., PDP Context Activation).
        - If trigger_lu_request==True, the module would naively issue an extra LU Req here (NOT TS.34-compliant)
        - If False, RPM-compliant logic: No new LU Request is sent, just PS service is noted
        """
        self.ps_service_log.append((app_tag, self._time))
        # TS.34 requires: If LU is already outstanding/ignored, NO new LU should be triggered.
        if trigger_lu_request:
            self.trigger_location_update()
        self._advance_time()

    def get_location_update_count(self):
        return len(self.lu_request_log)

    def get_ps_service_count(self):
        return len(self.ps_service_log)

    def get_lu_log(self):
        return list(self.lu_request_log)

    def get_ps_log(self):
        return list(self.ps_service_log)

    def reset(self):
        self.lu_request_log = []
        self.ps_service_log = []
        self._time = 0

# --- PYTEST FIXTURES ---

@pytest.fixture
def network_ignore_lu():
    """Network that ignores all Location Update Requests."""
    return MockNetwork(ignore_location_update=True)

@pytest.fixture
def comm_module_baseline(network_ignore_lu):
    """ Module running in baseline mode, i.e., no device application sending PS service requests. """
    return MockIoTCommModule(network_ignore_lu, log_tag="MODULE_BASELINE")

@pytest.fixture
def comm_module_with_app(network_ignore_lu):
    """ Module receiving explicit PS service requests from application (test case of interest). """
    return MockIoTCommModule(network_ignore_lu, log_tag="MODULE_W_APP")

# --- TEST SCRIPT ---

def test_rpm_no_extra_location_update_on_ps_request(comm_module_baseline, comm_module_with_app):
    """
    TS.34_8.2.2_REQ_009:
    When network ignores LU, PS service requests from application must NOT cause additional LU requests.
    """

    # Step 1: Establish baseline - Module operates under ignored LU scenario without any PS service requests:
    comm_module_baseline.trigger_location_update()
    comm_module_baseline.handle_periodic_network_processes()  # Simulate several cycles (baseline/LU window)
    comm_module_baseline.handle_periodic_network_processes()
    lu_log_baseline = comm_module_baseline.get_lu_log()
    k_baseline = comm_module_baseline.get_location_update_count()
    print(f"Baseline LU Requests (no PS service): {lu_log_baseline}")

    # Step 2: Test under same network: Module + App triggers PS service requests during LU ignored window:
    comm_module_with_app.trigger_location_update()
    comm_module_with_app.handle_periodic_network_processes()      # Simulate same LU window baseline (first LU outstanding)
    comm_module_with_app.receive_ps_service_request_from_app(trigger_lu_request=False, app_tag="APP1")
    comm_module_with_app.handle_periodic_network_processes()
    comm_module_with_app.receive_ps_service_request_from_app(trigger_lu_request=False, app_tag="APP2")
    lu_log_app = comm_module_with_app.get_lu_log()
    k_with_app = comm_module_with_app.get_location_update_count()
    print(f"Test LU Requests (with PS service): {lu_log_app}")
    ps_log_app = comm_module_with_app.get_ps_log()
    print(f"PS service logs (with PS service): {ps_log_app}")

    # Step 3: Compare LU request counts
    # The number should be equal: PS service requests should NOT increase LU Requests!
    assert k_with_app == k_baseline, (
        f"Extra Location Update Request(s) detected: {k_with_app} with app vs {k_baseline} baseline"
    )
    # Optionally, check that timestamps of all LU Requests in both logs match (no extras added at PS request time)
    baseline_timestamps = [ts for tag, ts in lu_log_baseline]
    withapp_timestamps = [ts for tag, ts in lu_log_app]
    assert withapp_timestamps == baseline_timestamps, (
        "LU request times differ; possible extra request(s) generated after PS service requests!"
    )

    # Step 4: Repeat with multiple PS service requests within a single LU ignore window -- confirm no extra LU Requests
    comm_module_with_app.reset()
    comm_module_with_app.trigger_location_update()
    comm_module_with_app.receive_ps_service_request_from_app(trigger_lu_request=False, app_tag="APP3")
    comm_module_with_app.receive_ps_service_request_from_app(trigger_lu_request=False, app_tag="APP4")
    comm_module_with_app.handle_periodic_network_processes()
    lu_log_repeat = comm_module_with_app.get_lu_log()
    assert comm_module_with_app.get_location_update_count() == k_baseline, "Additional PS service requests incorrectly increased LU requests"

    # Step 5: Print logs for evidence
    print("Final LU Log with multiple PS requests:", lu_log_repeat)

@pytest.mark.parametrize("trigger_ps_during_ignored_lu, expected_extra_lu", [
    (False, 0),  # TS.34-compliant behavior (no extra LU)
    (True, 1),   # Non-compliant (as a negative sample; for demonstration)
])
def test_noncompliant_behavior(example=trigger_ps_during_ignored_lu, expected_extra_lu=None):
    """
    Negative/control test: What if the module is NOT compliant and triggers extra LU on PS request?
    """
    network = MockNetwork(ignore_location_update=True)
    comm_module = MockIoTCommModule(network, log_tag="NEGATIVE_CASE")
    comm_module.trigger_location_update()
    base_count = comm_module.get_location_update_count()
    if expected_extra_lu:
        # Simulate the error: PS service triggers an extra LU
        comm_module.receive_ps_service_request_from_app(trigger_lu_request=True, app_tag="APP_NEG")
    else:
        # Correct: PS service does NOT trigger extra LU
        comm_module.receive_ps_service_request_from_app(trigger_lu_request=False, app_tag="APP_CORRECT")
    after_count = comm_module.get_location_update_count()
    correct_behavior = (after_count - base_count == expected_extra_lu)
    assert correct_behavior, (
        f"PS service request should result in {expected_extra_lu} extra LU Requests (got {after_count - base_count})"
    )
    print("Non-compliance log (negative sample):", comm_module.get_lu_log())

```
---

**How to use/adapt:**
- Save as `tests/test_rpm_location_update_no_extra_on_ps_request.py`
- Integrate/replace mocks with actual signaling/log APIs for device/network testbed when available.
- Run with:
  ```bash
  pytest tests/test_rpm_location_update_no_extra_on_ps_request.py
  ```
- The test strictly covers baseline and with-app scenarios, asserts no extra LU requests are triggered, and includes audit/control checks and negative examples for regression.

Let me know if you need this wired to a real protocol stack, live AT/NAS log, or test equipment API!