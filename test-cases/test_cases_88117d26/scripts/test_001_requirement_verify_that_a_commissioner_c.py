```python
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

"""
Test Case ID:      TC-CSA-001-CM-DISCOVERY
Requirement ID:    CM
Test Description:  Verify Commissioner can discover Nodes in Commissioning Mode by browsing for the _CM subtype
                   using avahi-browse _CM._sub._matterc._udp -r or equivalent tools.
"""

import subprocess
import re
import pytest

@pytest.mark.asyncio
@pytest.mark.cm_discovery
class TestCMDiscovery:
    """
    Test for discovering Nodes in Commissioning Mode using avahi-browse or equivalent.
    """

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """
        Pre-conditions:
        1. At least one Node must be in Commissioning Mode and connected to the same network as the Commissioner.
        2. The Commissioner device must have avahi or an equivalent browsing tool installed and properly configured.
        3. Network connectivity between Commissioner and Nodes must be stable and operational.
        Post-conditions:
        1. No system state change, Node(s) remain in Commissioning Mode.
        2. Clean up, if necessary.
        """
        # Setup would normally ensure the node is in commissioning mode before the test runs.
        # This is a placeholder, as commissioning is assumed set per test setup instructions.
        yield
        # No teardown/post-cleanup necessary for this test (Node remains in Commissioning Mode).

    def test_commissioning_mode_discovery(self):
        """
        Steps:
        1. Ensure at least one Node is placed in Commissioning Mode. (Assumed by fixture/pre-conditions)
        2. Open a terminal on the Commissioner device. (Automated by subprocess call)
        3. Execute discovery command.
        4. Observe and parse output for discovered services in Commissioning Mode.
        """

        # Step 3: Execute the command to browse for _CM nodes
        command = ["avahi-browse", "_CM._sub._matterc._udp", "-r"]

        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=15)
        except FileNotFoundError:
            pytest.skip("avahi-browse is not installed or not found in PATH; skipping test.")
        except subprocess.CalledProcessError as e:
            pytest.fail(f"avahi-browse returned a non-zero exit code: {e.returncode}\nStdout:\n{e.stdout}\nStderr:\n{e.stderr}")
        except subprocess.TimeoutExpired:
            pytest.fail("avahi-browse command timed out; network or tool problem.")

        output = result.stdout

        # Step 4: Validate output contains at least one active Node and no errors
        # avahi-browse typical output for found services:
        # +   eth0 IPv6 ChipXYZ [1234] _CM._sub._matterc._udp local
        # or   =   eth0 IPv6 ChipXYZ [1234] _CM._sub._matterc._udp local
        service_lines = [line for line in output.splitlines() if re.search(r'_CM\._sub\._matterc\._udp', line)]
        assert service_lines, (
            "No Nodes in Commissioning Mode were discovered.\n"
            f"Output of avahi-browse:\n{output}"
        )

        for line in service_lines:
            # Step 4: Check key service properties in output line
            assert "_CM._sub._matterc._udp" in line, "Node did not advertise expected service type."
            # Attempt to capture the instance name and IP (if detailed output found)
            # Example: '=;eth0;IPv4;CHIP-EDC4321D5D335572._CM._sub._matterc._udp;local;192.168.1.101;8000'
            # The format can vary, but we look for presence of an instance + IP address pattern (IPv4 or IPv6)
            m = re.search(r'(\S+)\s+\S+\s+([\w-]+)\._CM\._sub\._matterc\._udp\s+(\S+)\s+(?:([\d\.]+)|\[(.*)\])', line)
            # At minimum, must see service type and an instance name.
            assert m or len(line.split()) >= 5, f"Service line missing required details: {line}"

        # Step 4: Assert no errors in stderr
        assert not result.stderr.strip(), f"Unexpected error output from avahi-browse:\n{result.stderr}"

        # If required: print the found services (for debug or log)
        # for line in service_lines:
        #     print(f"Discovered: {line}")

```

**Instructions:**  
- Save as `tests/test_cm_discovery.py` or your appropriate test directory.
- Adjust as needed if your Python test runner or continuous integration (CI) setup expects different hooks.
- This script will skip if `avahi-browse` is not found.
- For more advanced environments, you can adapt the discovery check to use other Zeroconf/mDNS libraries.
