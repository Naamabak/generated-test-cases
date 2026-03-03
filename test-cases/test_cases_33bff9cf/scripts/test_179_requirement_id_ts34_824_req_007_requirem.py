```python
# File: tests/test_rpm_parameter_ota_management.py

"""
Test Case for:
Requirement ID : TS.34_8.2.4_REQ_007

Requirement:
The IoT Communication Module SHALL support remote management of RPM parameters via the (U)SIM OTA mechanism,
detect the REFRESH command with FILE LIST TLV on the (U)SIM after OTA parameter update, re-read new parameters,
and apply them as active configuration. All relevant counters/timers should be reset as per GSM TS.34 Section 8.2.4.

References:
- GSMA TS.34 v8.0, Section 8.2.4, TS.34_8.2.4_REQ_007/008/009
- 3GPP TS 31.102 (UICC/USIM REFRESH behavior)
"""

import pytest

# -- Mock/Placeholder classes (replace with real integration/APIs for live testbed) --

class MockUSIM:
    """
    Simulates a (U)SIM card that contains RPM parameters and can receive OTA updates with REFRESH.
    """
    def __init__(self, initial_params=None):
        self.rpm_params = dict(initial_params or {"RPM_Flag": True, "RPM_Threshold": 4, "RPM_Timer1": 30})
        self.last_refresh_type = None
        self.last_file_list = None
        self.file_change_count = 0

    def get_rpm_params(self):
        return dict(self.rpm_params)

    def ota_update_rpm_params(self, updated_params):
        self.rpm_params.update(updated_params)
        self.issue_refresh_command()

    def issue_refresh_command(self):
        self.last_refresh_type = "FILE_CHANGE_NOTIFICATION"
        self.last_file_list = ["EF_RPMPARAMS"]
        self.file_change_count += 1

    def get_refresh_event(self):
        # Returns refresh type and file list as in REFRESH command/notification
        return {"type": self.last_refresh_type, "file_list": self.last_file_list, "count": self.file_change_count}


class MockIoTCommModule:
    """
    Simulates the IoT Communication Module with ability to read and apply RPM parameters, monitor for REFRESH,
    and reset counters/timers after parameter updates.
    """
    def __init__(self, usim: MockUSIM):
        self.usim = usim
        self.active_rpm_params = dict(usim.get_rpm_params())
        self.counters_timers = {"C_RPM1": 7, "T_RPM1": 22}  # Example stateful values
        self.log = []
        self.refresh_event_seen = 0

    def query_rpm_params(self):
        return dict(self.active_rpm_params)

    def query_counters_timers(self):
        return dict(self.counters_timers)

    def simulate_detection_of_refresh(self):
        refresh_data = self.usim.get_refresh_event()
        if refresh_data["type"] == "FILE_CHANGE_NOTIFICATION" and "EF_RPMPARAMS" in refresh_data["file_list"]:
            self.log.append("Detected REFRESH command for EF_RPMPARAMS (OTA parameter update)")
            self.apply_rpm_update_from_usim()
            self.refresh_event_seen += 1

    def apply_rpm_update_from_usim(self):
        # Re-read all RPM params and apply as active config; reset counters/timers as required
        self.active_rpm_params = dict(self.usim.get_rpm_params())
        for ct in self.counters_timers:
            self.counters_timers[ct] = 0
        self.log.append("RPM params have been re-read and applied from (U)SIM; counters/timers reset")

    def get_log(self):
        return list(self.log)

    def reset_log(self):
        self.log = []

# --- Pytest Fixtures ---

@pytest.fixture
def usim():
    return MockUSIM({"RPM_Flag": True, "RPM_Threshold": 4, "RPM_Timer1": 30})

@pytest.fixture
def comm_module(usim):
    return MockIoTCommModule(usim)

# --- Test Script ---

def test_remote_rpm_parameter_ota_update_and_detection(comm_module, usim):
    """
    TS.34_8.2.4_REQ_007:
    - OTA platform can update RPM parameters on (U)SIM
    - REFRESH command is issued, detected by module, which re-reads and applies new values
    - Counters/timers are reset
    - All steps are logged and repeat for multiple cycles
    """

    # Step 1: Query/document initial RPM params (U)SIM and module
    initial_usim_params = usim.get_rpm_params()
    initial_module_params = comm_module.query_rpm_params()
    assert initial_module_params == initial_usim_params
    print("Initial RPM parameters:", initial_usim_params)

    # Step 2: Send OTA update to (U)SIM, change RPM params
    updated_params = {"RPM_Flag": False, "RPM_Threshold": 8, "RPM_Timer1": 61}
    usim.ota_update_rpm_params(updated_params)

    # Step 3: Simulate module detection of REFRESH event (as happens via real device REFRESH monitoring)
    comm_module.simulate_detection_of_refresh()
    log = comm_module.get_log()
    assert any("Detected REFRESH command" in l for l in log)
    assert any("re-read and applied from (U)SIM" in l for l in log)

    # Step 4-5: RPM params and counter/timer values are updated and reset
    after_update_params = comm_module.query_rpm_params()
    for k, v in updated_params.items():
        assert after_update_params[k] == v, f"Updated param {k} not applied ({after_update_params[k]} != {v})"
    print("RPM parameters after OTA update:", after_update_params)

    after_counters_timers = comm_module.query_counters_timers()
    assert all(v == 0 for v in after_counters_timers.values()), "Counters/timers not reset on REFRESH event"
    print("Counters/timers (post-REFRESH):", after_counters_timers)

    # Step 6: Repeat for further OTA updates and parameter sets (multiple cycles)
    for cycle, update in enumerate([
        {"RPM_Flag": True, "RPM_Threshold": 2, "RPM_Timer1": 88},
        {"RPM_Flag": False, "RPM_Threshold": 10, "RPM_Timer1": 11}
    ], 1):
        usim.ota_update_rpm_params(update)
        comm_module.simulate_detection_of_refresh()
        for k, v in update.items():
            assert comm_module.query_rpm_params()[k] == v
        assert all(v == 0 for v in comm_module.query_counters_timers().values())
        print(f"Cycle {cycle}: Updated params:", comm_module.query_rpm_params())

    # Step 7: All LOG output shows detection, re-read, counters zeroed each time
    all_log = comm_module.get_log()
    print("Full test log (OTA/REFRESH and RPM param state):")
    for entry in all_log:
        print("  ", entry)

@pytest.mark.parametrize("param_update", [
    {"RPM_Flag": True, "RPM_Threshold": 1, "RPM_Timer1": 99},
    {"RPM_Timer1": 45}
])
def test_log_and_param_readout_post_ota(comm_module, usim, param_update):
    """
    (e) End-to-end process works for repeated OTA updates—module always reflects new RPM param values after REFRESH.
    """
    usim.ota_update_rpm_params(param_update)
    comm_module.simulate_detection_of_refresh()
    log = comm_module.get_log()
    for k, v in param_update.items():
        assert comm_module.query_rpm_params()[k] == v
    print(f"OTA update {param_update} -> Log: {log[-2:]}")

```
---

**How to use / adapt:**
- Save as `tests/test_rpm_parameter_ota_management.py`
- Integrate with your OTA platform, SIM/USIM REFRESH notification hooks, and module diagnostic query for production/lab/system use
- Run with:
  ```bash
  pytest tests/test_rpm_parameter_ota_management.py
  ```
- All steps/assertions map directly to GSMA TS.34_8.2.4_REQ_007 and referenced UICC OTA/REFRESH logics. Logging statements serve for traceability and audit evidence. Extend mock logic for your parameter set or real module APIs as needed.
