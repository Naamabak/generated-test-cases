```python
# File: tests/test_local_diagnostic_interface.py

"""
Test Case for:
Requirement ID : TS.34_D.2_REQ_001

Requirement:
The IoT Communications Module SHALL support a local interface (e.g., RS-232, USB, or similar)
over which local diagnostic information may be obtained.

References:
- GSMA TS.34 v8.0, Annex D, TS.34_D.2_REQ_001 (page 72)
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
- Section D.2 (Local Diagnostic Requirements and Interface Examples)
"""

import pytest

# --- MOCK OR DEMONSTRATIVE INTERFACE IMPLEMENTATION ---
# For lab integration: replace with your physical/OS/driver interface using pyserial, pyusb, or actual device API.

class MockLocalInterface:
    """
    Simulates local interface access to IoT Communication Module diagnostics.
    Replace with real serial/USB/diagnostic interface code for actual tests.
    """
    SUPPORTED_INTERFACES = ['RS-232', 'USB']

    def __init__(self, interface_type):
        assert interface_type in self.SUPPORTED_INTERFACES
        self.interface_type = interface_type
        self.connected = False
        self.powered_on = True
        self.diagnostic_data = {
            "status": "OK",
            "firmware_version": "v1.2.3",
            "imei": "357723091234567",
            "signal_strength": -77,
            "temp_celsius": 32,
            "logs": ["Boot ok", "Network registered", "No errors"]
        }

    def connect(self):
        if self.powered_on:
            self.connected = True
            return True
        raise RuntimeError("Module not powered on")

    def disconnect(self):
        self.connected = False

    def issue_diagnostic_command(self, command):
        """
        Simulate sending a command for diagnostic info (e.g., 'AT+DIAG' or 'GETINFO').
        You can add command-specific handling as required by your interface/API.
        """
        if not self.powered_on or not self.connected:
            raise RuntimeError("No connection to module")
        # For demo, 'GETDIAG' always succeeds:
        if command in ("AT+DIAG", "GETDIAG", "INFO", "DEBUG"):
            return self.diagnostic_data
        raise ValueError(f"Unsupported command: {command}")

    def power_cycle(self):
        self.powered_on = False
        self.disconnect()
        # Simulate brief power-off
        self.powered_on = True
        # State remains; diagnostics should persist
        return True

    def is_interface_accessible(self):
        return self.connected

# --- TEST FIXTURE (can be extended for real or multiple interface types supported) ---
@pytest.fixture(params=['RS-232', 'USB'])
def local_diag_interface(request):
    interface = MockLocalInterface(interface_type=request.param)
    return interface

# --- TEST SCRIPT STARTS ---

def test_local_diagnostic_access_and_retrieval(local_diag_interface):
    """
    Main TS.34_D.2_REQ_001 test covering:
        - Physical connection via local interface (RS-232/USB)
        - Diagnostic info retrieval with correct command
        - Data content, repeatability, disconnect/reconnect persistence
    """
    # Step 1: Connect via local interface
    assert local_diag_interface.connect(), "Failed to connect to module over local interface"

    # Step 2: Retrieve diagnostics using supported command
    diag_data = local_diag_interface.issue_diagnostic_command("GETDIAG")
    assert diag_data and isinstance(diag_data, dict), "No or invalid diagnostic data returned"
    assert "status" in diag_data and diag_data["status"] == "OK"
    assert "firmware_version" in diag_data
    assert "imei" in diag_data
    assert "signal_strength" in diag_data
    print(f"Retrieved diagnostic info over {local_diag_interface.interface_type}:", diag_data)

    # Step 3: Disconnect and reconnect, retrieve diagnostics again to ensure persistence
    local_diag_interface.disconnect()
    assert not local_diag_interface.is_interface_accessible()
    local_diag_interface.connect()
    diag_data2 = local_diag_interface.issue_diagnostic_command("GETDIAG")
    assert diag_data2 == diag_data, "Diagnostic info did not persist or changed unexpectedly after reconnection"

    # Step 4: Power cycle, reconnect and verify diagnostic interface remains available
    local_diag_interface.power_cycle()
    local_diag_interface.connect()
    diag_after_pwr = local_diag_interface.issue_diagnostic_command("GETDIAG")
    assert diag_after_pwr == diag_data, "Diagnostic data incorrect or unavailable after power cycle"

    # Step 5: Interface must be listed in supported and physically accessible interfaces
    assert local_diag_interface.interface_type in local_diag_interface.SUPPORTED_INTERFACES

    # Step 6: Attempt unsupported command and expect error
    with pytest.raises(ValueError):
        local_diag_interface.issue_diagnostic_command("BADCMD")

    print(f"{local_diag_interface.interface_type}: Local diagnostic interface test passed successfully.")

# Optionally, extend for edge handling:
@pytest.mark.parametrize("interface_type", ['RS-232', 'USB'])
def test_interface_disconnect_and_availability(interface_type):
    """
    Interface remains accessible and diagnostics are retrievable before and after disconnect/reconnect.
    """
    intf = MockLocalInterface(interface_type)
    intf.connect()
    assert intf.is_interface_accessible()
    intf.disconnect()
    assert not intf.is_interface_accessible()
    intf.connect()
    data = intf.issue_diagnostic_command("GETDIAG")
    assert data["status"] == "OK"
    print(f"{interface_type}: Disconnect/reconnect persistence confirmed.")

```
---

**Instructions:**
- Save this file as `tests/test_local_diagnostic_interface.py`.
- For real hardware/production, replace `MockLocalInterface` methods with physical port (e.g., pyserial for RS-232, pyusb for USB) and real command/response parsing.
- To execute: `pytest tests/test_local_diagnostic_interface.py`
- Print/log statements and assertion outcomes support both evidence and traceability for all TS.34_D.2_REQ_001 entry/exit criteria.
- Extend/parametrize for additional local interfaces by updating the fixture parameter list.

Let me know if you need a test harness for direct USB/serial port access or vendor-specific diagnostic commands!