```python
# File: tests/test_data_end_to_end_encryption.py

"""
Test Case for:
Requirement ID : TS.34_4.0_REQ_021
Requirement: All data sent between the IoT Device Application and the IoT Service Platform SHOULD be end-to-end encrypted with security appropriate for the IoT Service—unless explicitly not required.

References:
- GSMA TS.34 v8.0, Section 4.0, TS.34_4.0_REQ_021
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest
import base64

# -------- MOCK/PLACEHOLDER CLASSES (Replace with real APIs/capture in production) --------

class MockIoTDeviceApplication:
    """Simulates sending and receiving application-level (E2E) encrypted data."""
    def __init__(self, encryption_required=True, algo="AES-256", documented_strength=256):
        self.encryption_required = encryption_required
        self.algorithm = algo
        self.key_strength = documented_strength  # bits

    def send_data(self, payload):
        # In real implementation: data would be application-encrypted (e.g., using TLS, DTLS, or app payload encryption)
        if self.encryption_required:
            # Simulate encryption by base64-encoding and mixing a non-plaintext pattern
            cipher_text = base64.b64encode(bytes("ENCRYPTED:" + payload, "utf-8"))
            return cipher_text
        else:
            # No encryption (plaintext)
            return bytes(payload, "utf-8")

    def get_encryption_details(self):
        return {
            "algorithm": self.algorithm,
            "key_strength": self.key_strength,
            "required": self.encryption_required,
        }

class MockIoTServicePlatform:
    """Simulates the Service Platform that sends/receives encrypted data and knows its own policies."""
    def __init__(self, security_policy=None):
        self.security_policy = security_policy or {"encryption_required": True, "algorithm": "AES-256", "key_strength": 256}
        self.rx_captured = None

    def receive_data(self, data):
        self.rx_captured = data

    def get_security_policy(self):
        return self.security_policy

# -------- TEST FIXTURES --------

@pytest.fixture
def device_and_platform():
    """Setup for a typical IoT service with required encryption."""
    # In a real test, load configuration from policy/document/IoT Service API
    platform_policy = {"encryption_required": True, "algorithm": "AES-256", "key_strength": 256}
    device = MockIoTDeviceApplication(**platform_policy)
    platform = MockIoTServicePlatform(security_policy=platform_policy)
    return device, platform

@pytest.fixture
def device_and_platform_no_encryption():
    """Setup for an IoT service where encryption is not required by documented service context."""
    platform_policy = {"encryption_required": False, "algorithm": None, "key_strength": None}
    device = MockIoTDeviceApplication(**platform_policy)
    platform = MockIoTServicePlatform(security_policy=platform_policy)
    return device, platform

# -------- TESTS --------

def test_end_to_end_encryption_applied_and_strength_documented(device_and_platform):
    """
    a) Data is encrypted in transit.
    b) Encryption meets service policy for strength and method.
    """
    device, platform = device_and_platform

    # Step 1: Initiate transmission from device to platform
    secret_payload = "sensor_reading:temperature:25.2"
    encrypted_data = device.send_data(secret_payload)

    # Step 2: Capture what is sent "on the wire"
    platform.receive_data(encrypted_data)

    # Step 3: Analyze captured data to confirm non-plaintext (i.e., encrypted)
    on_the_wire = platform.rx_captured
    try:
        as_text = on_the_wire.decode("utf-8")
    except Exception as e:
        as_text = ""  # expected for binary data

    assert not secret_payload in as_text, (
        "Payload is readable in transit! Expected end-to-end encryption."
    )
    assert b"ENCRYPTED:" in base64.b64decode(on_the_wire), (
        "Test mock: data did not follow simulated encryption format."
    )

    # Step 4: Check encryption documented and has appropriate strength
    device_details = device.get_encryption_details()
    policy = platform.get_security_policy()
    assert device_details["algorithm"] == policy["algorithm"]
    assert device_details["key_strength"] >= policy["key_strength"]
    assert device_details["required"] is True

    # Optional: print out for debug
    print("Encryption details:", device_details)

def test_no_encryption_when_explicitly_not_required(device_and_platform_no_encryption):
    """
    c) If encryption is NOT required (by policy), data can be sent in clear but must be documented as such.
    """
    device, platform = device_and_platform_no_encryption

    # Step 1: Initiate transmission from device to platform, expecting plaintext
    secret_payload = "alarm:door:open"
    plain_data = device.send_data(secret_payload)
    platform.receive_data(plain_data)

    # Step 2: Analyze captured data must be clear and match payload
    on_the_wire = platform.rx_captured
    as_text = on_the_wire.decode("utf-8")
    assert secret_payload in as_text, (
        "Payload not visible in transit, but encryption is not required by service policy."
    )

    # Step 3: Confirm policy/documentation explicitly allows for this case
    device_policy = device.get_encryption_details()
    platform_policy = platform.get_security_policy()
    assert device_policy["required"] is False
    assert platform_policy["encryption_required"] is False

    print("No encryption required per service policy and correctly handled.")

```

---

**How to Use / Customize:**
- Place as `tests/test_data_end_to_end_encryption.py`.
- Replace `MockIoTDeviceApplication` and `MockIoTServicePlatform` with real device/app SDK calls and network traffic capture in a real testbed.
- Use real encryption analysis tools (e.g., Wireshark, packet dissection, application layer decrypt check) in integration tests.
- Run this test with:
  ```sh
  pytest tests/test_data_end_to_end_encryption.py
  ```

---

**What is covered:**
- Validates data in transit is not readable unless explicitly allowed.
- Ensures documentation and config for encryption key strength and algorithm.
- Supports both required and exception (no encryption) scenarios.
- Ready for adaptation to wire-level packet or PCAP analysis.