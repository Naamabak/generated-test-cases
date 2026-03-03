```python
# File: tests/test_ce_policy_single_active.py

"""
Test Case for:
Requirement ID : TS.34_7.2.1_REQ_001

Requirement:
A IoT Communication Module can have many Connection Efficiency Policies configured,
but only one of these CE Policies SHALL be active at any given time.

References:
- GSMA TS.34 v8.0, Section 7.2.1, Requirement TS.34_7.2.1_REQ_001
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf (page 40–41)
"""

import pytest

# --- MOCK / PLACEHOLDER IMPLEMENTATION ---
# For integration, replace this with your device API or management interface hooks.

class MockCEPolicyModule:
    """
    Simulates a CE Policy management interface for an IoT Communication Module.
    Each policy has 'configured', 'active', and 'can_activate' states.
    """

    def __init__(self, policies=None):
        self.policies = policies or {
            "policy1": {"configured": True, "active": True, "priority": 1},
            "policy2": {"configured": True, "active": False, "priority": 2},
            "policy3": {"configured": True, "active": False, "priority": 3},
        }
        # Only one active at any given moment

    def query_configured_policies(self):
        """Returns a list of all (configured) CE Policy names."""
        return [name for name, meta in self.policies.items() if meta["configured"]]

    def get_active_policy(self):
        """Returns the name of the currently active policy."""
        for name, meta in self.policies.items():
            if meta["active"]:
                return name
        return None

    def activate_policy(self, policy_name):
        """Deactivate all, then activate the requested policy (if it is configured)."""
        if policy_name not in self.policies or not self.policies[policy_name]["configured"]:
            return False  # Policy not available
        for n in self.policies:
            self.policies[n]["active"] = False
        self.policies[policy_name]["active"] = True
        return True

    def activate_many_policies(self, policy_names):
        """
        Attempts to activate >1 policy at once.
        Only allows one active at any moment.
        Returns name of policy left active.
        """
        activated = []
        for p in policy_names:
            if p in self.policies and self.policies[p]["configured"]:
                activated.append(p)
        # Only last one in the list is left active ("last write wins")
        if activated:
            for n in self.policies:
                self.policies[n]["active"] = False
            last = activated[-1]
            self.policies[last]["active"] = True
            return last
        return None

    def get_policy_states(self):
        """Returns a dict of {policy_name: is_active}."""
        return {name: meta["active"] for name, meta in self.policies.items()}

    def reset(self):
        for name in self.policies:
            self.policies[name]["active"] = False
        self.policies["policy1"]["active"] = True

# --- PYTEST FIXTURE ---
@pytest.fixture
def ce_policy_module():
    mod = MockCEPolicyModule()
    yield mod
    mod.reset()

# --- TEST SCRIPT ---
def test_only_single_ce_policy_active(ce_policy_module):
    """
    TS.34_7.2.1_REQ_001:
    - Multiple policies can be configured.
    - Only one may ever be active at any time.
    - Switching policies deactivates the other(s).
    - Simultaneous activation is not permitted.
    """

    # Step 1: Query for all configured CE Policies
    configured_policies = ce_policy_module.query_configured_policies()
    assert len(configured_policies) >= 2, (
        "Should have at least two CE policies configured for this test."
    )
    print("Configured CE Policies:", configured_policies)

    # Step 2: Check the starting active CE Policy
    active_initial = ce_policy_module.get_active_policy()
    assert active_initial in configured_policies, (
        "No valid policy is active initially."
    )
    states = ce_policy_module.get_policy_states()
    assert sum(states.values()) == 1, (
        "More than one active policy at the same time initially!"
    )
    print("Initial active CE Policy:", active_initial)

    # Step 3: Activate a different policy
    next_policy = [p for p in configured_policies if p != active_initial][0]
    res = ce_policy_module.activate_policy(next_policy)
    assert res, f"Failed to activate policy '{next_policy}'"
    active_now = ce_policy_module.get_active_policy()
    assert active_now == next_policy, (
        "After activation, the requested policy is not the only active one."
    )

    # Step 4: Ensure no other policy is simultaneously active
    states = ce_policy_module.get_policy_states()
    active_policies = [name for name, is_active in states.items() if is_active]
    assert len(active_policies) == 1, (
        f"Multiple active policies found: {active_policies}"
    )

    # Step 5: Attempt to activate more than one policy at once
    all_policies = configured_policies
    ce_policy_module.activate_many_policies(all_policies)
    states2 = ce_policy_module.get_policy_states()
    active_policies2 = [name for name, is_active in states2.items() if is_active]
    assert len(active_policies2) == 1, (
        f"After attempting to activate multiple, more than one active: {active_policies2}"
    )
    print("Only one policy active after batch-activation attempt:", active_policies2)

    # Step 6: Any attempt to activate more than one must always result in only one remaining active.
    ce_policy_module.activate_policy("policy3")
    ce_policy_module.activate_many_policies(["policy2", "policy1"])
    states3 = ce_policy_module.get_policy_states()
    assert sum(states3.values()) == 1
    final_active = ce_policy_module.get_active_policy()
    print("Final active CE Policy:", final_active)

    # Step 7: All transitions and responses are logged (replace with device logs in integration)
    print("Activation state after each operation:", states, states2, states3)

@pytest.mark.parametrize("policies", [["policy1", "policy2"], ["policy2", "policy3"], ["policy3", "policy1"]])
def test_simultaneous_policy_activation_not_permitted(ce_policy_module, policies):
    """
    Any attempt to activate more than one policy at once, or simulate bulk/config race, must not result in >1 active.
    """
    ce_policy_module.reset()
    ce_policy_module.activate_many_policies(policies)
    state = ce_policy_module.get_policy_states()
    actives = [name for name, active in state.items() if active]
    assert len(actives) == 1, (
        f"More than one CE Policy is active after simultaneous activation attempt: {actives}"
    )
    print(f"Bulk activation for {policies}: Only active policy: {actives[0]}")

```
---

**Instructions:**
- Place as `tests/test_ce_policy_single_active.py`.
- Replace the mock implementation with your device management API, CLI, or other integration mechanism.
- Run via:
  ```bash
  pytest tests/test_ce_policy_single_active.py
  ```
- Assert and print statements strictly follow TS.34_7.2.1_REQ_001 and pass/fail criteria; logs/prints serve for audit and cross-check.
- To extend for integration, adapt the activation/query functions to your hardware, cloud, or live CE Policy management tool.