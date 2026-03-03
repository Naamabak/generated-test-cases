```python
# File: tests/test_oma_dm_tstamp_property.py

"""
Test Case for:
Requirement ID : TS.34_5.10_REQ_017

Requirement:
The IoT Communications Module SHALL also support the TStamp property for DM 1.2/1.3 tree nodes (in addition to all mandatory node properties).

References:
- GSMA TS.34 v8.0, Section 5.10, Requirement TS.34_5.10_REQ_017
- OMA Device Management v1.2/v1.3 Specification [8], Node Property Descriptions
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest
from datetime import datetime, timedelta
import re

# ------- MOCK CLASSES / PLACEHOLDERS (Replace with real integration for device or testbed) -------

class MockDMTreeNode:
    """Simulates a DM node with support for mandatory and TStamp properties."""
    def __init__(self, name, value, format="chr", access_types=("Get",), tstamp=None, custom=False):
        self.name = name
        self.value = value
        self.format = format
        self.access_types = access_types
        self.tstamp = tstamp or datetime.utcnow().isoformat()
        self.custom = custom # Indicates if node is custom or standard

    def get_properties(self):
        return {
            "Name": self.name,
            "Format": self.format,
            "AccessTypes": self.access_types,
            "TStamp": self.tstamp,
            "Custom": self.custom,
        }

    def update_value(self, value):
        self.value = value
        self.tstamp = datetime.utcnow().isoformat()

class MockOMADMManagementTree:
    """Simulates the OMA DM management tree in the module."""
    def __init__(self):
        # Example tree with representative standard and custom nodes
        self.nodes = {
            "./DevInfo/Man": MockDMTreeNode("Man", "BestIoT Co."),
            "./DevInfo/Mod": MockDMTreeNode("Mod", "GSMA-RefModel"),
            "./DevInfo/SwV": MockDMTreeNode("SwV", "1.2.3"),
            "./DevDetail/FwV": MockDMTreeNode("FwV", "1.2.3-fw", format="chr"),
            "./Custom/HostParam": MockDMTreeNode("HostParam", "42", format="int", custom=True),
        }

    def get_all_node_paths(self):
        return list(self.nodes.keys())

    def get_node(self, path):
        return self.nodes.get(path, None)

    def update_node(self, path, value):
        node = self.get_node(path)
        if node:
            node.update_value(value)

    def enumerate_nodes_with_properties(self):
        return {path: node.get_properties() for path, node in self.nodes.items()}

# --- PYTEST FIXTURE ---

@pytest.fixture
def dm_tree():
    tree = MockOMADMManagementTree()
    yield tree
    # No teardown necessary for this mock

# --- TEST SCRIPT ---

def test_tstamp_property_present_and_maintained(dm_tree):
    """
    TS.34_5.10_REQ_017:
    TStamp property must be present and maintained (populated/updated) for standard and custom nodes in the OMA DM tree (v1.2/1.3).
    """
    # Step 1: Enumerate nodes from the management tree
    node_props = dm_tree.enumerate_nodes_with_properties()
    assert node_props, "No nodes found in DM tree!"

    for path, props in node_props.items():
        # Step 2: Check that TStamp property exists and is a valid timestamp string
        tstamp = props.get("TStamp")
        assert tstamp is not None, f"Node {path} missing TStamp property!"
        
        # Check ISO8601 format (primitive)
        match = re.match(r"^(\d{4})-(\d{2})-(\d{2})T\d{2}:\d{2}:\d{2}", tstamp)
        assert match, f"Node {path} has TStamp not in ISO8601 format: {tstamp}"

        # Step 3: Simulate updating node and ensure TStamp is updated
        prev_tstamp = tstamp
        dm_tree.update_node(path, f"updated-{props['Name']}-{datetime.utcnow().microsecond}")
        new_tstamp = dm_tree.get_node(path).get_properties()["TStamp"]
        assert new_tstamp != prev_tstamp, f"Node {path} TStamp not updated after value change"
        # Confirm updated TStamp is not older than previous
        assert new_tstamp > prev_tstamp, f"Node {path} TStamp update did not increment: {new_tstamp} <= {prev_tstamp}"

        # Print for audit trace
        print(f"Node: {path} | TStamp (old -> new): {prev_tstamp} -> {new_tstamp} | Custom: {props['Custom']}")

    # Step 4: Check that mandatory properties (Format, AccessTypes) are present as per OMA DM 1.2/1.3
    for path, props in node_props.items():
        assert "Format" in props and props["Format"], f"Node {path} missing Format property"
        assert "AccessTypes" in props and isinstance(props["AccessTypes"], tuple), f"Node {path} missing or malformed AccessTypes"

def test_tstamp_support_coverage_for_standard_and_custom_nodes(dm_tree):
    """
    Checks a representative set covering both standard and custom nodes.
    """
    node_paths = dm_tree.get_all_node_paths()
    std_found = custom_found = False
    for path in node_paths:
        node = dm_tree.get_node(path)
        assert node.tstamp is not None, f"TStamp not present for node {path}"
        if node.custom:
            custom_found = True
        else:
            std_found = True
    
    assert std_found, "No standard nodes detected in DM tree"
    assert custom_found, "No custom nodes detected in DM tree"

    print(f"Standard node(s) {', '.join([p for p in node_paths if not dm_tree.get_node(p).custom])} include TStamp")
    print(f"Custom node(s) {', '.join([p for p in node_paths if dm_tree.get_node(p).custom])} include TStamp")

```
---
**How to use/adapt:**
- Save as `tests/test_oma_dm_tstamp_property.py`.
- Replace the mocks with your actual OMA DM tree API or device interface that supports property enumeration and value update.
- Run with:
  ```bash
  pytest tests/test_oma_dm_tstamp_property.py
  ```
- The script covers TStamp presence, correct format, maintenance (updated on value write), and checks a variety of node types, mapping exactly to GSMA TS.34_5.10_REQ_017.

Let me know if you need coverage for tree enumeration over device API, or to connect with live device integration!