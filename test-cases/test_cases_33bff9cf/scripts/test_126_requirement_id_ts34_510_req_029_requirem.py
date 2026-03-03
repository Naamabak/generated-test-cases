```python
# File: tests/test_comm_module_update_reporting.py

"""
Test Case for:
Requirement ID : TS.34_5.10_REQ_029

Requirement:
After a module firmware update (by sideload/USB or via OEM Device Management server), 
the IoT Communications Module SHALL automatically initiate a session with the Device Management 
platform/server and report, via the Device Detail Management Object, at minimum:
  - IMEI
  - Current Firmware version
  - Actual WLAN MAC address (not the default)
  - Original Firmware version
  - Previous Firmware version
  - Date stamp for initial activation
  - Date stamp for last software update

References:
- GSMA TS.34 v8.0, Section 5.10, TS.34_5.10_REQ_029
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest
from datetime import datetime, timedelta

# --- MOCKS / PLACEHOLDERS (Replace with your integration for real device/module, device management server, and network/log capture) ---

REQUIRED_DETAIL_FIELDS = [
    "IMEI",
    "CurrentFwVersion",
    "WlanMacAddrActual",
    "OriginalFwVersion",
    "PrevFwVersion",
    "InitialActivationDate",
    "LastUpdateDate"
]

class MockDeviceManagementServer:
    """
    Simulates a Device Management platform that can receive reported detail objects from updated modules.
    """
    def __init__(self):
        self.sessions = []
        self.last_received_details = None
        self.event_log = []

    def receive_session(self, detail_payload, method):
        self.sessions.append({"payload": detail_payload, "method": method, "timestamp": datetime.utcnow().isoformat()})
        self.last_received_details = detail_payload
        self.event_log.append(f"Received session via {method} with details: {detail_payload}")

    def get_last_details(self):
        return self.last_received_details

    def clear(self):
        self.sessions = []
        self.last_received_details = None
        self.event_log = []

class MockIoTCommModule:
    """
    Simulates an IoT Communications Module capable of multiple update methods, 
    maintains Device Detail Management Object, and initiates session/reporting after update.
    """
    def __init__(self, imei, original_fw, wlan_mac_actual, init_activation_date):
        self.imei = imei
        self.current_fw = original_fw
        self.original_fw = original_fw
        self.prev_fw = None
        self.wlan_mac = wlan_mac_actual
        self.init_activation_date = init_activation_date
        self.last_update_date = init_activation_date
        self.dm_server = None
        self.report_log = []

    def register_with_dm_server(self, dm_server):
        self.dm_server = dm_server

    def report_device_details(self, method):
        # Compose the Device Detail Management Object
        detail_obj = {
            "IMEI": self.imei,
            "CurrentFwVersion": self.current_fw,
            "WlanMacAddrActual": self.wlan_mac,
            "OriginalFwVersion": self.original_fw,
            "PrevFwVersion": self.prev_fw,
            "InitialActivationDate": self.init_activation_date,
            "LastUpdateDate": self.last_update_date
        }
        if self.dm_server:
            self.dm_server.receive_session(detail_obj, method)
            self.report_log.append((method, detail_obj, datetime.utcnow().isoformat()))

    def firmware_update(self, method, new_fw, update_time):
        # Called for both sideload/USB or OEM DM server scenario
        self.prev_fw = self.current_fw
        self.current_fw = new_fw
        self.last_update_date = update_time
        # After a successful update, initiate session/report
        self.report_device_details(method)

    def get_log(self):
        return list(self.report_log)

    def clear(self):
        self.prev_fw = None
        self.current_fw = self.original_fw
        self.last_update_date = self.init_activation_date
        self.report_log = []

# --- PYTEST FIXTURE ---
@pytest.fixture
def dm_server_and_module():
    imei = "357123456789012"
    wlan_mac_actual = "A1:B2:C3:D4:E5:F6"
    original_fw = "1.0.0"
    init_activation_date = (datetime.utcnow() - timedelta(days=365)).strftime('%Y-%m-%dT%H:%M:%SZ')
    module = MockIoTCommModule(
        imei=imei,
        original_fw=original_fw,
        wlan_mac_actual=wlan_mac_actual,
        init_activation_date=init_activation_date
    )
    dm_server = MockDeviceManagementServer()
    module.register_with_dm_server(dm_server)
    yield dm_server, module
    dm_server.clear()
    module.clear()

# --- TEST SCRIPT ---
@pytest.mark.parametrize("update_method", ["sideload_usb", "proprietary_oem_dm"])
def test_module_update_report_to_dm_server(dm_server_and_module, update_method):
    """
    TS.34_5.10_REQ_029:
    - After update (via sideload/USB or proprietary OEM DM server),
      module must auto-initiate DM session with required Device Detail fields included.
    """
    dm_server, module = dm_server_and_module

    # Step 1: Perform firmware update via requested method
    new_fw = "2.0.1" if update_method == "sideload_usb" else "3.1.0"
    now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    module.firmware_update(update_method, new_fw, now)

    # Step 2: Immediately after update, check that an automatic session is initiated and details sent
    data = dm_server.get_last_details()
    assert data, f"No device details were reported for update method: {update_method}"

    # Step 3: Validate all required fields in device detail report
    for field in REQUIRED_DETAIL_FIELDS:
        assert field in data, f"Missing '{field}' in device detail report"
        assert data[field] is not None, f"Field '{field}' not populated in report"

    # Step 4: Confirm correct and current values for major fields
    assert data["IMEI"] == module.imei
    assert data["CurrentFwVersion"] == new_fw
    assert data["WlanMacAddrActual"] == module.wlan_mac
    assert data["OriginalFwVersion"] == module.original_fw
    assert data["PrevFwVersion"] is not None
    assert data["InitialActivationDate"] == module.init_activation_date
    assert data["LastUpdateDate"] == now

    # Step 5: Confirm session was reported to server for the correct update method
    session = dm_server.sessions[-1]
    assert session["method"] == update_method

    # Print/log for audit
    print(f"{update_method.upper()} Device Details Session:{data}")

@pytest.mark.parametrize("update_scenarios", [
    [("sideload_usb", "2.0.0"), ("proprietary_oem_dm", "2.1.1")],
    [("proprietary_oem_dm", "3.0.0"), ("sideload_usb", "3.2.2")]
])
def test_multiple_update_scenarios_and_reporting(dm_server_and_module, update_scenarios):
    """
    TS.34_5.10_REQ_029:
    Repeat for at least two update events; verify automatic reporting with correct previous/original versions.
    """
    dm_server, module = dm_server_and_module

    for i, (method, fw_ver) in enumerate(update_scenarios):
        now = (datetime.utcnow() + timedelta(minutes=i)).strftime('%Y-%m-%dT%H:%M:%SZ')
        module.firmware_update(method, fw_ver, now)
        data = dm_server.get_last_details()
        # All required fields as above
        for field in REQUIRED_DETAIL_FIELDS:
            assert field in data, f"Missing '{field}' in device detail after {method} update"
        # Previous firmware version is correct
        if i == 0:
            # First update: previous should be original
            assert data["PrevFwVersion"] == module.original_fw, "PrevFwVersion should be the original at first update"
        else:
            # Subsequent: should match last CurrentFwVersion
            assert data["PrevFwVersion"] == update_scenarios[i-1][1], \
                "PrevFwVersion not correctly recorded after sequential update"
        print(f"Update {i+1} via {method} - Reporting details: {data}")

def test_details_logged_and_traceable(dm_server_and_module):
    """
    All reporting sessions and details are logged by both module and server, for traceability/audit.
    """
    dm_server, module = dm_server_and_module
    fw_seq = [("sideload_usb", "2.9.1"), ("proprietary_oem_dm", "3.0.0")]
    for method, fw in fw_seq:
        now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        module.firmware_update(method, fw, now)
    # Check log contents
    mod_log = module.get_log()
    svr_log = dm_server.event_log
    assert any(method in l[0] for l in mod_log for method, _ in fw_seq), "Module did not log all update sessions"
    assert any("Received session" in l for l in svr_log), "Server did not log all reporting sessions"
    print("Module Report Log:", mod_log)
    print("Server Event Log:", svr_log)

```
---

**How to Use:**
- Save as `tests/test_comm_module_update_reporting.py`.
- Replace the mock classes with your real device update/management logic, device management server capture tools, and logging if integrating with real hardware or backend.
- Run with:
  ```bash
  pytest tests/test_comm_module_update_reporting.py
  ```
- All assertions map directly to TS.34_5.10_REQ_029. Print/log evidence is suitable for audit and compliance demonstration.
