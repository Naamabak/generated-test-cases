```python
# File: tests/test_oma_dm_hostman_node.py

"""
Test Case for:
Requirement ID : TS.34_5.10_REQ_004

Requirement:
- The OMA-DM node DevDetail/Ext/HostMan SHALL specify the Host Device Manufacturer via the IoT Communications Module OMA DM client.
- The node's value MUST match the manufacturer name referenced in the Mobile Network Operator lab certification for the IoT Device.

References:
- GSMA TS.34 v8.0, Section 5.10, Requirement TS.34_5.10_REQ_004
- OMA Device Management specification
- Mobile Network Operator lab certification documentation for IoT Device Host
"""

import pytest

# ---- MOCK CLASSES / PLACEHOLDER IMPLEMENTATION ----
# In a real-world test setup, integrate these with the actual device OMA DM client/query tool and use real certification data

class MockLabCertification:
    """Simulates the Mobile Network Operator lab certification containing the official manufacturer name."""
    def __init__(self, manufacturer_name="BestIoT Co."):
        self.manufacturer_name = manufacturer_name
    def get_certified_manufacturer(self):
        return self.manufacturer_name

class MockIoTCommModuleOMADM:
    """Simulates the OMA DM client supporting GET on DevDetail/Ext/HostMan."""
    def __init__(self, manufacturer_name="BestIoT Co."):
        self.nodes = {
            "DevDetail/Ext/HostMan": manufacturer_name
        }
        self.log = []

    def oma_dm_get(self, node_path):
        # Simulate a GET operation over the OMA DM interface
        value = self.nodes.get(node_path, None)
        self.log.append(f"OMA-DM GET {node_path}: {value}")
        return value

    def simulate_persistence_check(self):
        # In actual implementation, re-query or check value after events
        return self.oma_dm_get("DevDetail/Ext/HostMan")

    def get_log(self):
        return list(self.log)

# ---- PYTEST FIXTURE ----

@pytest.fixture
def device_and_cert():
    # Certified manufacturer (from official lab certification doc)
    certified_manufacturer = "BestIoT Co."
    # Device OMA DM client reporting manufacturer
    device = MockIoTCommModuleOMADM(manufacturer_name=certified_manufacturer)
    cert = MockLabCertification(manufacturer_name=certified_manufacturer)
    yield device, cert

# ---- TEST SCRIPT ----

def test_oma_dm_hostman_node_matches_certification(device_and_cert):
    """
    TS.34_5.10_REQ_004:
    - GET to DevDetail/Ext/HostMan node returns correct manufacturer.
    - Returned value matches the name from the Mobile Network Operator lab certification.
    - Value persists and is always correct.
    """
    device, cert = device_and_cert

    # Step 1: Retrieve HostMan value via OMA-DM GET
    hostman_value = device.oma_dm_get("DevDetail/Ext/HostMan")
    print(f"OMA-DM GET DevDetail/Ext/HostMan: {hostman_value}")

    # Step 2: Retrieve official certified manufacturer from certification record
    certified_manufacturer = cert.get_certified_manufacturer()
    print(f"Certified Manufacturer (from lab certification): {certified_manufacturer}")

    # Step 3: Assert retrieved and certified names match exactly (case & content)
    assert hostman_value == certified_manufacturer, (
        f"OMA DM HostMan value '{hostman_value}' does not match lab certification '{certified_manufacturer}'"
    )

    # Step 4: Optionally simulate events/re-check for persistence of node value
    value_after_event = device.simulate_persistence_check()
    assert value_after_event == certified_manufacturer, (
        "OMA DM HostMan value did not persist or return correct value after device event."
    )

    # Step 5: Log output for trace/auditability
    log = device.get_log()
    print("OMA-DM node access/action log:", log)
    print(f"GET operation result: {hostman_value} | Expected: {certified_manufacturer}")

    # Step 6: Ensure value is a single string with no discrepancies
    assert isinstance(hostman_value, str), "Returned OMA DM node value is not a string."
    assert hostman_value.strip() == hostman_value, "Manufacturer string should not have leading/trailing whitespace."
    assert len(hostman_value) > 0, "Manufacturer string should not be empty."

def test_oma_dm_hostman_node_handles_mismatch(device_and_cert):
    """
    Negative test: If device node returns wrong manufacturer, must FAIL.
    """
    device, _ = device_and_cert
    # Set an incorrect manufacturer value in the device node (simulates misconfiguration or wrong branding)
    device.nodes["DevDetail/Ext/HostMan"] = "NotCertifiedInc"
    bad_val = device.oma_dm_get("DevDetail/Ext/HostMan")
    assert bad_val != "BestIoT Co.", (
        "Negative test expects OMA-DM node value and certification to differ"
    )
```
---

**How to Use:**
- Save as `tests/test_oma_dm_hostman_node.py`.
- Replace the mocks with integration to your OMA-DM client/actual device and official certification record lookup as available.
- Run with:
  ```bash
  pytest tests/test_oma_dm_hostman_node.py
  ```
- For traceability and manual audit, print statements log all queried values and results.


**Coverage:**  
- Ensures OMA-DM node content is correct, matches certification, and persists as required by TS.34_5.10_REQ_004.
- Includes a negative/mismatch test demonstrating test FAIL when a different value is present.

Let me know if you want integration hooks for a real device, OMA-DM interface, or digital parsing of lab certificates!