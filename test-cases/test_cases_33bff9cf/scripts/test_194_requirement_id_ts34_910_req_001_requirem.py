```python
# File: tests/test_nas_configuration_mo_reconfiguration.py

"""
Test Case for:
Requirement ID : TS.34_9.10_REQ_001

Requirement:
Verify that the terminal’s NAS configuration Management Object (MO) can be re-configured 
in accordance with 3GPP TS 24.368, as required by TS.34_9.10_REQ_001.

References:
- GSMA TS.34 v8.0, Section 9.10, TS.34_9.10_REQ_001
- 3GPP TS 24.368 (NAS configuration Management Object [MO] definition and reconfiguration procedures)
- IR.92 v22.0-2, Annex C (OMA DM V1.2/OMA DM Structure and MNO provisioning)
"""

import pytest

# --- MOCK/PLACEHOLDER CLASSES (replace with integration to live device, OMA DM server, and device APIs for actual testbed) ---

class MockNASConfigMO:
    """
    Simulates the NAS configuration Management Object (MO) as per 3GPP TS 24.368.
    Provides a dict-style API for params, with OMA DM GET/UPDATE simulation.
    """
    # Example parameter names/structure (actual as per TS 24.368 Annex A/C; adjust per your device's MO implementation)
    DEFAULTS = {
        "fallback_timer": 10,
        "allowed_rats": ["LTE", "NB-IoT"],
        "lapi_enabled": True,
        "emergency_timer": 30,
    }

    def __init__(self):
        self.mo_params = dict(self.DEFAULTS)
        self.log = []

    def query(self):
        """Return a copy of the current MO parameters/settings."""
        self.log.append("Queried NAS config MO (GET).")
        return dict(self.mo_params)
    
    def update(self, params):
        """Update specific parameters. Only keys present in DEFAULTS are allowed. Simulates OMA DM update behavior."""
        valid_updates = {}
        for k, v in params.items():
            if k in self.DEFAULTS:
                self.mo_params[k] = v
                valid_updates[k] = v
            else:
                self.log.append(f"Rejected update out-of-spec parameter: {k}={v} (not allowed by MO)")
        if valid_updates:
            self.log.append(f"MO parameters updated: {valid_updates}")

    def reset(self):
        self.mo_params = dict(self.DEFAULTS)
        self.log = []
    
    def get_log(self):
        return list(self.log)

# --- PYTEST FIXTURE ---

@pytest.fixture
def nas_config_mo():
    mo = MockNASConfigMO()
    yield mo
    mo.reset()

# --- TEST SCRIPT ---

def test_nas_config_mo_reconfiguration_via_oma_dm(nas_config_mo):
    """
    TS.34_9.10_REQ_001:
    - Query NAS Config MO, update via DM, verify results.
    - Repeat for at least two parameter sets (fallback_timer, allowed_rats, lapi, etc.).
    """

    # Step 1: Query and record current MO contents/settings
    orig_settings = nas_config_mo.query()
    print("Original NAS Config MO values:", orig_settings)
    assert isinstance(orig_settings, dict)
    for key in MockNASConfigMO.DEFAULTS:
        assert key in orig_settings

    # Step 2: Update MO via DM with first parameter set (change fallback_timer and allowed_rats)
    update_params_1 = {
        "fallback_timer": 20,
        "allowed_rats": ["LTE", "NR"],  # change allowed RATs
    }
    nas_config_mo.update(update_params_1)
    nas_config_mo.log.append("Update 1 completed.")

    # Step 3: Re-query, confirm immediate update for updated fields, unchanged others
    after_update_1 = nas_config_mo.query()
    for k, v in update_params_1.items():
        assert after_update_1[k] == v, f"{k} not updated to {v}, got {after_update_1[k]}"
    for k in MockNASConfigMO.DEFAULTS:
        if k not in update_params_1:
            assert after_update_1[k] == orig_settings[k], f"{k} changed unexpectedly."

    # Step 4: Try out-of-spec parameter update (should be rejected)
    update_params_invalid = {"unsupported_param": 12345}
    nas_config_mo.update(update_params_invalid)
    after_invalid_attempt = nas_config_mo.query()
    assert "unsupported_param" not in after_invalid_attempt, "Out-of-spec parameter update should be rejected."

    # Step 5: Update a different set (toggle LAPI, update emergency timer)
    update_params_2 = {
        "lapi_enabled": False,
        "emergency_timer": 60
    }
    nas_config_mo.update(update_params_2)
    after_update_2 = nas_config_mo.query()
    for k, v in update_params_2.items():
        assert after_update_2[k] == v, f"{k} did not update as expected."

    # Step 6: Repeat with original values for restoration (to check repeatability)
    nas_config_mo.update(orig_settings)
    after_reset = nas_config_mo.query()
    assert after_reset == orig_settings, "MO values not restored to original configuration"

    # Optional: Step 7: "Validate changes take effect in network behavior" - for True system/hardware, have
    # protocol analyzer capture signaling and verify behavior after config (not covered in this mock)
    #
    # Log all actions for traceability/audit
    log = nas_config_mo.get_log()
    print("NAS Config MO operation log:")
    for entry in log:
        print(" -", entry)

@pytest.mark.parametrize("update_params,should_pass", [
    ({"fallback_timer": 15}, True),                       # Valid update
    ({"emergency_timer": 999}, True),                     # Valid update
    ({"unrecognized_param": "bad"}, False),               # Not in MO, should be rejected
    ({"allowed_rats": ["LTE", "NB-IoT", "UnknownRAT"]}, True),  # Valid syntax, even if RAT value not in reference set
])
def test_nas_config_mo_param_validation(nas_config_mo, update_params, should_pass):
    """Confirm that only supported parameters may be updated; others rejected or ignored."""
    before = nas_config_mo.query()
    nas_config_mo.update(update_params)
    after = nas_config_mo.query()
    if should_pass:
        for k, v in update_params.items():
            assert k in MockNASConfigMO.DEFAULTS, f"{k} should be recognized as a valid param"
            assert after[k] == v
    else:
        for k in update_params:
            assert k not in after or after[k] == before.get(k), f"{k} was incorrectly updated"

    log = nas_config_mo.get_log()
    print("Validation test log:", log)
```
---

**How to use this script:**
- Save as `tests/test_nas_configuration_mo_reconfiguration.py`
- For real integration, replace `MockNASConfigMO` with OMA DM or device config APIs, and actual MO schema for your terminal.
- Run with:
  ```bash
  pytest tests/test_nas_configuration_mo_reconfiguration.py
  ```
- All step comments and assertions align with TS.34_9.10_REQ_001 and referenced 3GPP procedures, including parameter validation, repeatable updates, and audit-friendly output. Adjust parameter or structure for your TS 24.368 MO schema as required.