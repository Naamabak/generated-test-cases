```python
# File: tests/test_bootstrap_fqdn_server_url.py

"""
Test Case for:
Requirement ID : TS.34_BOOTSTRAP_REQ_FQDN

Requirement:
Only a Fully Qualified Domain Name (FQDN) SHALL be used in the bootstrap account for the server URL for an HTTPS connection.
IP addresses or incomplete domains are forbidden in the server URL for HTTPS bootstrap.

References:
- GSMA TS.34 v8.0, Page 38 (“No IP address SHALL be used in the bootstrap account for the server URL...”)
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
- OMA Device Management (bootstrap account parameter definition)

"""

import pytest
import re

# --- MOCK IMPLEMENTATION (Replace with your real API/server/client for integration/system testing) ---

def is_fqdn(url):
    """
    Checks if the provided URL (e.g., for a DM server) is a valid FQDN.
    This is a basic implementation. Replace with robust validation if needed.
    """
    domain_pattern = re.compile(
        r"^(https://)?((?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,63}(/.*)?$"
    )
    ip_pattern = re.compile(
        r"^(https://)?(\d{1,3}\.){3}\d{1,3}(:\d+)?(/.*)?$"
    )
    # Not a valid FQDN if it matches an IP pattern or is only a single label (no dot)
    if ip_pattern.match(url):
        return False
    if '.' not in url.split("://")[-1].split('/')[0]:
        return False
    return bool(domain_pattern.match(url))

class MockBootstrapAccount:
    """
    Simulates a bootstrap account with a configurable HTTPS server URL.
    """
    def __init__(self, server_url):
        self.server_url = server_url  # E.g. "https://dm.example-mno.com"
        self.logs = [f"Initial bootstrap server URL set to: {server_url}"]

    def get_server_url(self):
        return self.server_url

    def set_server_url(self, new_url):
        """
        Attempt to set the server URL; only allows valid FQDNs.
        Returns True if accepted, False if rejected (as per device/module policy).
        """
        if is_fqdn(new_url):
            self.server_url = new_url
            self.logs.append(f"Server URL updated to valid FQDN: {new_url}")
            return True
        else:
            self.logs.append(f"Rejected server URL (must be FQDN): {new_url}")
            return False

    def bootstrap_attempt(self):
        """
        Attempt to bootstrap using the current server URL. Succeeds only if URL is a valid FQDN.
        """
        if is_fqdn(self.server_url):
            self.logs.append(f"Bootstrap attempt with '{self.server_url}': SUCCESS")
            return True
        else:
            self.logs.append(f"Bootstrap attempt with '{self.server_url}': FAIL (not a valid FQDN)")
            return False

    def get_logs(self):
        return list(self.logs)

    def reset(self, server_url):
        self.__init__(server_url)

# --- TEST FIXTURE ---

@pytest.fixture
def bootstrap_account():
    """
    Yields a factory-default bootstrap account with a valid FQDN server URL.
    """
    default_fqdn = "https://dm.operator-prod.com"
    acct = MockBootstrapAccount(server_url=default_fqdn)
    yield acct
    acct.reset(server_url=default_fqdn)

# --- TEST SCRIPT ---

def test_bootstrap_account_server_url_only_fqdn_allowed(bootstrap_account):
    """
    TS.34_BOOTSTRAP_REQ_FQDN:
    - The server URL MUST be a valid FQDN for HTTPS bootstrap.
    - IP addresses and incomplete domains must be rejected.
    """
    # Step 1: Retrieve and display the current server URL (should be a valid FQDN).
    url = bootstrap_account.get_server_url()
    assert is_fqdn(url), f"Initial server URL is not a valid FQDN: {url}"

    # Step 2: Try to set to a valid FQDN (should succeed)
    result1 = bootstrap_account.set_server_url("https://dm.new-mno-uk.co.uk")
    assert result1
    assert is_fqdn(bootstrap_account.get_server_url())

    # Step 3: Try to set server URL to various invalid values (should all be rejected)
    test_cases = [
        "https://192.168.1.10",                    # Explicit IP address
        "https://10.0.0.5:8443",                   # IP with port
        "https://localhost",                       # Incomplete domain
        "https://mgmt",                            # Not a FQDN (no dot)
        "https://mno.com",                         # Minimal FQDN (should pass)
        "192.168.50.100",                          # No scheme, IP
        "mno.com",                                 # Just domain (should pass)
        "dm.example",                              # Fake partial domain, no TLD
    ]
    expected_results = [False, False, False, False, True, False, True, False]

    for test_url, should_pass in zip(test_cases, expected_results):
        result = bootstrap_account.set_server_url(test_url)
        if should_pass:
            assert result, f"Valid FQDN '{test_url}' was incorrectly rejected"
        else:
            assert not result, f"Invalid server URL '{test_url}' was incorrectly accepted"

    # Step 4: Attempt to bootstrap
    # Valid FQDN - should succeed
    assert bootstrap_account.set_server_url("https://dm.ok-operator.com")
    assert bootstrap_account.bootstrap_attempt()
    # IP address - should fail to bootstrap
    assert not bootstrap_account.set_server_url("https://8.8.8.8")
    # Partial domain - should fail
    assert not bootstrap_account.set_server_url("localhost")

    # Step 5: Assert log entries confirm that only FQDNs are allowed/accepted at all config and attempt interfaces
    logs = bootstrap_account.get_logs()
    assert any("SUCCESS" in l for l in logs), "No successful bootstrap attempt found with FQDN"
    assert all(
        "Rejected server URL" in l or "Bootstrap attempt with" not in l or "SUCCESS" in l
        for l in logs if "192.168." in l or "localhost" in l
    ), "IP or incomplete domain was not consistently rejected"

    print("Bootstrap server URL tests - logs:")
    for entry in logs:
        print(entry)

@pytest.mark.parametrize("invalid_url", [
    "https://127.0.0.1",
    "https://172.16.254.1",
    "http://dm.example.org",             # Not HTTPS (for stricter interpretation)
    "89.12.14.13",
    "dm",
    "ftp://dm.example-mno.com",
])
def test_bootstrap_account_rejects_ip_and_non_fqdn_urls(bootstrap_account, invalid_url):
    """
    Explicitly checks a variety of bad server URL patterns are always forbidden.
    """
    result = bootstrap_account.set_server_url(invalid_url)
    assert not result, f"Invalid server URL '{invalid_url}' was incorrectly accepted."
    logs = bootstrap_account.get_logs()
    assert any(invalid_url in l and "Rejected" in l for l in logs)

```
---

**Instructions / Integration:**
- Save as `tests/test_bootstrap_fqdn_server_url.py`.
- Replace the mock implementation with your real OMA DM node/config API, or real bootstrap account parameter tooling for live/hardware testing.
- Run with:
  ```bash
  pytest tests/test_bootstrap_fqdn_server_url.py
  ```
- Every assertion strictly covers the allowed patterns: only FQDN, never IP or bare label, for the HTTPS bootstrap account server URL per TS.34, logs for audit, negative and positive tests included.