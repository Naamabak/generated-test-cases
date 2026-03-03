```python
# File: tests/test_oma_dm_imeisv_node.py

"""
Test Case for:
Requirement ID: TS.34_5.10_REQ_021

Requirement:
- The IoT Communications Module SHALL implement the DevDetail/Ext/IMEISV node.
- It SHALL return ONLY the IMEI SV (Software Version, 2-digit numeric string) on GET.
- The IMEI (without SV) is reported in DevInfo/DevId node.
- SV and IMEI nodes must be separately queryable, accurate, and consistent.

References:
- GSMA TS.34 v8.0, Section 5.10, TS.34_5.10_REQ_021
- OMA Device Management specification [8]
- 3GPP TS 22.016 (IMEI/SV structure and reporting)
"""

import pytest
import re

# --------- MOCK IMPLEMENTATION (Replace with actual module OMA DM client interface in integration/system tests) ---------

class MockIoTCommModuleOMADMClient:
    """
    Simulates a running OMA DM client on an IoT Communications Module.
    Provides GET operations to standard and extension nodes.
    """
    def __init__(self, imei="357123456789012", sv="05"):
        """
        imei: Full 14/15 digit IMEI string (excluding or including checksum)
        sv:   2-digit software version string as per GSMA/3GPP standards
        """
        self.nodes = {
            "DevInfo/DevId": imei,                  # Should be 14 (or 15) digits, IMEI only
            "DevDetail/Ext/IMEISV": sv              # SV only (Software Version) as 2-digit numeric string
        }
        # For test, assert expected format at creation
        assert re.fullmatch(r"\d{14,15}", imei), "IMEI should be 14 or 15 digits"
        assert re.fullmatch(r"\d{2}", sv), "SV must be a 2-digit numeric string"
        self.imei = imei
        self.sv = sv
        self.get_count = {k: 0 for k in self.nodes}

    def oma_dm_get(self, node_path):
        if node_path not in self.nodes:
            raise KeyError(f"Node {node_path} not available")
        self.get_count[node_path] += 1
        return self.nodes[node_path]

    def oma_dm_set(self, node_path, value):
        """
        SV node must NOT be writable. DevInfo/DevId is read-only.
        """
        if node_path == "DevDetail/Ext/IMEISV":
            raise PermissionError("IMEISV node is read-only (GET only)")
        if node_path == "DevInfo/DevId":
            raise PermissionError("DevId node is read-only (GET only)")
        self.nodes[node_path] = value

    def get_get_count(self, node_path):
        return self.get_count[node_path]

    def simulate_sv_update(self, new_sv):
        assert re.fullmatch(r"\d{2}", new_sv)
        self.sv = new_sv
        self.nodes["DevDetail/Ext/IMEISV"] = new_sv

    def get_all_values(self):
        return dict(self.nodes)

# ------------ FIXTURES ------------

@pytest.fixture
def module():
    # Example IMEI and SV, as would appear on a real module/device
    imei = "357123456789012"
    sv = "05"  # For test, the SV is the last two digits (for IMEI SV: usually serial+SV or per documentation)
    mod = MockIoTCommModuleOMADMClient(imei=imei, sv=sv)
    yield mod

# ------------ TEST SCRIPT ------------

def test_imei_and_sv_oma_dm_nodes(module):
    """
    TS.34_5.10_REQ_021:
    - DevInfo/DevId (GET) returns the full IMEI, but NOT the SV.
    - DevDetail/Ext/IMEISV (GET) returns only the 2-digit SV (Software Version).
    - SV and IMEI values are accurate and consistent with device documentation.
    - DevDetail/Ext/IMEISV is not writable.
    - No discrepancies on repeated queries.
    """

    # Step 1: GET DevInfo/DevId, check IMEI
    dev_id_val = module.oma_dm_get("DevInfo/DevId")
    # IMEI: 14 or 15 digits, numeric
    assert re.fullmatch(r"\d{14,15}", dev_id_val), f"DevId (IMEI) format invalid: {dev_id_val}"
    # Ensure it does NOT include SV
    assert not dev_id_val.endswith(module.sv), (
        f"DevInfo/DevId should NOT include SV (should be just IMEI): got {dev_id_val}"
    )

    # Step 2: GET DevDetail/Ext/IMEISV, check SV format and value
    sv_val = module.oma_dm_get("DevDetail/Ext/IMEISV")
    assert re.fullmatch(r"\d{2}", sv_val), f"IMEISV value is not a 2-digit numeric string: {sv_val}"

    # Step 3: Cross-check SV value against expected value (e.g., from device/AT+CGSN)
    expected_sv = module.sv
    assert sv_val == expected_sv, (
        f"IMEISV node reports {sv_val}, but expected {expected_sv} as per device"
    )

    # Step 4: Ensure IMEI node does NOT contain SV, only IMEI
    assert dev_id_val == module.imei

    # Step 5: Ensure SV node does NOT contain IMEI
    assert sv_val != dev_id_val

    # Step 6: Attempt to write to SV node (should fail)
    with pytest.raises(PermissionError):
        module.oma_dm_set("DevDetail/Ext/IMEISV", "99")

    # Step 7: Replicate GET multiple times, confirm consistent response
    sv_vals = [module.oma_dm_get("DevDetail/Ext/IMEISV") for _ in range(3)]
    imei_vals = [module.oma_dm_get("DevInfo/DevId") for _ in range(3)]
    assert all(v == sv_val for v in sv_vals), f"Inconsistent SV GET response across queries: {sv_vals}"
    assert all(v == dev_id_val for v in imei_vals), f"Inconsistent IMEI GET response across queries: {imei_vals}"

    # Step 8: Simulate SV change and confirm node update
    new_sv = "07"
    module.simulate_sv_update(new_sv)
    sv_after = module.oma_dm_get("DevDetail/Ext/IMEISV")
    assert sv_after == new_sv, "SV node value not updated after SV change"

    # Step 9: Try to GET missing node (should error)
    with pytest.raises(KeyError):
        module.oma_dm_get("DevDetail/Ext/BogusNode")

    print(f"DevInfo/DevId (IMEI): {dev_id_val}")
    print(f"DevDetail/Ext/IMEISV (SV): {sv_val}, after update: {sv_after}")

    # Exit Criteria (Pass/Fail summary in asserts above)

```
---

**How to use:**

- Save as `tests/test_oma_dm_imeisv_node.py`.
- Integrate with your actual OMA DM interface for live/hardware/product test.
- Run with:
  ```bash
  pytest tests/test_oma_dm_imeisv_node.py
  ```

**Covers:**
- IMEI and SV separation across nodes.
- Format and value checks for both.
- Node read-only (GET-only) enforcement for SV.
- Device documentation, AT+CGSN, or labeling alignment.
- Query repeatability and consistency per TS.34_5.10_REQ_021.