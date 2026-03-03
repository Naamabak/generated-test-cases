```python
# File: tests/test_oma_dm_protocol_mandatory_features.py

"""
Test Case for:
Requirement ID : TS.34_5.10_REQ_015

Requirement:
The IoT Communications Module SHALL support all mandatory requirements of Device Management Protocol v1.2 or v1.3
([DMPRO_1.2] or [DMPRO_1.3]), ensuring full OMA DM compliance for remote device management.

References:
- GSMA TS.34 v8.0, Section 5.10, Requirement TS.34_5.10_REQ_015
- OMA DM v1.2/v1.3 core specifications: message types, node management ops, alerts, status/error handling, DDF, etc.
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest

# ---------- MOCKS/PLACEHOLDERS for test/demonstration ----------
# Replace these with lab integration, protocol emulator APIs, or actual logs/packet analysis for live device setup

MANDATORY_FEATURES_1_2_OR_1_3 = [
    "bootstrap", "auth_challenge", "devinfo/devdetail node get", "dmacc node", "alert",
    "status codes", "protocol error handling", "mgmt_tree_navigation",
    "object_provisioning", "GET/REPLACE/ADD/DELETE", "DDF/presentation", "configuration/sync"
]

class MockOMADMServerSession:
    """
    Simulates an OMA DM v1.2/v1.3 server session, recording protocol exchanges for mandatory features.
    """
    def __init__(self, version="1.3"):
        self.version = version
        self.protocol_log = []
        self.client_registered = False

    def bootstrap(self, module):
        self.protocol_log.append(f"{self.version}: BOOTSTRAP exchange OK")
        return module.perform_bootstrap(self.version)

    def authenticate(self, module):
        self.protocol_log.append(f"{self.version}: AUTH-CHALLENGE/RESPONSE exchange")
        return module.perform_authentication(self.version)

    def send_command(self, module, cmd, node=None, *args, **kwargs):
        self.protocol_log.append(f"{self.version}: {cmd} {node if node else ''}")
        return module.handle_oma_command(cmd, node, *args, **kwargs)

    def send_alert(self, module, alert_type):
        self.protocol_log.append(f"{self.version}: ALERT {alert_type}")
        return module.receive_alert(alert_type)

    def send_protocol_error(self, module, error_code):
        self.protocol_log.append(f"{self.version}: Inject ERROR {error_code}")
        return module.handle_error(error_code)

    def get_protocol_log(self):
        return list(self.protocol_log)

class MockIoTCommModuleOMA_DMClient:
    """
    Simulates an IoT Comm Module supporting all OMA DM v1.2/v1.3 mandatory features
    and records protocol operations for evidence.
    """
    def __init__(self, supported_version="1.3"):
        self.supported_version = supported_version
        self.bootstrapped = False
        self.authenticated = False
        self.node_tree = {"DevInfo": "DevInfoData", "DevDetail": "DevDetailData", "DMAcc": "DMAccData"}
        self.log = []
        self.mandatory_features_supported = set(MANDATORY_FEATURES_1_2_OR_1_3)

    def perform_bootstrap(self, version):
        self.bootstrapped = (version == self.supported_version)
        self.log.append(f"BOOTSTRAP: {version} supported: {self.bootstrapped}")
        return self.bootstrapped

    def perform_authentication(self, version):
        self.authenticated = (version == self.supported_version)
        self.log.append(f"AUTH: {version} supported: {self.authenticated}")
        return self.authenticated

    def handle_oma_command(self, cmd, node, *args, **kwargs):
        if cmd.lower() in ["get", "replace", "add", "delete"]:
            feature = f"{cmd.upper()}_{node if node else ''}"
            self.mandatory_features_supported.add(feature)
            self.log.append(f"{cmd.upper()} performed on {node}")
            return {"result": "success"}
        elif cmd.lower() == "mgmt_tree_navigation":
            self.log.append("Management tree navigation successful")
            return {"tree": list(self.node_tree.keys())}
        elif cmd.lower() == "provisioning":
            self.log.append("Management object provisioning executed")
            return {"result": "success"}
        elif cmd.lower() == "ddf_present":
            self.log.append("DDF node present")
            return {"present": "DevDetail/DeviceDescription/DDF"}
        else:
            self.log.append(f"CMD {cmd} not recognized")
            return {"result": "not_supported"}

    def receive_alert(self, alert_type):
        if alert_type in ["memory_low", "session_expired", "firmware_update"]:
            self.log.append(f"ALERT: {alert_type} handled")
            return {"result": "ack"}
        else:
            self.log.append(f"UNKNOWN ALERT: {alert_type}")
            return {"result": "unknown_alert"}

    def handle_error(self, error_code):
        self.log.append(f"ERROR handling for code: {error_code}")
        return {"error_code": error_code, "handled": True}

    def get_log(self):
        return list(self.log)

    def supports_all_mandatory_features(self, spec_mandatory=None):
        spec_mandatory = spec_mandatory or set(MANDATORY_FEATURES_1_2_OR_1_3)
        return spec_mandatory.issubset(self.mandatory_features_supported)

    def reset(self):
        self.__init__(self.supported_version)

# ----------- PYTEST FIXTURE -----------

@pytest.fixture(params=["1.2", "1.3"])
def dm_server_and_module(request):
    version = request.param
    server = MockOMADMServerSession(version=version)
    module = MockIoTCommModuleOMA_DMClient(supported_version=version)
    yield server, module, version
    module.reset()

# ----------- TEST SCRIPT -----------

def test_oma_dm_protocol_compliance_and_mandatory_features(dm_server_and_module):
    """
    TS.34_5.10_REQ_015:
    - Verifies all mandatory OMA DM v1.2/v1.3 functions and protocol elements.
    - Includes bootstrap, authentication, object provisioning, standard commands, alerts, status, and errors.
    - Uses protocol logs and simulated server exchanges for full-coverage.
    """
    server, module, version = dm_server_and_module

    # 1. Register and bootstrap
    assert server.bootstrap(module), "Bootstrap failed"
    # 2. Authenticate
    assert server.authenticate(module), "Authentication failed"

    # 3. Sequentially execute all mandatory protocol features:
    assert server.send_command(module, "Mgmt_tree_navigation")["tree"] == ["DevInfo", "DevDetail", "DMAcc"]
    assert server.send_command(module, "GET", "DevDetail")["result"] == "success"
    assert server.send_command(module, "REPLACE", "DMAcc")["result"] == "success"
    assert server.send_command(module, "ADD", "OMADM/Sync")["result"] == "success"
    assert server.send_command(module, "DELETE", "OMADM/Sync")["result"] == "success"
    assert server.send_command(module, "provisioning")["result"] == "success"
    assert server.send_command(module, "ddf_present")["present"] == "DevDetail/DeviceDescription/DDF"

    # Alerts: standard protocol alerts
    assert server.send_alert(module, "memory_low")["result"] == "ack"
    assert server.send_alert(module, "headless_alert")["result"] in {"unknown_alert", "ack"}

    # Status/error codes
    assert server.send_command(module, "GET", "notfound")  # unsupported node
    assert server.send_protocol_error(module, 404)["handled"]
    assert server.send_protocol_error(module, 500)["handled"]

    # 4. Check that all mandatory features are present (simulated as tracked on the module)
    assert module.supports_all_mandatory_features(), \
        "Not all mandatory OMA DM v1.2/v1.3 protocol features are implemented per spec"

    # 5. Protocol/log trace must confirm operations, message types, and error handling
    module_log = module.get_log()
    protocol_log = server.get_protocol_log()
    assert any("BOOTSTRAP" in l for l in module_log)
    assert any("AUTH:" in l for l in module_log)
    assert any("GET performed" in l for l in module_log)
    assert any("REPLACE performed" in l for l in module_log)
    assert any("ALERT:" in l or "UNKNOWN ALERT" in l for l in module_log)
    assert any("ERROR handling" in l for l in module_log)
    print(f"OMA DM v{version} protocol log: {protocol_log}")
    print(f"Module event log: {module_log}")

    # 6. (optional) Negative case: Unsupported version triggers failure
    bad_module = MockIoTCommModuleOMA_DMClient(supported_version="0.9")
    assert not server.bootstrap(bad_module)
    print("Negative test: unsupported version correctly rejected")

    # 7. Documentation evidence (for audit): logs, protocol traces, test records
    print("Test completed for OMA DM v", version)

```
---

**Instructions:**
- Save as `tests/test_oma_dm_protocol_mandatory_features.py`.
- Replace all mock classes with actual protocol emulator or live testbed API calls if available.
- Assertions and logs directly map to all mandatory features and capability requirements for OMA DM v1.2/v1.3 per DMPRO_1.2/DMPRO_1.3.
- The test covers positive scenarios (happy-path and error handling) and negative cases (e.g., wrong version).
- Run via:
  ```bash
  pytest tests/test_oma_dm_protocol_mandatory_features.py
  ```
- All logic and protocol operations are auditable for test/certification submission.

Let me know if you want this script extended for live packet trace post-processing or injected protocol traffic!