```python
# File: tests/test_ota_secure_authenticated_protocols.py

"""
Test Case for:
Requirement ID : TS.34_D.1_REQ_001

Requirement Summary:
The IoT Communications Module SHOULD support secure and authenticated over-the-air (OTA) protocols
to implement diagnostic requirements stated in RDR2. Example protocols are OMA DiagMon, OMA DM, OMA FUMO.

References:
- GSMA TS.34 v8.0, Annex D, TS.34_D.1_REQ_001
- OMA DiagMon [7], OMA DM [8], OMA FUMO [9] specifications
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest

# ---- MOCK / PLACEHOLDER CLASSES (Replace with integration to actual device, secure OTA server, and protocol captures) ----

class MockOTAServer:
    """
    Simulates an OTA management server (DiagMon, DM, or FUMO).
    """
    def __init__(self, protocol, valid_credentials=True, secure_transport=True):
        self.protocol = protocol
        self.secure_transport = secure_transport
        self.valid_credentials = valid_credentials

    def start_authenticated_ota_session(self, module):
        # Step 2/3: Only succeed if credentials and transport are both secure/authenticated
        if self.valid_credentials and self.secure_transport:
            session = {"authenticated": True, "secure": True, "protocol": self.protocol}
            module.session_log.append(f"OTA {self.protocol} session: secure+authenticated established")
            return session
        else:
            session = {"authenticated": False, "secure": bool(self.secure_transport)}
            module.session_log.append(
                f"OTA {self.protocol} session: FAILED - {'unauthenticated' if not self.valid_credentials else 'insecure'}"
            )
            return session

    def start_insecure_session(self, module):
        # Simulate OTA attempt over insecure (non-encrypted/unauthenticated) channel
        session = {"authenticated": False, "secure": False}
        module.session_log.append(f"OTA {self.protocol} INSECURE ATTEMPT: failed authentication")
        return session

    def send_diagnostic_command(self, module, session, diagnostic_name):
        # Step 4: Only work if session is authenticated/secure; invoke RDR2 diagnostic command
        if session.get("authenticated") and session.get("secure"):
            result = module.execute_diagnostic(diagnostic_name)
            module.session_log.append(f"Diag command '{diagnostic_name}' sent via {self.protocol}: executed ({result})")
            return result
        else:
            module.session_log.append(
                f"Diag command '{diagnostic_name}' failed: session not authenticated/secure"
            )
            return None

class MockIoTCommModule:
    """
    Simulates an IoT Communications Module supporting secure OTA diagnostics.
    """
    SUPPORTED_PROTOCOLS = {"OMA DiagMon", "OMA DM", "OMA FUMO"}

    def __init__(self):
        self.session_log = []

    def execute_diagnostic(self, diagnostic_name):
        # Simulate RDR2 diagnostic command: always succeeds if called in test
        self.session_log.append(f"Diagnostic '{diagnostic_name}' executed and report send")
        return "success"

    def get_log(self):
        return list(self.session_log)

    def reset(self):
        self.session_log = []

# ---- FIXTURE FOR SHARED MODULE ----
@pytest.fixture
def comm_module():
    module = MockIoTCommModule()
    yield module
    module.reset()

# ---- TEST SCRIPT ----

@pytest.mark.parametrize("protocol", ["OMA DiagMon", "OMA DM", "OMA FUMO"])
def test_secure_authenticated_ota_protocols_are_enforced(comm_module, protocol):
    """
    TS.34_D.1_REQ_001:
    - OTA diagnostics (RDR2) are ONLY accepted over secure, authenticated OTA protocols.
    - Mutual authentication is required. Insecure/incomplete sessions are denied.
    - Logs/captures confirm security enforcement and protocol use.
    """
    # Step 1: Initiate a secure, authenticated OTA session
    ota_server = MockOTAServer(protocol, valid_credentials=True, secure_transport=True)
    session = ota_server.start_authenticated_ota_session(comm_module)
    assert session["authenticated"] and session["secure"], \
        f"{protocol} OTA session was not secure/authenticated."
    assert protocol in comm_module.SUPPORTED_PROTOCOLS

    # Step 4: Send an RDR2 diagnostic command and verify execution/log
    diagnostic_name = "RDR2_TestDiag"
    result = ota_server.send_diagnostic_command(comm_module, session, diagnostic_name)
    assert result == "success"

    # Step 5: Attempt session with insecure/invalid setup - must be denied
    insecure_server = MockOTAServer(protocol, valid_credentials=False, secure_transport=False)
    bad_session = insecure_server.start_authenticated_ota_session(comm_module)
    result2 = insecure_server.send_diagnostic_command(comm_module, bad_session, diagnostic_name)
    assert not bad_session["authenticated"] or not bad_session["secure"]
    assert result2 is None

    # Step 6: Repeat for all mocked protocols (pytest param)

    # Step 7: Check logs for audit/compliance
    log = comm_module.get_log()
    assert any("established" in l for l in log if "OTA" in l.lower()), "No secure session accepted in log."
    assert any("Diag command" in l and "executed" in l for l in log), "Diagnostic command not executed via secure OTA session."
    assert any("INSECURE ATTEMPT" in l or "FAILED" in l for l in log if "ota" in l.lower() or "diag" in l.lower())
    print(f"===== OTA {protocol} LOG =====")
    for entry in log:
        print(entry)

@pytest.mark.parametrize("protocol", ["OMA DiagMon", "OMA DM", "OMA FUMO"])
def test_unauthenticated_ota_attempt_is_blocked(comm_module, protocol):
    """
    Unauthenticated or insecure OTA sessions are NOT allowed; no diagnostic or management is permitted.
    """
    ota_server = MockOTAServer(protocol, valid_credentials=False, secure_transport=False)
    session = ota_server.start_insecure_session(comm_module)
    assert not session["authenticated"] and not session["secure"]
    result = ota_server.send_diagnostic_command(comm_module, session, "RDR2_FailDiag")
    assert result is None
    log = comm_module.get_log()
    assert any("INSECURE ATTEMPT" in l or "FAILED" in l for l in log)
    print(f"===== OTA {protocol} UNAUTH LOG =====")
    for entry in log:
        print(entry)
```
---

**Instructions to use/adapt:**
- Save as `tests/test_ota_secure_authenticated_protocols.py`
- Replace mocks with your actual OTA management server/client integration, network analyzer hooks, and device test commands. 
- Run with:
  ```bash
  pytest tests/test_ota_secure_authenticated_protocols.py
  ```
- Every assertion and print/log maps to TS.34_D.1_REQ_001 entry/exit criteria and evidence for audit or compliance. Expand protocol logic and diagnostic payloads as per your product's diagnostic capabilities or RDR2 feature set.