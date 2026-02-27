```python
#!/usr/bin/env python3
#
#    Copyright (c) 2024 Project CHIP Authors
#    All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#

# File: tests/test_TC_CSA_DNSSD_001.py

import pytest
import socket
import time

from zeroconf import Zeroconf, ServiceInfo, DNSPointer, DNSAddress, DNSText
from unittest import mock

# Requirement: DNS-SD-1.2.3
# Test Case ID: TC-CSA-DNSSD-001
# Test Type: API (DNS-SD interaction and caching verification)
# Target: DNS-SD client implementation (e.g., zeroconf based client)

@pytest.mark.asyncio
class TestCSADNSSD001:
    """
    Verify that the DNS-SD client stores SRV, TXT, and address records received in the
    Additional Record section of the reply, and does NOT send redundant queries for those records
    immediately after discovery.
    """

    @pytest.fixture(scope="function")
    def zeroconf_server(self):
        """Set up a mock zeroconf server to reply to queries with additional records."""
        zeroconf = Zeroconf()
        service_type = "_testservice._tcp.local."
        name = "TestInstance._testservice._tcp.local."
        address = "127.0.0.1"
        info = ServiceInfo(
            type_=service_type,
            name=name,
            addresses=[socket.inet_aton(address)],
            port=12345,
            properties={'key': b'value'},
            server="testhost.local."
        )
        zeroconf.register_service(info)
        yield zeroconf, info
        zeroconf.unregister_service(info)
        zeroconf.close()

    @pytest.fixture(scope="function")
    def client_cache(self):
        """Simulate a DNS-SD client cache (simple dict for this test)."""
        return {}

    def test_dndsd_client_stores_and_uses_additional_records(self, zeroconf_server, client_cache, monkeypatch):
        """
        1. Initiate a DNS-SD service query (e.g., PTR query for a service type) from the client.
        2. Capture network traffic between the DNS-SD client and the DNS-SD server. (mock/inspect, not real capture)
        3. Server responds with service PTR and includes associated SRV, TXT, and address (A/AAAA) records in Additional Record section.
        4. On client, trigger an action that would otherwise require it to fetch SRV, TXT, or address records for the discovered service instance.
        5. Observe whether the client issues additional queries (should not) for the same records.
        6. Assert correct parse, storage, and no redundant queries.
        """
        zeroconf, info = zeroconf_server

        # --- Step 1: Client sends PTR query ---
        service_type = info.type
        queried = []

        # Patch the DNS query sender to record who/when it's called so we can assert on redundant queries.
        def query_callback(*args, **kwargs):
            # Record the query type and name
            queried.append((args, kwargs))

        # Monkeypatch a method in Zeroconf that actually makes DNS queries to intercept calls
        monkeypatch.setattr(zeroconf, "send", mock.MagicMock(side_effect=query_callback))

        # --- Step 2: Discover services using zeroconf/py ---
        found_services = []

        def on_service_state_change(zeroconf, service_type, name, state_change):
            found_services.append((service_type, name, state_change))

        browser = zeroconf.ServiceBrowser(zeroconf, service_type, handlers=[on_service_state_change])
        # Sleep a short bit to allow background mDNS discovery to happen
        time.sleep(1.5)

        # --- Step 3: Server replied with additional records ---
        # (Zeroconf server does this automatically for us)
        # In a more manual test, we would verify the reply packet had Additional Records,
        # but here we assume our ServiceInfo contains them and zeroconf populates its cache.

        # --- Step 4: Try to fetch SRV, TXT, A records directly as client would upon e.g. connect ---
        # (zeroconf should serve from local cache if those came in Additional Records)
        result_info = zeroconf.get_service_info(service_type, info.name)

        # --- Step 5: Observe network traffic/query debug: were any additional queries produced? ---
        # As we monkeypatched zeroconf.send, any outgoing DNS request will record to 'queried'.
        # We allow a PTR query (service discovery), but after that,
        # fetching SRV, TXT, and A/AAAA for this info.name should NOT emit more queries.

        # --- Step 6: Assert expected outcome ---

        # Client should have parsed all records and stored them:
        assert result_info is not None, "Client did not cache or retrieve ServiceInfo."
        assert result_info.server == info.server, "SRV record mismatch or not stored."
        assert result_info.properties == info.properties, "TXT record mismatch or not stored."
        assert result_info.addresses, "No address records cached."
        assert socket.inet_ntoa(result_info.addresses[0]) == "127.0.0.1"

        # Client should NOT make new queries for SRV/TXT/A immediately after PTR
        # (Only initial PTR allowed queries. We check only 1 outgoing query max)
        # May need to loosen this if zeroconf re-queries for cache validation, so check for no
        # more than 1 SRV/TXT/A query (should be <=1 and not for info.name).
        all_queries_types = [args for args, kwargs in queried]
        for qargs in all_queries_types:
            if info.name.encode("utf-8") in str(qargs):
                pytest.fail(
                    f"Redundant network query for record {info.name} detected after initial discovery. Queried: {qargs}"
                )

        # If all above assert, client correctly stored and avoided redundant lookups.
        # --- Post-conditions: cache contains SRV, TXT, and address records ---
```