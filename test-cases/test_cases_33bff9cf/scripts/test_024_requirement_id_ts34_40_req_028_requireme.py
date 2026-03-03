```python
# File: tests/test_dhir_node_reporting.py

"""
Test Case for:
Requirement ID : TS.34_4.0_REQ_028
Requirement: If the IoT Device contains a DHIR capable Communication Module and leverages the Communication Module’s IMEI TAC,
the IoT Device Application SHALL report (via secure method) the Host Device Manufacturer and Model custom nodes to the IoT Communications Module on:
 - initial communication
 - any node value change during device lifecycle

References:
- GSMA TS.34 v8.0, Section 4.0, TS.34_4.0_REQ_028
- GSMA TS.34 v8.0, Section 5.10, TS.34_5.10_REQ_004, TS.34_5.10_REQ_005
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
- OMA DM specification
"""

import pytest
import time

# --- MOCKS/PLACEHOLDERS (substitute with real interfaces for integration tests) ---

class MockCommModule:
    """
    Simulates a DHIR-capable Communications Module and monitors for secure node reports from the application.
    """
    def __init__(self):
        self.secure_reports = []
        self.last_received_nodes = {}
        self.last_method_secure = None  # (None/'plain'/'secure')

    def receive_node_report(self, nodes, secure_method):
        # secure_method: 'plain', 'secure'
        self.secure_reports.append({"nodes": nodes.copy(), "secure": secure_method})
        self.last_received_nodes = nodes.copy()
        self.last_method_secure = secure_method

    def report_log(self):
        return list(self.secure_reports)

    def reset(self):
        self.secure_reports.clear()
        self.last_received_nodes = {}
        self.last_method_secure = None

class MockIoTDeviceApplication:
    """
    Simulates the IoT Device Application under test.
    - Reports manufacturer and model nodes securely to the communication module.
    """
    def __init__(self, comm_module):
        self.comm_module = comm_module
        self.host_device_info = {
            "manufacturer": "AcmeIoT",
            "model": "SC-1000"
        }
        self.secure_channel_established = False

    def establish_secure_channel(self):
        self.secure_channel_established = True

    def initial_communication(self):
        """
        Called upon initial communication with the Communication Module.
        Sends Host Device Manufacturer and Model securely.
        """
        self.establish_secure_channel()
        self.comm_module.receive_node_report(nodes=self.host_device_info, secure_method="secure")

    def update_host_device_info(self, manufacturer=None, model=None):
        """
        Changes custom node values and triggers update/report if changed.
        """
        updated = False
        if manufacturer is not None and manufacturer != self.host_device_info["manufacturer"]:
            self.host_device_info["manufacturer"] = manufacturer
            updated = True
        if model is not None and model != self.host_device_info["model"]:
            self.host_device_info["model"] = model
            updated = True
        # For each change: send a new secure report (if secure channel is established)
        if updated and self.secure_channel_established:
            self.comm_module.receive_node_report(nodes=self.host_device_info, secure_method="secure")

    def send_report_insecure(self):
        """(Used for negative/edge case demo) Send report without security - should be caught in real test."""
        self.comm_module.receive_node_report(nodes=self.host_device_info, secure_method="plain")

    def reset(self):
        self.secure_channel_established = False

# --- PYTEST FIXTURES ---

@pytest.fixture
def comm_module():
    """Provides a fresh simulated Communication Module for each test."""
    cm = MockCommModule()
    yield cm
    cm.reset()

@pytest.fixture
def iot_device(comm_module):
    """Provides a fresh IoT Device Application instance per test."""
    app = MockIoTDeviceApplication(comm_module)
    yield app
    app.reset()
    comm_module.reset()

# --- TEST CASES ---

def test_initial_secure_node_report(iot_device, comm_module):
    """
    Step 1–2: At initial comms, device securely reports Host Device Manufacturer and Model to Comm Module.
    """
    iot_device.initial_communication()
    reports = comm_module.report_log()
    assert len(reports) == 1, "On initial communication, one node report should be sent."
    report = reports[0]
    # Check reported values
    assert "manufacturer" in report["nodes"] and "model" in report["nodes"], "Both nodes must be reported"
    assert report["nodes"]["manufacturer"] == "AcmeIoT"
    assert report["nodes"]["model"] == "SC-1000"
    # Check secure report
    assert report["secure"] == "secure", "Report must be sent using a secure method"

def test_update_and_re_report_on_change(iot_device, comm_module):
    """
    Step 3–4: When either node value changes, a new secure report is sent.
    """
    iot_device.initial_communication()
    # Change manufacturer, expect a new secure report
    iot_device.update_host_device_info(manufacturer="NewBrandIoT")
    reports = comm_module.report_log()
    # Should have two reports (initial + update)
    assert len(reports) == 2, "Second node report (update) should be sent after value change"
    # The newest report should reflect the update
    latest = reports[-1]
    assert latest["nodes"]["manufacturer"] == "NewBrandIoT"
    # Now, change only model
    iot_device.update_host_device_info(model="X-2000")
    reports = comm_module.report_log()
    assert len(reports) == 3, "Third node report (update) should be sent after second value change"
    latest = reports[-1]
    assert latest["nodes"]["model"] == "X-2000"
    # All updates sent over secure method
    for r in reports:
        assert r["secure"] == "secure", "All node reports must use secure communication"

def test_secure_method_enforced(iot_device, comm_module):
    """
    Step 5 & c: Node reporting must not be done using plain/unencrypted communication.
    """
    iot_device.initial_communication()
    iot_device.send_report_insecure()
    # There should be at least one insecure report in the log
    insecure_reports = [r for r in comm_module.report_log() if r["secure"] != "secure"]
    assert not insecure_reports, "All reports must be performed using a secure method"

def test_reporting_reflected_in_logs(iot_device, comm_module):
    """
    d) All node reporting activity can be traced in logs for verification.
    """
    iot_device.initial_communication()
    iot_device.update_host_device_info(model="QA-9000")
    log = comm_module.report_log()
    assert len(log) == 2
    models_reported = [r["nodes"]["model"] for r in log]
    assert models_reported == ["SC-1000", "QA-9000"]
    # Log is preserved for traceability
    print("Node reports (log):", log)

```

---

**How to Use / Customize:**
- Place as `tests/test_dhir_node_reporting.py`.
- Replace mocks with your actual device/module APIs and secure channel hooks.
- Run with:
  ```bash
  pytest tests/test_dhir_node_reporting.py
  ```
- Adapt secure reporting checks, node enums/names, and log captures as per your implementation or interface.

**Coverage:**
- Verifies **secure, not plain** reporting of manufacturer/model nodes
- Triggers and checks new report on each node value change
- Checks proper logging for auditability
- Cover all exit/pass/fail criteria listed in the test case

Let me know if you want this tailored to live OMA DM stack, real device, or automation harness!
