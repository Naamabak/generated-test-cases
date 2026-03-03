```python
# File: tests/test_module_ipv6_functionality.py

"""
Test Case for:
Requirement ID : TS.34_5.3_REQ_004

Requirement:
The IoT Communications Module SHALL support the following IPv6 functionality:
  - Neighbour Discovery Protocol (subject to exceptions in 3GPP TS 23.060 (3G) or TS 23.401 (LTE))
  - Stateless Address Auto Configuration (SLAAC)
  - ICMPv6 protocol
  - IPv6 addressing architecture
  - IPv6 address text representation

References:
- GSMA TS.34 v8.0, Section 5.3, Requirement TS.34_5.3_REQ_004
- 3GPP TS 23.060 (3G), TS 23.401 (LTE), RFC 4291, RFC 2462/SLAAC
"""

import pytest
import re
import ipaddress

# ---- MOCK CLASSES (Replace with lab/integration interfaces as available) ----

class MockIoTCommsModuleIPv6:
    """
    Simulates an IoT Communications Module with IPv6 stack and log hooks (for demonstration).
    Replace with SDK/integration in production!
    """
    def __init__(self):
        self.interface_up = False
        self.ipv6_addresses = []
        self.neighbor_discovery_log = []
        self.icmpv6_log = []
        self.address_assigned = None

    def power_on_and_connect_ipv6(self):
        """Step 1: Power on and connect to IPv6 network (simulate link-local and global addresses assigned)"""
        self.interface_up = True
        # Example: SLAAC assigns an IPv6 address
        self.address_assigned = "2001:db8:abcd:0012:3456:78ff:fe12:abcd"
        self.ipv6_addresses = [self.address_assigned, "fe80::78ff:fe12:abcd"]  # Includes link-local
        # Neighbor Discovery, ICMPv6 simulated sessions initiated
        self.neighbor_discovery_log.append("Router Solicitation sent (ICMPv6, code=133)")
        self.neighbor_discovery_log.append("Router Advertisement received (ICMPv6, type=134)")
        self.neighbor_discovery_log.append("Neighbor Solicitation sent (ICMPv6, type=135)")
        self.neighbor_discovery_log.append("Neighbor Advertisement received (ICMPv6, type=136)")
        self.icmpv6_log.extend([
            ("echo_request", "128"),
            ("echo_reply", "129"),
            ("router_solicitation", "133"),
            ("router_advertisement", "134"),
            ("neighbor_solicitation", "135"),
            ("neighbor_advertisement", "136"),
        ])

    def get_ipv6_addresses(self):
        return list(self.ipv6_addresses)

    def get_neighbor_discovery_log(self):
        return list(self.neighbor_discovery_log)

    def get_icmpv6_log(self):
        return list(self.icmpv6_log)

    def get_address_text_representations(self):
        return [str(ip) for ip in self.ipv6_addresses]

    def reset(self):
        self.__init__()

# ---- PYTEST FIXTURE ----

@pytest.fixture
def ipv6_module():
    module = MockIoTCommsModuleIPv6()
    module.power_on_and_connect_ipv6()
    yield module
    module.reset()

# ---- TEST SCRIPT ----

def test_module_supports_icmpv6_neighbor_discovery(ipv6_module):
    """
    a) ICMPv6 Neighbor Discovery (compliant and as-per 3GPP exceptions)
    """
    nd_log = ipv6_module.get_neighbor_discovery_log()
    # Verify presence of key ND messages
    types = ["Router Solicitation", "Router Advertisement", "Neighbor Solicitation", "Neighbor Advertisement"]
    found_types = [any(t in entry for entry in nd_log) for t in types]
    assert all(found_types), "Not all required Neighbor Discovery messages found in log"
    # 3GPP TS 23.060/23.401 exceptions: Some features may be omitted, check spec for details as needed

def test_module_performs_stateless_address_autoconfiguration(ipv6_module):
    """
    b) Stateless Address Auto Configuration (SLAAC)
    """
    ipv6s = ipv6_module.get_ipv6_addresses()
    # Must have a valid global and link-local address
    found_global = any(ip.startswith("2001:db8:") for ip in ipv6s)
    found_linklocal = any(ip.startswith("fe80::") for ip in ipv6s)
    assert found_global, "No global IPv6 address assigned via SLAAC"
    assert found_linklocal, "No link-local IPv6 address assigned"

def test_module_supports_icmpv6_protocol(ipv6_module):
    """
    c) General ICMPv6 protocol use
    """
    icmpv6_log = ipv6_module.get_icmpv6_log()
    required_types = {"echo_request": "128", "echo_reply": "129", "router_solicitation": "133", "router_advertisement": "134"}
    log_types = {entry[0]: entry[1] for entry in icmpv6_log}
    for k, v in required_types.items():
        assert log_types.get(k) == v, f"ICMPv6 message {k} (type {v}) not found in log"

def test_module_ipv6_address_architecture(ipv6_module):
    """
    d) Proper IPv6 addressing architecture (RFC 4291)
    """
    addrs = ipv6_module.get_ipv6_addresses()
    for addr in addrs:
        # Verify that this is a valid IPv6 address (RFC 4291 format)
        try:
            ip = ipaddress.ip_interface(addr)
            assert ip.version == 6, f"Address {addr} is not IPv6"
        except ValueError:
            pytest.fail(f"Address {addr} is not a valid IPv6 address per RFC 4291")

def test_module_ipv6_address_text_representation(ipv6_module):
    """
    e) Accurate representation of IPv6 addresses in text format (RFC 4291 Section 2.2)
    """
    addrs = ipv6_module.get_address_text_representations()
    for addr in addrs:
        # Pattern: Valid IPv6 text (compressed/expanded) with allowed colons, hexadecimal
        assert re.fullmatch(r"([0-9a-fA-F]{1,4}:){1,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|::([0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}", addr) or "::" in addr, \
            f"Address {addr} not in correct IPv6 text representation"
        # Also confirm it round-trips using Python's own standard library
        try:
            parsed_back = ipaddress.IPv6Address(addr)
            assert str(parsed_back) == ipaddress.IPv6Address(addr).compressed
        except Exception as e:
            pytest.fail(f"Address '{addr}' is not valid IPv6 text representation: {e}")

def test_module_ipv6_functionality_combined(ipv6_module):
    """
    Summary test: All five functionalities in one routine for traceability/logging/demo.
    """
    test_module_supports_icmpv6_neighbor_discovery(ipv6_module)
    test_module_performs_stateless_address_autoconfiguration(ipv6_module)
    test_module_supports_icmpv6_protocol(ipv6_module)
    test_module_ipv6_address_architecture(ipv6_module)
    test_module_ipv6_address_text_representation(ipv6_module)
    print("All IPv6 functionality checks passed for module:", ipv6_module.get_ipv6_addresses())

```
---

**Instructions:**

- Save as `tests/test_module_ipv6_functionality.py`
- Replace mock class logic with your real module/integration or interface with live testbeds/packet traces.
- Add/extend hooks for neighbor discovery/ICMPv6 traces, address assignment, and control interfaces for deep validation.
- Run with:

  ```bash
  pytest tests/test_module_ipv6_functionality.py
  ```

**Coverage:**
- All five IPv6 features: ND, SLAAC, general ICMPv6, addressing, and text representation.
- Each assertion and step is directly mapped to TS.34_5.3_REQ_004 pass/fail criteria and covers RFC 4291, 3GPP, and SLAAC as appropriate.

Let me know if you need integration examples or hooks for a live device or network testbed!
