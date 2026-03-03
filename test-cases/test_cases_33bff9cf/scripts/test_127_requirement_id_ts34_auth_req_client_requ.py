```python
# File: tests/test_ts34_client_authentication_by_server.py

"""
Test Case for:
Requirement ID: TS.34_AUTH_REQ_CLIENT

Requirement:
Authentication of the client by the server is permitted as part of the authentication process
for device management or data communication. Server-side challenge and client authentication
per TS.34 and OMA DM/TLS standards.

References:
- GSMA TS.34 v8.0, Section 5.10, Page 38
- OMA-TS-DM_Protocol-V1_3-20160524-A.pdf, Section 9
"""

import pytest

# ---- MOCKS / PLACEHOLDERS (Replace with your actual DM client/server, API hooks, or protocol capture as needed) ----

class MockServer:
    """
    Simulates a device management or IoT server that can challenge and authenticate the client.
    """
    def __init__(self, expected_credentials="CLNT_AUTH_TOKEN"):
        self.expected_credentials = expected_credentials
        self.auth_challenge_sent = False
        self.auth_successful = False
        self.protocol_log = []
    
    def initiate_session(self, client):
        # Step 1: Begin handshake/session establishment
        self.protocol_log.append("Session initiated by client")
        # Step 2: Server issues authentication challenge to client
        self.auth_challenge_sent = True
        self.protocol_log.append("Authentication challenge sent to client")
        client.receive_auth_challenge(self)
    
    def receive_client_auth_response(self, credential):
        # Step 4: Server receives/scrutinizes client's credentials
        self.protocol_log.append(f"Received client credentials: {credential}")
        if credential == self.expected_credentials:
            self.auth_successful = True
            self.protocol_log.append("Client authentication succeeded")
        else:
            self.auth_successful = False
            self.protocol_log.append("Client authentication failed")
        return self.auth_successful

    def is_authenticated(self):
        return self.auth_successful

    def get_protocol_log(self):
        return list(self.protocol_log)
    
    def reset(self):
        self.auth_challenge_sent = False
        self.auth_successful = False
        self.protocol_log = []

class MockClient:
    """
    Simulates an IoT Device (DM client or application) that can be challenged for authentication.
    """
    def __init__(self, credential="CLNT_AUTH_TOKEN"):
        self.credential = credential
        self.session_established = False
        self.last_server = None
        self.protocol_log = []
    
    def start_session(self, server: MockServer):
        # Client initiates the session
        self.last_server = server
        self.protocol_log.append("Session establishment request sent to server")
        server.initiate_session(self)
    
    def receive_auth_challenge(self, server):
        # Upon challenge, respond with credential
        self.protocol_log.append("Authentication challenge received from server")
        result = server.receive_client_auth_response(self.credential)
        if result:
            self.session_established = True
            self.protocol_log.append("Session established after successful authentication")
        else:
            self.session_established = False
            self.protocol_log.append("Session failed due to authentication error")
    
    def get_protocol_log(self):
        return list(self.protocol_log)
    
    def reset(self):
        self.session_established = False
        self.protocol_log = []

# ---- FIXTURE ----
@pytest.fixture
def client_and_server():
    server = MockServer(expected_credentials="CLNT_AUTH_TOKEN")
    client = MockClient(credential="CLNT_AUTH_TOKEN")
    yield client, server
    client.reset()
    server.reset()

# ---- TEST SCRIPT ----
def test_server_side_authentication_of_client_permitted_and_functional(client_and_server):
    """
    TS.34_AUTH_REQ_CLIENT:
    Server-side authentication challenge is permitted and functional per TS.34/OMA DM.
    """
    client, server = client_and_server

    # Step 1-2-3: Client initiates DM/data session, server issues authentication challenge
    client.start_session(server)

    # Step 4: Logs should show challenge and client response
    server_log = server.get_protocol_log()
    client_log = client.get_protocol_log()
    assert any("Authentication challenge sent" in l for l in server_log), "Server did not initiate authentication challenge"
    assert any("Authentication challenge received" in l for l in client_log), "Client did not process server challenge"
    assert server.auth_challenge_sent, "Server challenge flag not set"

    # Step 5: Server should accept valid credential, session established if successful
    assert server.is_authenticated(), "Server did not authenticate valid client credentials"
    assert client.session_established, "Client session not established after passing authentication"
    assert "Session established after successful authentication" in client_log[-1]

    # Output protocol logs for traceability
    print("Server protocol log:", server_log)
    print("Client protocol log:", client_log)

@pytest.mark.parametrize("client_credential,should_pass", [
    ("CLNT_AUTH_TOKEN", True),
    ("WRONG_TOKEN", False),
])
def test_server_side_authentication_rejects_invalid_credentials(client_credential, should_pass):
    """
    Server denies session establishment if client authentication fails; only permitted client is authenticated.
    """
    server = MockServer(expected_credentials="CLNT_AUTH_TOKEN")
    client = MockClient(credential=client_credential)
    client.start_session(server)
    if should_pass:
        assert server.is_authenticated(), "Expected valid authentication to succeed"
        assert client.session_established
    else:
        assert not server.is_authenticated(), "Expected invalid authentication to be rejected"
        assert not client.session_established
    print("Server protocol log with credential:", server.get_protocol_log())
    print("Client protocol log with credential:", client.get_protocol_log())
```
---

**How to use/adapt:**
- Save as `tests/test_ts34_client_authentication_by_server.py`
- Replace mocks with actual client/server APIs, protocol analyzers, or session traces for your IoT DM environment.
- Run:
  ```bash
  pytest tests/test_ts34_client_authentication_by_server.py
  ```
- Assertions strictly map to step-by-step authentication flow, per GSMA TS.34 and OMA DM reference logic.

Let me know if you need TLS/X.509 or OMA-DM/MS-CHAP specific test integration!