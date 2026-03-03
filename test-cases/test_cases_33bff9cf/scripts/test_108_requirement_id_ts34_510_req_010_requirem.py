```python
# File: tests/test_comm_module_dm_server_settings_factory_load.py

"""
Test Case for:
Requirement ID : TS.34_5.10_REQ_010

Requirement:
The IoT Communications Module SHALL support the factory loading of current DM Server settings (from the MNO) prior to shipment, and must allow differentiation of DM server settings based on the MNO of the UICC if multiple MNOs are supported.

References:
- GSMA TS.34 v8.0, Section 5.10, TS.34_5.10_REQ_010
- OMA Device Management specification
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest

# --- MOCK/PLACEHOLDER CLASSES (replace with your own device/OMA DM client/server and manufacturer data integration) ---

class MockMNOSettingsSource:
    """Simulates current, approved DM Server settings per MNO as provided/approved by each operator."""
    def __init__(self, mno_settings):
        # mno_settings: dict of {mno_code: {"dm_server": ..., "dm_port": ...}}
        self.mno_settings = mno_settings

    def get_settings(self, mno_code):
        return self.mno_settings.get(mno_code)

class MockManufacturerRecords:
    """Simulates the manufacturer's documented process, showing source of DM server config values for modules."""
    def __init__(self, config_map):
        # config_map: dict of {module_sn: {"dm_server": ..., "from_mno": True/False, "timestamp": ...}}
        self.config_map = config_map

    def get_module_record(self, module_sn):
        return self.config_map.get(module_sn, None)

class MockUICC:
    """Simulates a UICC card carrying an MNO profile."""
    def __init__(self, imsi_prefix, mno_code):
        self.imsi_prefix = imsi_prefix
        self.mno_code = mno_code

class MockCommModule:
    """
    Simulates a factory-shipped IoT Communications Module, storing DM Server settings per "as-shipped" image.
    For multi-MNO modules, can change DM server config based on inserted UICC/MNO.
    """
    def __init__(self, module_sn, factory_loaded_settings, multi_mno_support=False, mno_map=None):
        self.module_sn = module_sn
        self.dm_server_settings = dict(factory_loaded_settings)  # as-shipped settings
        self.multi_mno_support = multi_mno_support
        self.mno_map = mno_map or {}  # e.g. {'mnoA': {...}, 'mnoB': {...}}
        self.current_uicc = None

    def query_dm_server_settings(self):
        """Simulate querying settings via OMA DM node fetch or other management interface."""
        return dict(self.dm_server_settings)

    def insert_uicc_and_reload(self, uicc: MockUICC):
        """
        For multi-MNO modules, simulate switching DM server settings based on UICC/MNO.
        """
        self.current_uicc = uicc
        if self.multi_mno_support and uicc and uicc.mno_code in self.mno_map:
            self.dm_server_settings = dict(self.mno_map[uicc.mno_code])

    def get_sn(self):
        return self.module_sn

# ---- TEST FIXTURES ----

@pytest.fixture
def mno_settings_source():
    """Provides the latest MNO-approved server settings for reference/comparison."""
    return MockMNOSettingsSource({
        "MNO1": {"dm_server": "dm-server.mno1.com", "dm_port": 443, "version": "v1.3"},
        "MNO2": {"dm_server": "dm-server.mno2.com", "dm_port": 8443, "version": "v1.3"},
    })

@pytest.fixture
def manufacturer_records():
    """Simulates manufacturer production/configuration records for a set of shipped modules."""
    return MockManufacturerRecords({
        "SN-MOD1": {"dm_server": "dm-server.mno1.com", "from_mno": True, "timestamp": "2024-07-01T13:00Z"},
        "SN-MOD2": {"dm_server": "dm-server.mno2.com", "from_mno": True, "timestamp": "2024-07-01T14:00Z"},
    })

@pytest.fixture
def factory_modules():
    """Produces several as-shipped modules for test."""
    # Single-MNO module
    mod1 = MockCommModule("SN-MOD1",
        factory_loaded_settings={"dm_server": "dm-server.mno1.com", "dm_port": 443, "version": "v1.3"},
        multi_mno_support=False
    )
    # Multi-MNO module with support for settings switch
    multi_mod = MockCommModule("SN-MOD-MULTI",
        factory_loaded_settings={"dm_server": "dm-server.mno1.com", "dm_port": 443, "version": "v1.3"},
        multi_mno_support=True,
        mno_map={
            "MNO1": {"dm_server": "dm-server.mno1.com", "dm_port": 443, "version": "v1.3"},
            "MNO2": {"dm_server": "dm-server.mno2.com", "dm_port": 8443, "version": "v1.3"},
        }
    )
    return [mod1, multi_mod]

# ---- TEST SCRIPT ----

def test_factory_loaded_dm_server_settings(factory_modules, mno_settings_source, manufacturer_records):
    """
    TS.34_5.10_REQ_010:
    - Each module must have factory-loaded settings matching the latest from MNO (as-shipped, before config).
    - Manufacturer process docs must show that configs were sourced from MNO.
    - For multi-MNO, verify correct DM server per UICC/MNO.
    - No module may have stale/missing/default DM server.
    """

    for mod in factory_modules:
        record = manufacturer_records.get_module_record(mod.get_sn())
        # a) As-shipped DM Server settings must MATCH MNO reference
        settings = mod.query_dm_server_settings()
        # Use record and UICC (if present) to determine expected MNO for the module
        if record:
            mno_code = "MNO1" if record["dm_server"] == "dm-server.mno1.com" else "MNO2"
            expected_settings = mno_settings_source.get_settings(mno_code)
            for k, v in expected_settings.items():
                assert settings[k] == v, f"{mod.get_sn()}: Setting '{k}' does not match MNO reference ({v}), found '{settings[k]}'"
        else:
            # Multi-MNO: checked separately in next step
            continue

        # b) Manufacturer process docs confirm values from MNO and include timestamp/evidence
        assert record["from_mno"], f"{mod.get_sn()}: Manufacturer record does not show settings sourced from MNO"
        assert "timestamp" in record, "Manufacturer record missing timestamp"

    # c) Multi-MNO support: Insert UICCs for different MNOs and check proper DM Server setting selection
    multi_mod = next(m for m in factory_modules if m.multi_mno_support)
    for mno_code in ["MNO1", "MNO2"]:
        uicc = MockUICC(imsi_prefix=f"IMSI-{mno_code}", mno_code=mno_code)
        multi_mod.insert_uicc_and_reload(uicc)
        settings = multi_mod.query_dm_server_settings()
        expected_settings = mno_settings_source.get_settings(mno_code)
        assert settings == expected_settings, f"Multi-MNO module failed to load correct settings for {mno_code}"
        print(f"For UICC MNO={mno_code}, loaded settings: {settings}")

    # d) Assert no out-of-date or default settings present for factory state
    for mod in factory_modules:
        settings = mod.query_dm_server_settings()
        for k, v in settings.items():
            assert v is not None and v != "" and "default" not in str(v).lower(), f"{mod.get_sn()}: Found default or missing setting '{k}'"

    # e) Print/log current settings and all relevant evidence for trace/audit
    for mod in factory_modules:
        print(f"Module: {mod.get_sn()}, settings: {mod.query_dm_server_settings()}")

def test_no_stale_or_missing_dm_server_settings(factory_modules, mno_settings_source):
    """Sanity check: No modules should ship with missing/stale/incorrect DM Server parameters."""
    for mod in factory_modules:
        settings = mod.query_dm_server_settings()
        # Simulate test that would compare with MNO's current config (direct check)
        dm_server_ref = {v["dm_server"] for k, v in mno_settings_source.mno_settings.items()}
        assert settings["dm_server"] in dm_server_ref, \
            f"{mod.get_sn()}: Factory-loaded dm_server '{settings['dm_server']}' is missing or stale."
```
---

**Instructions:**
- Save as `tests/test_comm_module_dm_server_settings_factory_load.py`.
- Replace mocks with your real device/OMA DM interrogation methods, actual manufacturer shipment/configuration records, and live/current MNO reference settings.
- For real multi-MNO modules, replace logic simulating UICC insertion and MNO mapping with your device's UICC profile detection and settings switch functionality.
- Run with:
  ```bash
  pytest tests/test_comm_module_dm_server_settings_factory_load.py
  ```
- All assertions and logs strictly map to GSMA TS.34_5.10_REQ_010 pass/fail/audit criteria for factory loading and differentiation of DM server settings.
- Easily extend for more modules, records, and MNOs as needed for batch/lab automation or CI.