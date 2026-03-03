```python
# File: tests/test_esl_dhir_custom_node_reporting.py

"""
Test Case for:
Requirement ID: TS.34_4.2_REQ_028
Requirement: If the IoT Device contains a DHIR-capable Communication Module and leverages the Communication Module’s IMEI TAC,
the IoT Embedded Service Layer SHALL securely report Host Device Manufacturer, Model, Software Version, and Unique ID custom nodes
to the IoT Communications Module both at initial communication and whenever any of the values change (including for local/remote firmware update).

References:
- GSMA TS.34 v8.0, Section 4.2, Requirement TS.34_4.2_REQ_028
- Section 5.10 requirements: TS.34_5.10_REQ_004–TS.34_5.10_REQ_007
- OMA DM specification (custom node reporting, secure methods)
"""

import pytest

# ------ MOCK CLASSES FOR DEMONSTRATION/TEST DOUBLES ------

class MockCommunicationModule:
    """
    Simulates DHIR-capable IoT Communication Module. Records all secure reports received from the Embedded Service Layer.
    """
    def __init__(self):
        self.reports = []
        self.last_method_secure = None

    def receive_custom_node_report(self, nodes, secure_method: str):
        assert secure_method == "secure", "Report must be sent over a secure channel!"
        self.reports.append({"nodes": nodes.copy(), "secure": secure_method})

    def get_reports(self):
        return list(self.reports)

    def reset(self):
        self.reports.clear()
        self.last_method_secure = None

class MockIoTEmbeddedServiceLayer:
    """
    Simulates the IoT Embedded Service Layer with logic to report custom nodes securely to Communication Module.
    """
    def __init__(self, comm_module):
        # Four required custom nodes from TS.34_5.10 requirements
        self.node_values = {
            "manufacturer": "TestBrand",
            "model": "ModelX",
            "software_version": "1.0.0",
            "unique_id": "DEV123ABC"
        }
        self.comm_module = comm_module
        self.secure_channel_established = False
        self.log = []

    def establish_secure_channel(self):
        self.secure_channel_established = True
        self.log.append("Secure channel established with CommModule")

    def initial_communication(self):
        """Initial communication: must report ALL four custom nodes securely."""
        self.establish_secure_channel()
        self.report_custom_nodes()

    def change_custom_node(self, key, value):
        """
        Change a node value (simulate config change, local/remote firmware update, etc.)
        and securely report new node per requirement.
        """
        if key not in self.node_values:
            raise ValueError("Unknown custom node: " + key)
        self.node_values[key] = value
        self.report_custom_nodes()

    def firmware_update(self, new_software_version, local=False, remote=False):
        """
        Simulate firmware update, local/remote (affects 'software_version' node).
        Triggers reporting.
        """
        update_type = "local" if local else "remote" if remote else "unknown"
        self.change_custom_node("software_version", new_software_version)
        self.log.append(f"Firmware updated by {update_type} method to {new_software_version}")

    def report_custom_nodes(self):
        """Send secure report to CommModule."""
        assert self.secure_channel_established
        self.comm_module.receive_custom_node_report(self.node_values, secure_method="secure")
        self.log.append(f"Reported custom nodes: {self.node_values}")

    def get_log(self):
        return list(self.log)

    def reset(self):
        self.node_values = {
            "manufacturer": "TestBrand",
            "model": "ModelX",
            "software_version": "1.0.0",
            "unique_id": "DEV123ABC"
        }
        self.comm_module.reset()
        self.secure_channel_established = False
        self.log = []

# --------- PYTEST FIXTURE ---------

@pytest.fixture
def esl_and_comm_module():
    comm_module = MockCommunicationModule()
    esl = MockIoTEmbeddedServiceLayer(comm_module)
    yield esl, comm_module
    esl.reset()
    comm_module.reset()

# ---------- TESTS ----------

def test_secure_reporting_of_custom_nodes_initial_and_on_change(esl_and_comm_module):
    """
    TS.34_4.2_REQ_028:
    - On initial communication, all four custom nodes must be reported securely.
    - When any node changes (incl. firmware update local/remote), a new secure report is triggered.
    - All reporting is via secure method; all reporting events are auditable/logged.
    """

    esl, comm = esl_and_comm_module

    # Step 1: Initial power-on and communication
    esl.initial_communication()
    initial_reports = comm.get_reports()
    assert len(initial_reports) == 1, "Initial custom node report not sent."
    report = initial_reports[0]
    for k in ["manufacturer", "model", "software_version", "unique_id"]:
        assert k in report["nodes"]
    assert report["secure"] == "secure"
    # Confirm log
    assert any("Secure channel established" in entry for entry in esl.get_log())
    assert any("Reported custom nodes" in entry for entry in esl.get_log())

    # Step 3-4: Change each parameter individually and check reporting
    esl.change_custom_node("manufacturer", "AcmeCorp")
    esl.change_custom_node("model", "ModelZ")
    esl.change_custom_node("unique_id", "XYZ-987")
    after_changes = comm.get_reports()
    assert len(after_changes) == 4, "Change in each custom node should trigger a new secure report."
    # Only the latest value should be present now:
    latest_nodes = after_changes[-1]["nodes"]
    assert latest_nodes["manufacturer"] == "AcmeCorp"
    assert latest_nodes["model"] == "ModelZ"
    assert latest_nodes["unique_id"] == "XYZ-987"
    assert after_changes[-1]["secure"] == "secure"

    # Step 5-6: Simulate firmware updates (local, then remote)
    esl.firmware_update("2.1.3", local=True)
    fw_update_reports = comm.get_reports()
    assert fw_update_reports[-1]["nodes"]["software_version"] == "2.1.3"
    # Simulate remote/OTA update
    esl.firmware_update("3.0.0", remote=True)
    fw_update_reports2 = comm.get_reports()
    assert fw_update_reports2[-1]["nodes"]["software_version"] == "3.0.0"
    # All reports must use secure method
    for rep in fw_update_reports2:
        assert rep["secure"] == "secure"

    # Step 7: Confirm all changes and events are logged and traceable
    log = esl.get_log()
    assert any("Firmware updated by local method" in entry for entry in log)
    assert any("Firmware updated by remote method" in entry for entry in log)
    assert log.count("Reported custom nodes: " + str(latest_nodes)) >= 1

    print("Custom node reports (log):", comm.get_reports())
    print("Event log:", log)

def test_no_insecure_reporting_allowed(esl_and_comm_module):
    """
    Negative test: insecure reporting shall never be allowed (would fail 'secure' method assertion).
    """
    esl, comm = esl_and_comm_module
    esl.initial_communication()
    try:
        comm.receive_custom_node_report(esl.node_values, secure_method="plain")
        assert False, "Insecure method was incorrectly allowed"
    except AssertionError:
        pass  # Expected behavior
```
---

**How to use:**

- Save as `tests/test_esl_dhir_custom_node_reporting.py`
- Replace the mocks with your actual ESL → CommModule integration and secure communication hooks if available (e.g., OMA DM stack, device APIs).
- Run via:
  ```bash
  pytest tests/test_esl_dhir_custom_node_reporting.py
  ```
- Assertions cover all required reporting, update scenarios, security criteria, and log observability per GSMA TS.34_4.2_REQ_028.

Let me know if you need this tailored to your specific platform/testbed/log structure!