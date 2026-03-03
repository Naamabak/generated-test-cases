```python
# File: tests/test_dm_client_nonce_resynchronization.py

"""
Test Case for:
Requirement ID : TS.34_5.10_REQ_014

Requirement:
The DM client that uses MD5 or HMAC authentication for security must support client-initiated nonce resynchronization when the nonce value becomes stale.
The module manufacturer SHALL use the same authentication type during IoT/testing and production/lifetime operation.

References:
- GSMA TS.34 v8.0, Section 5.10, TS.34_5.10_REQ_014
- OMA DM Protocol v1.2/v1.3, Section 9.4.2 (MD5/HMAC digest & nonce resync)
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest

# --- MOCKS / INTERFACES (Replace with integration to your DM client/server & test platform) ---

class MockDMServer:
    """
    Simulates an OMA DM server supporting MD5/HMAC authentication and nonce management.
    """
    def __init__(self, auth_type="MD5"):
        self.auth_type = auth_type         # "MD5" or "HMAC"
        self.nonce = "NONCE0"
        self.nonce_history = ["NONCE0"]
        self.resync_handled = False
        self.log = []

    def generate_fresh_nonce(self):
        count = len(self.nonce_history)
        new_nonce = f"NONCE{count}"
        self.nonce = new_nonce
        self.nonce_history.append(new_nonce)
        return new_nonce

    def process_auth_request(self, client_digest, nonce, resync_request=False):
        """
        Simulate normal authentication on incoming client request with provided digest and nonce.
        """
        # Step 2: Accept server-generated nonce as normal
        if nonce == self.nonce and not resync_request:
            self.log.append(f"Auth success (auth={self.auth_type}, nonce={nonce})")
            return True
        
        # Step 3/4: Nonce is stale, client initiates resync per protocol (Section 9.4.2)
        if resync_request:
            self.resync_handled = True
            new_nonce = self.generate_fresh_nonce()
            self.log.append(
                f"Nonce resync triggered, server provides fresh nonce: {new_nonce}"
            )
            return {"resync_nonce": new_nonce}
        else:
            self.log.append(f"Auth failed (stale or invalid nonce: {nonce})")
            return False

    def get_log(self):
        return list(self.log)
    
    def reset(self):
        self.__init__(self.auth_type)

class MockDMClient:
    """
    Simulates a DM Client supporting OMA DM protocol with MD5/HMAC and nonce resynchronization.
    """
    def __init__(self, auth_type="MD5"):
        self.auth_type = auth_type  # "MD5" or "HMAC"
        self.current_nonce = None
        self.session_resync = False
        self.log = []
        self.mode = "normal"  # switches to "need_resync" if nonce is stale

    def initiate_dm_session(self, server: MockDMServer):
        # Initial session: receive server nonce, use for digest
        self.current_nonce = server.nonce
        self.session_resync = False
        digest = self._calculate_digest(self.current_nonce)
        result = server.process_auth_request(digest, self.current_nonce)
        if result is True:
            self.log.append(f"DM session started (auth={self.auth_type}, nonce={self.current_nonce}) (success)")
            return True

        # Simulate staleness (out-of-date nonce) triggers resync
        if result is False:
            self.log.append("DM session failed (stale nonce detected), resync required")
            self.mode = "need_resync"
            return False
    
    def simulate_stale_nonce(self, server: MockDMServer):
        # Use "old" nonce—simulate replay or old session; expect resync flow
        self.session_resync = True
        digest = self._calculate_digest(self.current_nonce)
        result = server.process_auth_request(digest, self.current_nonce)
        if result is False:
            self.mode = "need_resync"
            self.log.append("Stale nonce detected, preparing to resync")
            return False

    def trigger_nonce_resync(self, server: MockDMServer):
        # Step 4: Client initiates a nonce resync per OMA DM protocol
        self.log.append("Client initiates nonce resynchronization request")
        result = server.process_auth_request(None, self.current_nonce, resync_request=True)
        if isinstance(result, dict) and "resync_nonce" in result:
            # Accept new nonce
            self.current_nonce = result["resync_nonce"]
            digest = self._calculate_digest(self.current_nonce)
            self.log.append(
                f"Nonce resync completed; new server nonce: {self.current_nonce}; retrying session..."
            )
            # Retry session with new nonce
            success = server.process_auth_request(digest, self.current_nonce)
            if success:
                self.log.append(f"Session resumed after nonce resync (auth={self.auth_type}) (success)")
            return success
        else:
            self.log.append("Nonce resync failed")
            return False

    def _calculate_digest(self, nonce):
        # Simulate digest (don't perform real MD5/HMAC, just placeholder for data flow)
        return f"digest-{self.auth_type}-{nonce[-1]}"

    def get_log(self):
        return list(self.log)

    def get_auth_type(self):
        return self.auth_type

    def reset(self):
        self.__init__(self.auth_type)


# --- MOCK MODULE CONFIGURATION LOGS ---
class MockModuleConfigHistory:
    """
    Simulates tracking of device/module configuration & authentication mode across manufacturing, test, and production.
    """
    def __init__(self, initial_auth_type):
        self.records = {
            "manufacturing": initial_auth_type,
            "IoT_test": initial_auth_type,
            "production": initial_auth_type
        }

    def set_phase_auth(self, phase, auth_type):
        self.records[phase] = auth_type

    def all_phases_same_auth(self):
        return len(set(self.records.values())) == 1

    def get_audit_log(self):
        return dict(self.records)

# --- PYTEST FIXTURES ----

@pytest.fixture(params=["MD5", "HMAC"], ids=["md5_auth", "hmac_auth"])
def dm_server_and_client(request):
    auth_type = request.param
    server = MockDMServer(auth_type=auth_type)
    client = MockDMClient(auth_type=auth_type)
    config_history = MockModuleConfigHistory(auth_type)
    yield server, client, config_history

# --- TEST SCRIPT ---

def test_dm_client_nonce_resync_and_auth_type_consistency(dm_server_and_client):
    """
    TS.34_5.10_REQ_014:
    - DM client using MD5/HMAC detects and resynchronizes stale nonce.
    - Session resumes successfully after resynchronization.
    - Authentication method is consistent across module lifecycle.
    """

    server, client, config_history = dm_server_and_client

    # Step 1: Initialize DM session using MD5 or HMAC, verify nonce in normal flow
    assert client.initiate_dm_session(server) is True
    assert client.mode == "normal"

    # Step 2: Simulate a session with a stale/expired nonce (old one replayed)
    client.simulate_stale_nonce(server)
    assert client.mode == "need_resync"

    # Step 3/4: Client initiates nonce resynchronization, gets new nonce, resumes session
    success = client.trigger_nonce_resync(server)
    assert success is True, "Failed to resume DM session after nonce resynchronization"
    assert server.resync_handled is True
    assert client.mode != "need_resync"
    assert any("DM session started" in l for l in client.get_log())
    assert any("Nonce resync completed" in l for l in client.get_log())
    assert any("Session resumed after nonce resync" in l for l in client.get_log())
    assert any("Nonce resync triggered" in entry for entry in server.get_log())

    # Step 6/7: Authentication type is the same throughout lifecycle (manufacturing, test, production)
    # (Simulate log/config evidence and audit)
    audit_log = config_history.get_audit_log()
    assert config_history.all_phases_same_auth(), (
        f"Authentication method varied across device lifetime phases: {audit_log}"
    )
    assert audit_log["manufacturing"] == audit_log["production"] == client.get_auth_type()

    # Output for reporting/audit
    print("Client log:", client.get_log())
    print("Server log:", server.get_log())
    print("Config audit over lifetime:", audit_log)

# Optionally, add negative test to demonstrate failure if a different authentication is attempted in production
def test_auth_type_inconsistency_detected():
    config_history = MockModuleConfigHistory("MD5")
    config_history.set_phase_auth("production", "HMAC")
    assert not config_history.all_phases_same_auth(), "Mismatch in auth type across lifecycle not detected"

```
---

**Instructions to Use / Customize:**
- Save as `tests/test_dm_client_nonce_resynchronization.py`.
- Replace mocks with integration to your device OMA DM client and server (supporting MD5/HMAC and nonce resync).
- Use protocol analyzers and audit logs for real sessions as needed.
- Run with:
  ```bash
  pytest tests/test_dm_client_nonce_resynchronization.py
  ```
- Logs and output will provide step-by-step traceability for DM session, nonce resync, and constant authentication method usage.
- Each assertion matches the pass criteria and protocol steps described in the test case.
