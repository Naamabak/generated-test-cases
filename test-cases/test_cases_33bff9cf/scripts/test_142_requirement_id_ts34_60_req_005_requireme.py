```python
# File: tests/test_service_platform_device_authentication.py

"""
Test Case for:
Requirement ID : TS.34_6.0_REQ_005

Requirement:
The IoT Service Platform SHOULD authenticate the IoT Device prior to data communication.
The strength of authentication SHOULD be appropriate to the IoT Service.

References:
- GSMA TS.34 v8.0, Section 6.0, TS.34_6.0_REQ_005
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
- Section 4.2 (authentication strength best practices)
"""

import pytest

# ---- MOCKS / PLACEHOLDERS (replace with integration to your real service/device for system/lab/CI) ----

class MockIoTDevice:
    """Simulate an IoT Device with various authentication methods."""
    def __init__(self, auth_mechanism, credential, credential_strength):
        self.auth_mechanism = auth_mechanism  # e.g., 'X.509', 'PSK', 'Token'
        self.credential = credential
        self.credential_strength = credential_strength  # e.g., {'key_length': 2048, 'algo': 'RSA'}
        self.authenticated = False

    def connect_and_authenticate(self, platform):
        self.authenticated = platform.authenticate_device(self.auth_mechanism, self.credential, self.credential_strength)
        return self.authenticated

    def send_data(self, platform, data):
        return platform.receive_data(self, data, authenticated=self.authenticated)

    def reset(self):
        self.authenticated = False


class MockIoTServicePlatform:
    """Simulates the IoT Service Platform authentication and data acceptance logic."""
    def __init__(self, expected_auth_mech, expected_strength_policy):
        self.expected_auth_mech = expected_auth_mech  # e.g., 'X.509'
        self.expected_strength_policy = expected_strength_policy  # e.g., {'key_length': 2048, ...}
        self.authenticated_devices = set()
        self.received_messages = []
        self.logs = []

    def authenticate_device(self, auth_mechanism, credential, credential_strength):
        # Step 2: Validate auth mechanism and strength
        policy = self.expected_strength_policy
        match = (
            auth_mechanism == self.expected_auth_mech and
            credential.get('valid', False) and
            all(credential_strength.get(k) >= v for k, v in policy.items())
        )
        if match:
            self.authenticated_devices.add(id(credential))
            self.logs.append("Authentication success: Device authenticated using appropriate mechanism/strength.")
            return True
        else:
            self.logs.append("Authentication failed: Mechanism/strength invalid or credential not accepted.")
            return False

    def receive_data(self, device, data, authenticated):
        # Step 3: Only accept data after successful authentication
        if authenticated and id(device.credential) in self.authenticated_devices:
            self.received_messages.append(data)
            self.logs.append("Data accepted from device.")
            return True
        else:
            self.logs.append("Data rejected: Device not authenticated.")
            return False

    def get_logs(self):
        return list(self.logs)

    def reset(self):
        self.authenticated_devices.clear()
        self.received_messages.clear()
        self.logs = []

# ---- FIXTURES ----

@pytest.fixture
def iot_service_platform():
    # Example policy: require X.509 auth, RSA key >= 2048 bits
    auth_policy = {'key_length': 2048}
    return MockIoTServicePlatform(expected_auth_mech='X.509', expected_strength_policy=auth_policy)

@pytest.fixture
def valid_device():
    # Valid device: has valid X.509 cert, RSA 3072 bits
    credential = {'valid': True}
    cred_strength = {'key_length': 3072}
    return MockIoTDevice(auth_mechanism='X.509', credential=credential, credential_strength=cred_strength)

@pytest.fixture
def invalid_device_wrong_mech():
    # Invalid mechanism: uses pre-shared key instead of required cert
    credential = {'valid': True}
    cred_strength = {'key_length': 128}  # Irrelevant for PSK
    return MockIoTDevice(auth_mechanism='PSK', credential=credential, credential_strength=cred_strength)

@pytest.fixture
def invalid_device_weak_key():
    # Too weak key for platform policy
    credential = {'valid': True}
    cred_strength = {'key_length': 1024}
    return MockIoTDevice(auth_mechanism='X.509', credential=credential, credential_strength=cred_strength)

@pytest.fixture
def invalid_device_bad_cred():
    # Bad credential (not valid)
    credential = {'valid': False}
    cred_strength = {'key_length': 3072}
    return MockIoTDevice(auth_mechanism='X.509', credential=credential, credential_strength=cred_strength)

# ---- TEST SCRIPT ----

def test_platform_authenticates_device_before_data(iot_service_platform, valid_device):
    """
    a) The platform requires authentication before any data is accepted.
    b) Auth mechanism and strength meet the policy.
    """
    # Step 1: Device initiates communication, authenticates
    assert valid_device.connect_and_authenticate(iot_service_platform), \
        "Device should successfully authenticate with supported mechanism and strength."
    # Step 2: Send data after authentication
    result = valid_device.send_data(iot_service_platform, "hello")
    assert result, "Data should be accepted after authentication."
    logs = iot_service_platform.get_logs()
    assert any("authenticated" in log for log in logs)
    assert any("Data accepted" in log for log in logs)
    print("Valid device logs:", logs)

@pytest.mark.parametrize("inv_dev_fixture", [
    "invalid_device_wrong_mech", "invalid_device_weak_key", "invalid_device_bad_cred"
])
def test_platform_denies_unauthenticated_or_weak_device(iot_service_platform, request, inv_dev_fixture):
    """
    b) Unauthenticated or incorrectly authenticated devices cannot send/receive data.
    """
    device = request.getfixturevalue(inv_dev_fixture)
    result = device.connect_and_authenticate(iot_service_platform)
    assert not result, "Authentication should fail for invalid dev config"
    data_ok = device.send_data(iot_service_platform, "testdata")
    assert not data_ok, "Unauthenticated or non-compliant device must not be allowed to send data"
    logs = iot_service_platform.get_logs()
    assert any("Authentication failed" in log for log in logs)
    assert any("Data rejected" in log for log in logs)
    print(f"Invalid device logs ({inv_dev_fixture}):", logs)

def test_authentication_mechanism_strength_documented(iot_service_platform, valid_device):
    """
    c) Authentication strength can be cross-referenced with the IoT Service policy.
    """
    # Example: Service policy is X.509, RSA >= 2048
    # Device should document 'auth_mechanism' and 'credential_strength'
    assert valid_device.auth_mechanism == iot_service_platform.expected_auth_mech
    assert all(valid_device.credential_strength.get(k) >= v for k, v in iot_service_platform.expected_strength_policy.items())
    print("Device authentication mechanism and strength:", valid_device.auth_mechanism, valid_device.credential_strength)
    print("Service policy (expected):", iot_service_platform.expected_auth_mech, iot_service_platform.expected_strength_policy)
```
---

**Instructions:**
- Save as `tests/test_service_platform_device_authentication.py`.
- Replace mock class logic with your real platform/device integration for system/lab or CI.
- Run with:
  ```bash
  pytest tests/test_service_platform_device_authentication.py
  ```
- The script covers:
  - Platform always authenticates the device before allowing data traffic.
  - Platform denies communication from unauthenticated or weakly-authenticated devices.
  - Checks that the authentication method and strength meet the service’s requirements.
  - Print/log evidence for audit and reporting.