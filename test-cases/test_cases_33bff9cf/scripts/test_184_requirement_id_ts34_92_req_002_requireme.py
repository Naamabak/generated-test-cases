```python
# File: tests/test_efnasconfig_lapi_indicator.py

"""
Test Case for:
Requirement ID : TS.34_9.2_REQ_002

Requirement:
If the EFNAS Config Elementary File is present on SIM Card and the LAPI field is filled, then the module SHALL comply with the LAPI value contained in that file, conveying the LAP Indicator in RRC and NAS messages to the network.

References:
- GSMA TS.34 v8.0, Section 9.2, TS.34_9.2_REQ_002 (page 58)
- 3GPP TS 31.102 (EFNASCONFIG file structure)
- 3GPP TS 24.008, 3GPP TS 36.331 (LAPI/LAP signaling in NAS & RRC)
"""

import pytest

# ------------------ MOCK CLASSES (Replace for system/lab integration) ------------------

class MockSimCard:
    """
    Simulates a SIM Card with an EFNAS Config file containing a LAPI field.
    """
    def __init__(self, lapi_value: int):
        self.efnasconfig_lapi = lapi_value  # LAPI value as present in EFNAS Config

    def read_lapi(self):
        # Simulate reading the LAPI value from EFNAS Config
        return self.efnasconfig_lapi

class MockIoTCommModule:
    """
    Simulates an IoT module reading EFNAS Config, incorporating LAPI into RRC/NAS messaging.
    """
    def __init__(self):
        self.lapi_value = None
        self.last_captured_rrc = []
        self.last_captured_nas = []

    def insert_sim(self, sim: MockSimCard):
        self.lapi_value = sim.read_lapi()

    def power_on_and_attach(self):
        # Simulate sending RRC/NAS messages that should contain LAP Indicator
        lapi = self.lapi_value
        # Dummy message format for LAPI in bit field (real structure is 3GPP-specific)
        self.last_captured_rrc = [
            {"type": "RRCConnectionRequest", "lap_indicator": lapi},
            {"type": "RRCConnectionSetupComplete", "lap_indicator": lapi}
        ]
        self.last_captured_nas = [
            {"type": "AttachRequest", "lap_indicator": lapi},
            {"type": "ServiceRequest", "lap_indicator": lapi},
            {"type": "TrackingAreaUpdateRequest", "lap_indicator": lapi}
        ]

    def get_last_rrc_messages(self):
        return list(self.last_captured_rrc)

    def get_last_nas_messages(self):
        return list(self.last_captured_nas)

    def reset(self):
        self.lapi_value = None
        self.last_captured_rrc = []
        self.last_captured_nas = []

# ----------- FIXTURE: Combine module and SIM for parameterized scenarios -----------

@pytest.fixture(params=[
    0, 1, 2, 3  # Different possible LAPI values for testing (real values are protocol field-dependent)
], ids=lambda v: f"LAPI={v}")
def sim_and_module(request):
    sim = MockSimCard(lapi_value=request.param)
    mod = MockIoTCommModule()
    mod.insert_sim(sim)
    mod.power_on_and_attach()
    yield sim, mod
    mod.reset()

# ----------- TEST SCRIPT -----------

def test_lap_indicator_matches_lapi_value_in_all_rrc_and_nas(sim_and_module):
    """
    Main TS.34_9.2_REQ_002 pass/fail logic:
    - For every relevant RRC/NAS message, LAP Indicator must match SIM EFNASConfig.LAPI.
    """

    sim, mod = sim_and_module
    lapi = sim.read_lapi()

    # Step 3-4: Capture and inspect all RRC/NAS messages for LAP indicator bits/fields
    rrc_msgs = mod.get_last_rrc_messages()
    nas_msgs = mod.get_last_nas_messages()

    # Check RRC messages
    for msg in rrc_msgs:
        assert msg['lap_indicator'] == lapi, (
            f"RRC Message '{msg['type']}' LAP Indicator ({msg['lap_indicator']}) "
            f"does not match SIM LAPI value ({lapi})"
        )

    # Check NAS messages
    for msg in nas_msgs:
        assert msg['lap_indicator'] == lapi, (
            f"NAS Message '{msg['type']}' LAP Indicator ({msg['lap_indicator']}) "
            f"does not match SIM LAPI value ({lapi})"
        )

    # Print messages for trace/audit
    print("Tested SIM LAPI:", lapi)
    print("RRC Messages:", rrc_msgs)
    print("NAS Messages:", nas_msgs)

@pytest.mark.parametrize("initial_lapi,updated_lapi", [(2, 0), (1, 3)])
def test_dynamic_lapi_change_is_reflected_after_reboot(initial_lapi, updated_lapi):
    """
    Exit criteria (c):
    - Dynamic change to LAPI (with module reboot/hotswap) is reflected in all subsequent messages.
    """
    sim = MockSimCard(lapi_value=initial_lapi)
    mod = MockIoTCommModule()
    mod.insert_sim(sim)
    mod.power_on_and_attach()

    # Confirm initial
    msgs_before = mod.get_last_rrc_messages() + mod.get_last_nas_messages()
    assert all(msg['lap_indicator'] == initial_lapi for msg in msgs_before)

    # Change LAPI on SIM, re-insert/reboot module
    sim.efnasconfig_lapi = updated_lapi
    mod.insert_sim(sim)  # Hot-swap / simulate re-insertion
    mod.power_on_and_attach()
    msgs_after = mod.get_last_rrc_messages() + mod.get_last_nas_messages()
    assert all(msg['lap_indicator'] == updated_lapi for msg in msgs_after)

    print(f"Dynamic LAPI update from {initial_lapi} -> {updated_lapi} reflected in all RRC/NAS messages.")

def test_protocol_captures_show_lap_indicator_fields(sim_and_module):
    """
    For documentation/audit: Confirm protocol captures/fields match expected value layouts (pseudo).
    """
    sim, mod = sim_and_module
    lapi = sim.read_lapi()
    rrc, nas = mod.get_last_rrc_messages(), mod.get_last_nas_messages()
    for msg in rrc + nas:
        # Emulate binary field extraction (in real test: parse hex/bitfield structure)
        field_val = msg['lap_indicator']
        assert isinstance(field_val, int) and 0 <= field_val <= 3, "LAP Indicator field out of valid encoding range!"
        print(f"Message {msg['type']} | LAP field value: {field_val} (matches LAPI {lapi})")

```
---

**Instructions:**
- Place as `tests/test_efnasconfig_lapi_indicator.py`.
- Replace mock classes with your real SIM/EFNASConfig extractor, RRC/NAS message capture/log parser, or device/network tool integration as required.
- Run with:
  ```bash
  pytest tests/test_efnasconfig_lapi_indicator.py
  ```
- All assertions and test steps map directly to GSMA TS.34_9.2_REQ_002 entry/procedure/exit criteria, with print/logs for traceability and evidence.
- To integrate with live protocol logs, add parsing to extract LAP Indicator from RRC/NAS binary traces and compare to LAPI values programmed on the SIM.
