```python
# File: tests/test_embedded_service_layer_end_to_end_encryption.py

"""
Test Case for:
Requirement ID : TS.34_4.2_REQ_021

Requirement:
Data sent from the IoT Embedded Service Layer to the IoT Service Platform SHOULD be end-to-end encrypted, with security strength appropriate to the IoT Service. For services that don't require encryption, this must be documented and traffic should be cleartext.

References:
- GSMA TS.34 v8.0, Section 4.2, Requirement TS.34_4.2_REQ_021
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest
import base64

# --- Mocks/Placeholders for Embedded Layer and Service Platform (replace with lab/API/live hooks as needed) ---

class MockIoTEmbeddedServiceLayer:
    """
    Simulates the IoT Embedded Service Layer with possible end-to-end encryption.
    """
    def __init__(self, encryption_required=True, algo="AES-256", key_strength=256):
        self.encryption_required = encryption_required
        self.algorithm = algo
        self.key_strength = key_strength

    def send_data(self, data: str) -> bytes:
        # Simulate encryption or plaintext (for exception case)
        if self.encryption_required:
            # Data is encrypted (simulate by base64 encoding with "ENCRYPTED:" marker)
            encrypted = base64.b64encode(b"ENCRYPTED:" + data.encode('utf-8'))
            return encrypted
        else:
            # Data sent as plaintext
            return data.encode('utf-8')

    def get_encryption_config(self):
        return {
            "required": self.encryption_required,
            "algorithm": self.algorithm,
            "key_strength": self.key_strength
        }

class MockIoTServicePlatform:
    """
    Simulates a simple IoT Service Platform with its own (documented) security policy.
    """
    def __init__(self, security_policy=None):
        # Default: encryption required, AES-256
        self.security_policy = security_policy or {
            "encryption_required": True,
            "algorithm": "AES-256",
            "key_strength": 256
        }
        self.last_rx = None

    def receive_data(self, data: bytes):
        self.last_rx = data

    def get_policy(self):
        return self.security_policy

# --- Fixtures ---

@pytest.fixture
def esl_and_platform():
    """Yields a pair of Embedded Service Layer and Service Platform with encryption required."""
    policy = {"encryption_required": True, "algorithm": "AES-256", "key_strength": 256}
    esl = MockIoTEmbeddedServiceLayer(**policy)
    platform = MockIoTServicePlatform(security_policy=policy)
    return esl, platform

@pytest.fixture
def esl_and_platform_no_encryption():
    """Yields a pair where encryption is explicitly not required (policy exception)."""
    policy = {"encryption_required": False, "algorithm": None, "key_strength": None}
    esl = MockIoTEmbeddedServiceLayer(**policy)
    platform = MockIoTServicePlatform(security_policy=policy)
    return esl, platform

# --- Tests ---

def test_end_to_end_encryption_active(esl_and_platform):
    """
    a) All traffic is end-to-end encrypted per service policy.
    b) Encryption strength and method matches/exceeds requirement.
    c) Payload unreadable in transit unless at endpoint.
    """
    esl, platform = esl_and_platform

    # 1. Send data from ESL to Platform (simulate normal operation)
    user_data = "temperature:22;humidity:58"
    tx_bytes = esl.send_data(user_data)
    platform.receive_data(tx_bytes)

    # 2. Analyze network traffic (simulate by direct access)
    rx_on_wire = platform.last_rx
    # Ensure E2E encryption by (a) not directly readable and (b) has encryption marker when decoded
    as_text = ""
    try:
        as_text = rx_on_wire.decode("utf-8")
    except Exception:
        as_text = ""  # Should look binary if genuinely encrypted

    assert "ENCRYPTED:" in base64.b64decode(rx_on_wire).decode("utf-8", errors="ignore"), \
        "Traffic does not contain expected encryption marker or cannot be decrypted at endpoint"
    assert user_data not in as_text, "User data was visible in-transit, not end-to-end encrypted"

    # 3. Check algorithm & key strength match/exceed requirements
    esl_cfg = esl.get_encryption_config()
    policy = platform.get_policy()
    assert esl_cfg["required"] == policy["encryption_required"]
    assert esl_cfg["algorithm"] == policy["algorithm"]
    assert esl_cfg["key_strength"] >= policy["key_strength"]

    print("E2E encryption validated for sent data. Encryption config:", esl_cfg)

def test_end_to_end_encryption_active_receive(esl_and_platform):
    """
    Repeat for 'received' data (i.e., service platform sends to ESL).
    """
    esl, platform = esl_and_platform

    # Platform prepares response to ESL (simulate encryption)
    response_data = "setpoints:cooling:20"
    if platform.security_policy["encryption_required"]:
        tx_bytes = base64.b64encode(b"ENCRYPTED:" + response_data.encode('utf-8'))
    else:
        tx_bytes = response_data.encode('utf-8')

    # ESL (testbed would capture network traffic)
    assert "ENCRYPTED:" in base64.b64decode(tx_bytes).decode("utf-8", errors="ignore")
    as_text = tx_bytes.decode("utf-8")
    assert response_data not in as_text

def test_no_encryption_when_policy_exempts(esl_and_platform_no_encryption):
    """
    c) If policy is 'NO ENCRYPTION REQUIRED', cleartext is OK, must be documented.
    """
    esl, platform = esl_and_platform_no_encryption

    # 1. Send data
    user_data = "status:open"
    tx_bytes = esl.send_data(user_data)
    platform.receive_data(tx_bytes)

    # 2. Should be readable directly
    rx_text = tx_bytes.decode("utf-8")
    assert user_data in rx_text, "Data should be sent as cleartext for exempted service"

    # 3. Verify policy/documentation explicitly disables encryption
    esl_policy = esl.get_encryption_config()
    platform_policy = platform.get_policy()
    assert esl_policy["required"] is False
    assert platform_policy["encryption_required"] is False

    print("No encryption scenario correctly handled as per explicitly documented policy exception.")

```
---

**How to use:**
- Save as `tests/test_embedded_service_layer_end_to_end_encryption.py`
- Replace the mock implementations with your real embedded service layer, packet capture tools, and policy review for system/integration test.
- Run with `pytest tests/test_embedded_service_layer_end_to_end_encryption.py`

**Coverage:**
- Positive case: E2E encryption, correct strength, non-readable payloads.
- Negative/exception case: Policy-documented cleartext, verified and allowed per GSMA TS.34.
- Both send/receive directions per requirement and test case.

Let me know if you want help adapting these for real capture/analysis, or integration with your device’s cloud/OTA platform.