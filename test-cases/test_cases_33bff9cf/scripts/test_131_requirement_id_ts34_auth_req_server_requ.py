```python
# File: tests/test_x509_server_authentication.py

"""
Test Case for:
Requirement ID : TS.34_AUTH_REQ_SERVER

Requirement:
The client device MUST support authentication of the server using X.509 public key technologies (“certificates”)
when establishing secure communication.

References:
- GSMA TS.34 v8.0, Section 5.10, Authentication and Secure Technology (page 38), TS.34_AUTH_REQ_SERVER
- RFC 5280: Internet X.509 PKI Certificate and Certificate Revocation List Profile
- GSMA TS.34 v8.0 (“certificates”, “secure transport protocol must include TLS”)
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest
import ssl
import socket

# ---- MOCKS FOR DEMONSTRATION (Replace with real device/server/testbed integration) ----
# For live device or system, replace with actual client API log hooks, TLS connection harness, pcap/log analyzers, etc.

class MockServerCertificate:
    """Represents a server certificate scenario for testing."""
    def __init__(self, trusted=True, expired=False, revoked=False):
        self.trusted = trusted
        self.expired = expired
        self.revoked = revoked

def simulate_client_tls_handshake(server_cert: MockServerCertificate):
    """
    Simulates a client attempting to perform TLS handshake and authenticate the server using X.509 certificates.
    Replace this logic with either a real Python ssl.SSLContext test or device command API.
    """
    # Step 2-3: Attempt connection to server with presented certificate scenario
    # Return tuple: (connection_success, log)
    if not server_cert.trusted or server_cert.expired or server_cert.revoked:
        return False, ["TLS handshake failed: certificate not trusted/expired/revoked", "X.509 validation failed"]
    else:
        return True, ["TLS handshake succeeded", "X.509 certificate validated against trusted CA store"]

@pytest.mark.parametrize("cert_scenario,should_pass,reason", [
    (MockServerCertificate(trusted=True, expired=False, revoked=False), True, "Trusted CA, valid X.509"),
    (MockServerCertificate(trusted=False, expired=False, revoked=False), False, "Untrusted CA"),
    (MockServerCertificate(trusted=True, expired=True, revoked=False), False, "Expired X.509"),
    (MockServerCertificate(trusted=True, expired=False, revoked=True), False, "Revoked certificate"),
])
def test_client_device_x509_server_authentication(cert_scenario, should_pass, reason):
    """
    TS.34_AUTH_REQ_SERVER: Verify server authentication via X.509 certificate is enforced on the client.
    """
    # Step 1: Simulate (or trigger) TLS/secure connection attempt from client device to the test server
    conn, logs = simulate_client_tls_handshake(cert_scenario)

    # Step 2-6: Assert connection outcome matches expectation
    if should_pass:
        assert conn, f"Connection to server with valid X.509 certificate should succeed [{reason}]"
        # Step 3: Logs must confirm X.509 validation was performed
        assert any("X.509 certificate validated" in entry for entry in logs), "X.509 validation log missing"
    else:
        assert not conn, f"Connection with {reason} should fail"
        assert any("X.509 validation failed" in entry for entry in logs), "Failure reason (X.509) should be logged"

    # Step 7: Output for traceability/audit
    print(f"Scenario: {reason} | Handshake logs: {logs}")

def test_client_rejects_invalid_server_certificates():
    """
    Negative: Ensure X.509 server authentication cannot be bypassed, connection fails with log entry.
    """
    untrusted_cert = MockServerCertificate(trusted=False)
    expired_cert = MockServerCertificate(trusted=True, expired=True)
    revoked_cert = MockServerCertificate(trusted=True, revoked=True)

    for scenario, label in [
        (untrusted_cert, "untrusted"),
        (expired_cert, "expired"),
        (revoked_cert, "revoked")
    ]:
        conn, logs = simulate_client_tls_handshake(scenario)
        assert not conn, f"Client should reject a {label} server certificate"
        assert any("failed" in entry.lower() and "x.509" in entry.lower() for entry in logs), "Rejection should be logged"
        print(f"Reject {label} cert - handshake log: {logs}")

def test_client_server_handshake_includes_x509_authentication(monkeypatch):
    """
    Demo: (For embedded or CI) - Simulate parsing logs/capture for "Certificate" records in handshake
    """
    # In live system, replace this logic with capture/parse of device log or pcap handshake
    handshake_log = [
        "ClientHello: TLSv1.2",
        "ServerHello: TLSv1.2",
        "Certificate: present (X.509 PEM)",
        "ServerHelloDone",
        "Client verifies server certificate issuer against CA store"
    ]
    x509_lines = [line for line in handshake_log if "Certificate" in line or "server certificate" in line]
    assert any("X.509" in line for line in x509_lines), "Handshake records must show X.509 server certificate presented/validated"
    print("Handshake log confirms X.509 authentication:", x509_lines)

# This test scaffolding can be extended to use Python's ssl.SSLContext in client mode for actual cert validation,
# or be connected to your CI/testbed logs and TLS handshake trace analyzers as required.

```
---
**How to use/adapt:**
- Save as `tests/test_x509_server_authentication.py`.
- Replace/mock `simulate_client_tls_handshake()` with code that initiates a real device TLS/HTTPS/OMA DM connection and parses responses or protocol logs.
- For hardware/embedded or CI, ensure server cert rotation is possible for trusted/untrusted, and capture device logs for validation messages.
- Run with:
  ```bash
  pytest tests/test_x509_server_authentication.py
  ```
- All assertion and logging steps map to GSMA TS.34_AUTH_REQ_SERVER entry/exit criteria for X.509 server authentication enforcement and validation.
If needed, I can provide a pytest + OpenSSL-based client/server for real certificate validation with minimal Python code. Let me know!