```python
# File: tests/test_extended_access_barring.py

"""
Test Case for:
Requirement ID : TS.34_9.6_REQ_001

Requirement:
The IoT Device SHALL support Extended Access Barring (EAB) according to 3GPP and GSMA TS.34_9.6_REQ_001,
correctly recognizing and complying with EAB signaling broadcast by the network, and refraining from access
attempts when EAB restrictions apply to the device's access class.

References:
- GSMA TS.34 v8.0, Section 9.6, TS.34_9.6_REQ_001
- 3GPP TS 23.060 (EAB functionality), TS 36.331, TS 24.008
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf, page 59
"""

import pytest

# ---- MOCK/PLACEHOLDER CLASSES ----
# Replace with actual network and device control/integration in real system/lab testing.

class MockTestNetwork:
    """Simulates a test network supporting EAB signaling (can activate/deactivate EAB)."""
    def __init__(self):
        self.eab_active = False
        self.eab_barring_classes = set()
        self.logs = []

    def activate_eab(self, barred_classes=None):
        """Activate Extended Access Barring for specific access classes."""
        self.eab_active = True
        self.eab_barring_classes = set(barred_classes or [])
        self.logs.append(f"EAB activated for access classes: {self.eab_barring_classes}")

    def deactivate_eab(self):
        """Deactivate EAB."""
        self.eab_active = False
        self.eab_barring_classes = set()
        self.logs.append("EAB deactivated")

    def get_eab_state(self):
        return self.eab_active, set(self.eab_barring_classes)

    def get_logs(self):
        return list(self.logs)

    def reset(self):
        self.eab_active = False
        self.eab_barring_classes = set()
        self.logs.clear()

class MockIoTDevice:
    """
    Simulates an IoT Device that can recognize and comply with EAB, including tracking access class,
    recognizing EAB signaling, and managing access attempts accordingly.
    """
    def __init__(self, access_class):
        self.access_class = access_class
        self.network = None
        self.eab_indicated = False
        self.access_log = []
        self.last_bcch_info = None

    def register_on_network(self, network: MockTestNetwork):
        self.network = network
        # On registration, read current system information (including EAB from BCCH)
        self.update_from_bcch()

    def update_from_bcch(self):
        # Simulate system information (including EAB on BCCH)
        eab_active, barred_classes = self.network.get_eab_state()
        self.eab_indicated = eab_active and self.access_class in barred_classes
        self.last_bcch_info = (eab_active, barred_classes)
        self.access_log.append(f"BCCH update: EAB={'ON' if eab_active else 'OFF'}, barred={barred_classes}")

    def attempt_access(self, req_tag='generic_access'):
        # On every access attempt, refresh from BCCH and decide whether to proceed
        self.update_from_bcch()
        if self.eab_indicated:
            self.access_log.append(f"ACCESS BLOCKED by EAB: (class {self.access_class}) [{req_tag}]")
            return False
        self.access_log.append(f"ACCESS ATTEMPTED/ALLOWED: (class {self.access_class}) [{req_tag}]")
        return True

    def get_access_log(self):
        return list(self.access_log)

    def reset_log(self):
        self.access_log.clear()

    def reset(self):
        self.eab_indicated = False
        self.access_log = []
        self.last_bcch_info = None

# ---- PYTEST FIXTURES ----

@pytest.fixture
def test_network():
    net = MockTestNetwork()
    return net

@pytest.fixture(params=[7, 13], ids=["access_class_7", "access_class_13"])
def iot_device(request, test_network):
    # Choose access classes typical for IoT: 7-9, 12-14, etc. (see 3GPP/TS.34 docs for mapping)
    dev = MockIoTDevice(access_class=request.param)
    dev.register_on_network(test_network)
    yield dev
    dev.reset()

# ---- TEST SCRIPT ----

def test_device_allows_access_when_eab_not_active(iot_device, test_network):
    """(Step 1) EAB OFF: Device performs normal network access as expected."""
    test_network.deactivate_eab()
    iot_device.reset_log()
    for i in range(3):
        allowed = iot_device.attempt_access(f"pre-EAB-{i}")
        assert allowed, f"Device should be allowed access while EAB is not active (attempt {i})."
    print("Pre-EAB access log:", iot_device.get_access_log())

def test_device_blocks_access_when_eab_active_for_class(iot_device, test_network):
    """
    (Step 2-4) EAB ON: Device's access class is barred by EAB, access is blocked,
    device recognizes BCCH and complies with restriction.
    """
    # Act: Activate EAB for this device's access class (simulate network BCCH signal)
    test_network.activate_eab(barred_classes=[iot_device.access_class])
    iot_device.reset_log()

    # Try to access several times: all must be blocked
    for i in range(3):
        allowed = iot_device.attempt_access(req_tag=f"blocked-{i}")
        assert not allowed, f"Device (class {iot_device.access_class}) incorrectly tried access during EAB period."
    log = iot_device.get_access_log()
    assert all("BLOCKED" in entry for entry in log if "blocked-" in entry), "Not all attempts blocked during EAB."
    print("During-EAB access log:", log)

def test_device_resumes_access_when_eab_deactivated(iot_device, test_network):
    """(Step 5) After EAB lifted: Device resumes normal access (not blocked)."""
    # First block access
    test_network.activate_eab(barred_classes=[iot_device.access_class])
    iot_device.attempt_access(req_tag="blocked-check")
    # Then lift EAB
    test_network.deactivate_eab()
    iot_device.reset_log()
    for i in range(2):
        allowed = iot_device.attempt_access(req_tag=f"post-EAB-{i}")
        assert allowed, f"Device should resume access after EAB is deactivated (attempt {i})."
    print("Post-EAB access log:", iot_device.get_access_log())

@pytest.mark.parametrize("barred_classes,should_block", [
    ([7, 8, 10, 13], True),  # This device's class is included
    ([1, 2, 3, 15], False),  # This device's class is not included
])
def test_eab_barred_class_selection(iot_device, test_network, barred_classes, should_block):
    """
    (Step 6) EAB ON with different class configurations:
        - Device blocks when its access class is barred.
        - Device does NOT block when its class is not in barred_classes.
    """
    test_network.activate_eab(barred_classes=barred_classes)
    iot_device.reset_log()
    attempt = iot_device.attempt_access(req_tag="barred_class_test")
    if should_block:
        assert not attempt, f"Device with class {iot_device.access_class} should be barred by EAB."
    else:
        assert attempt, f"Device with class {iot_device.access_class} should NOT be barred by EAB."
    print("Barred-class test log:", iot_device.get_access_log())
```
---

**Usage:**
- Save as `tests/test_extended_access_barring.py`.
- For real integration, replace mock class logic with your actual device/network API.
- Run with:
  ```bash
  pytest tests/test_extended_access_barring.py
  ```
- Assertions and logs map to GSMA TS.34_9.6_REQ_001; print/logs provide audit trace for every phase (normal, EAB, after EAB, per-class selection).