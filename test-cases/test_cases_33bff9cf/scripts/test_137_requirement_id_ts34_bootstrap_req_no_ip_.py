```python
# File: tests/test_bootstrap_no_ip_in_server_url.py

"""
Test Case for:
Requirement ID : TS.34_BOOTSTRAP_REQ_NO_IP

Requirement:
No IP address SHALL be used in the bootstrap account for the server URL. Only an FQDN is permitted.

References:
- GSMA TS.34 v8.0, Section 5.10 (Bootstrap and Secure Connection Requirements)
- TS.34_BOOTSTRAP_REQ_NO_IP
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest
import re
from ipaddress import ip_address

# --- MOCKS / PLACEHOLDER IMPLEMENTATIONS ---
# Replace these with real device/config APIs in actual integration/lab setup.

class MockBootstrapAccount:
    """
    Simulates a bootstrap account object returned from device/module for testing.
    """
    def __init__(self, server_url: str):
        self.server_url = server_url

    def get_server_url(self):
        return self.server_url

    def set_server_url(self, url: str):
        # Simulates interface: returns True if accepted, False if rejected (per requirement)
        # Block IP address assignment as per TS.34_BOOTSTRAP_REQ_NO_IP
        if self.is_url_ip_address(url):
            return False
        self.server_url = url
        return True

    @staticmethod
    def is_url_ip_address(url: str):
        """
        Returns True if the URL represents a numeric IP address, False if FQDN.
        Accepts URLs with or without "https://" prefixes, and optional port.
        """
        # Strip URL scheme if present
        no_scheme_url = re.sub(r'^https?://', '', url)
        # Remove port or path if present
        match = re.match(r"([^/:]+)", no_scheme_url)
        host = match.group(1) if match else no_scheme_url
        try:
            ip_address(host)
            return True
        except ValueError:
            return False

# -- TEST FIXTURES --

@pytest.fixture(params=[
    # Add representatives: FQDN (valid), IPv4 (invalid), IPv6 (invalid in brackets or not)
    "https://dm.iot-operator.com/bootstrap",
    "https://192.168.10.5:443/bootstrap",
    "https://[2001:0db8:85a3:0000:0000:8a2e:0370:7334]:443/bootstrap",
    "dm.device-management.carrier.tld",
    "10.1.2.3",
    "[2607:f8b0:4005:805::200e]"
], ids=[
    "fqdn_https", "ipv4_https", "ipv6_https", "fqdn_no_scheme", "ipv4_no_scheme", "ipv6_bracket"
])
def bootstrap_account(request):
    # By default, instantiate with a valid FQDN, but allow each test to mutate as needed.
    url = request.param
    return MockBootstrapAccount(server_url=url)

# -- TEST SCRIPT --

def is_url_fqdn(url):
    """
    Helper: Returns True if the URL host is an FQDN (not a numeric IPv4/IPv6).
    """
    try:
        # Use same logic as in class
        no_scheme_url = re.sub(r'^https?://', '', url)
        match = re.match(r"([^/:]+)", no_scheme_url)
        host = match.group(1) if match else no_scheme_url
        # Will throw ValueError if not IP, which is good
        ip_address(host)
        return False
    except ValueError:
        # Also FQDN should have at least one dot and no brackets (to avoid IPv6 string-in-brackets)
        return bool(re.match(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{2,63})+$", host))

def is_url_ip(url):
    # Use the static method in the class to determine IP address use.
    return MockBootstrapAccount.is_url_ip_address(url)

def test_bootstrap_server_url_is_fqdn_only(bootstrap_account):
    """
    Requirement:
    - The server URL in the bootstrap account must be an FQDN and CANNOT be an IP address.
    """
    server_url = bootstrap_account.get_server_url()
    
    # Step 2: Locate and parse the server URL field
    # Step 3: Check if server URL is an IP or FQDN
    is_ip = is_url_ip(server_url)
    is_fqdn = is_url_fqdn(server_url)
    
    # Pass/fail based on actual value
    if is_ip:
        assert not is_ip, (
            f"FAIL: Bootstrap account '[{server_url}]' uses an IP address! "
            "Per TS.34_BOOTSTRAP_REQ_NO_IP this is not permitted."
        )
    else:
        assert is_fqdn, f"FAIL: Server URL '{server_url}' is not a valid FQDN."
    print(f"Bootstrap account server URL: {server_url} | FQDN: {is_fqdn} | IP: {is_ip}")

def test_attempt_to_provision_ip_address_rejected():
    """
    Attempts to set/provision an IP server URL must be rejected or not possible.
    """
    acc = MockBootstrapAccount("dm.example.com")
    ip_urls = [
        "10.11.12.13",
        "https://172.18.1.3/somepath",
        "[2001:db8::1]",
        "https://[2001:4860:4860::8888]:443/api"
    ]
    for ip_url in ip_urls:
        accepted = acc.set_server_url(ip_url)
        assert not accepted, (
            f"FAIL: Setting server URL to IP address ('{ip_url}') was accepted, "
            "but must be rejected as per TS.34_BOOTSTRAP_REQ_NO_IP."
        )
        print(f"Attempted to provision '{ip_url}' as server URL: {'rejected' if not accepted else 'accepted'}")

def test_supports_multiple_operational_states():
    """
    Repeat for multiple states (factory, post-activation): Server URL must never be IP.
    """
    # Factory state
    acc = MockBootstrapAccount("factory.dm.operator.com")
    assert is_url_fqdn(acc.get_server_url()), "Fail: Factory state uses non-FQDN server URL"
    # Simulate post-activation (e.g. after device is configured in the field)
    acc.set_server_url("activated.mgmt.carrier.org")
    assert is_url_fqdn(acc.get_server_url()), "Fail: Post-activation state uses non-FQDN server URL"
    print(f"Factory: {acc.get_server_url()} | Post-activation: {acc.get_server_url()}")

```
---

**How to use/adapt:**
- Save as `tests/test_bootstrap_no_ip_in_server_url.py`.
- Replace the mocks with the API or CLI used by your IoT device/module to retrieve, display, and provision the bootstrap account server URL.
- Run with:
  ```bash
  pytest tests/test_bootstrap_no_ip_in_server_url.py
  ```
- The script performs both positive and negative assertions for FQDN/IP acceptance and rejection, per TS.34_BOOTSTRAP_REQ_NO_IP, and can be easily adapted to your integration environment.

**Coverage:**  
- Server URL must be FQDN (never IP address)
- Rejection of IP address provisioning  
- Applies in all device states (factory, post-activation, etc.)
- Print/log output included for audit and CI reporting  

Let me know if you need hooks for a real device DM interface, fielded logs, or configuration crawlers!