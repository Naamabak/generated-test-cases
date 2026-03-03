```python
# File: tests/test_oma_dm_standard_object_support.py

"""
Test Case for:
Requirement ID : TS.34_5.10_REQ_023

Requirement:
The IoT Communications Module SHALL support the DevInfo, DevDetail and DMAcc objects as mandated in OMA Device Management Standard Objects v1.2 or v1.3 ([DMSTDOBJ_1.2] or [DMSTDOBJ_1.3]).

References:
- GSMA TS.34 v8.0, Section 5.10, Requirement TS.34_5.10_REQ_023
- OMA Device Management Standard Objects v1.2/v1.3 ([DMSTDOBJ_1.2], [DMSTDOBJ_1.3])
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest

# --- MOCKS/PLACEHOLDERS ---
# Replace these with actual OMA DM client/server & DM tree data in your testbed or device integration

MANDATORY_DEVINFO = {"Man", "Mod", "SwV", "DmV"}
MANDATORY_DEVDETAIL = {"DevTyp", "HwV", "FwV"}
MANDATORY_DMACC = {"ServerID", "Addr", "PortNbr"}  # Example, see OMA DM spec for full details

class MockOMADMTree:
    """
    Simulates or queries an IoT module's OMA DM tree for standard objects/nodes.
    In integration replace the tree with a live OMA DM query/response!
    """
    def __init__(self, version="1.3"):
        # Simulate full objects as per [DMSTDOBJ_1.2]/[DMSTDOBJ_1.3] for test environment
        self.version = version
        self.tree = {
            "./DevInfo": {
                "Man": "BestIoT",
                "Mod": "ModelPro",
                "SwV": "5.2.1",
                "DmV": "1.3",  # Device management version string
                # Add any other OMA-mandated DevInfo properties if needed
            },
            "./DevDetail": {
                "DevTyp": "IoTCommModule",
                "HwV": "A1",
                "FwV": "5.2.1-fw",
                # Add further mandatory properties if needed
            },
            "./DMAcc": {
                "ServerID": "testdm.example.com",
                "Addr": "https://testdm.example.com",
                "PortNbr": "443"
            }
        }

    def get_node(self, path):
        if path not in self.tree:
            raise KeyError(f"Node {path} not found in DM tree")
        return dict(self.tree[path])

    def get_tree_object_names(self):
        return set(self.tree.keys())

    def get_version(self):
        return self.version

# --- FIXTURE ---
@pytest.fixture(params=["1.2", "1.3"])
def dm_tree(request):
    # In real test, would use OMA DM server to query device and build the tree from live GET calls
    tree = MockOMADMTree(version=request.param)
    yield tree

# --- TEST SCRIPT ---
def test_oma_dm_standard_objects_and_properties(dm_tree):
    """
    - Ensure DevInfo, DevDetail, and DMAcc objects exist in DM tree
    - Each has all mandatory properties as per OMA DM v1.2/v1.3 standard objects
    - Validate GET responses for each property
    - Check that all required nodes/properties respond correctly
    """
    # Step 1: Query existence of standard objects
    object_names = dm_tree.get_tree_object_names()
    for obj in ["./DevInfo", "./DevDetail", "./DMAcc"]:
        assert obj in object_names, f"Standard OMA DM object {obj} missing from DM tree!"

    # Step 2: For each object, check mandatory property presence
    devinfo = dm_tree.get_node("./DevInfo")
    devdetail = dm_tree.get_node("./DevDetail")
    dmacc = dm_tree.get_node("./DMAcc")

    for prop in MANDATORY_DEVINFO:
        assert prop in devinfo, f"Mandatory property '{prop}' missing in DevInfo object!"

    for prop in MANDATORY_DEVDETAIL:
        assert prop in devdetail, f"Mandatory property '{prop}' missing in DevDetail object!"

    for prop in MANDATORY_DMACC:
        assert prop in dmacc, f"Mandatory property '{prop}' missing in DMAcc object!"

    # Step 3: Optionally, validate GET operation returns the correct value
    assert isinstance(devinfo["Man"], str) and devinfo["Man"], "DevInfo.Man property invalid"
    assert isinstance(devinfo["SwV"], str) and devinfo["SwV"], "DevInfo.SwV property invalid"
    assert isinstance(dmacc["Addr"], str) and "http" in dmacc["Addr"], "DMAcc.Addr property seems invalid"

    # Step 4: Print/log for traceability
    print(f"Tested OMA DM version: {dm_tree.get_version()}")
    print("DevInfo object:", devinfo)
    print("DevDetail object:", devdetail)
    print("DMAcc object:", dmacc)

@pytest.mark.parametrize("obj,missing_prop", [
    ("./DevInfo", "Man"),
    ("./DevDetail", "HwV"),
    ("./DMAcc", "ServerID"),
])
def test_missing_mandatory_property_fails(obj, missing_prop):
    """Negative test: if any mandatory property is missing, test MUST fail."""
    tree_dict = {
        "./DevInfo": {"Mod": "ModelPro", "SwV": "5.1.0", "DmV": "1.3"},  # Missing Man
        "./DevDetail": {"DevTyp": "IoTCommModule", "FwV": "5.2.1-fw"},  # Missing HwV
        "./DMAcc": {"Addr": "https://testdm.example.com", "PortNbr": "443"}  # Missing ServerID
    }
    tree = MockOMADMTree()
    tree.tree[obj] = tree_dict[obj]
    with pytest.raises(AssertionError):
        if obj == "./DevInfo":
            for prop in MANDATORY_DEVINFO:
                assert prop in tree.get_node(obj)
        elif obj == "./DevDetail":
            for prop in MANDATORY_DEVDETAIL:
                assert prop in tree.get_node(obj)
        elif obj == "./DMAcc":
            for prop in MANDATORY_DMACC:
                assert prop in tree.get_node(obj)

```
---
**Instructions:**
- Save as `tests/test_oma_dm_standard_object_support.py`.
- Replace mocks with live OMA DM server/device queries for production/lab/integration.
- Run with:
  ```bash
  pytest tests/test_oma_dm_standard_object_support.py
  ```
- The script asserts the presence and completeness of all mandatory OMA DM objects and required properties, per TS.34_5.10_REQ_023 and OMA DM standard specifications.
- The negative test demonstrates test failure when a required property is missing in any object.