```python
# File: tests/test_oma_dm_account_limit.py

"""
Test Case for:
Requirement ID : TS.34_5.10_REQ_012

Requirement:
IoT Communications Modules SHALL support only 3 DM Accounts per Mobile Network Operator (MNO).

References:
- GSMA TS.34 v8.0, Section 5.10, Requirement TS.34_5.10_REQ_012
- OMA Device Management (OMADM) specification (DM account node management)
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest

# --- MOCK/PLACEHOLDER CLASS FOR MODULE ---

class MockOmaDmModule:
    """
    Simulates an IoT Communications Module supporting a maximum of 3 DM Accounts per MNO.
    """
    MAX_DM_ACCOUNTS_PER_MNO = 3

    def __init__(self):
        # Structure: { mno_id: [{account_id, credentials}] }
        self.dm_accounts = {}

    def add_dm_account(self, mno_id, account_id, credentials):
        accounts = self.dm_accounts.get(mno_id, [])
        if len(accounts) >= self.MAX_DM_ACCOUNTS_PER_MNO:
            return False  # Deny creation above allowed maximum
        # account_id must also be unique for this MNO
        if any(acc['account_id'] == account_id for acc in accounts):
            return False  # Duplicate not allowed
        accounts.append({"account_id": account_id, "credentials": credentials})
        self.dm_accounts[mno_id] = accounts
        return True

    def list_dm_accounts(self, mno_id):
        return list(self.dm_accounts.get(mno_id, []))

    def delete_dm_account(self, mno_id, account_id):
        accounts = self.dm_accounts.get(mno_id, [])
        updated_accounts = [acc for acc in accounts if acc["account_id"] != account_id]
        self.dm_accounts[mno_id] = updated_accounts

    def get_total_accounts(self, mno_id):
        return len(self.list_dm_accounts(mno_id))

    def reset(self):
        self.dm_accounts.clear()

# --- FIXTURE ---

@pytest.fixture
def module():
    mod = MockOmaDmModule()
    yield mod
    mod.reset()

# --- TEST SCRIPT ---

def test_dm_account_limit_per_mno(module):
    """
    TS.34_5.10_REQ_012:
    The module allows creation of up to 3 DM Accounts per MNO, not a fourth.
    The rule is enforced during add/delete cycles as well.
    """

    mno_id = "MCC310MNC260"  # Example MNO identifier (e.g., IMSI MCC+MNC or profile ID)
    creds_template = lambda n: {"username": f"user{n}", "password": f"pw{n}"}

    # Step 1: Create three DM Accounts for the same MNO (should succeed)
    for n in range(1, 4):
        res = module.add_dm_account(mno_id, f"acc{n}", creds_template(n))
        assert res, f"Failed to create allowed DM account number {n} for MNO {mno_id}"

    accounts = module.list_dm_accounts(mno_id)
    assert len(accounts) == 3
    assert all(acc["account_id"] == f"acc{idx+1}" for idx, acc in enumerate(accounts))

    # Step 2: Try to create a fourth DM Account (should FAIL)
    res = module.add_dm_account(mno_id, "acc4", creds_template(4))
    assert not res, "Module accepted creation of fourth DM Account for the same MNO (limit exceeded!)"

    # Step 3: Delete one existing DM Account, list remaining
    module.delete_dm_account(mno_id, "acc2")
    accounts_post_delete = module.list_dm_accounts(mno_id)
    assert len(accounts_post_delete) == 2
    assert "acc2" not in [acc["account_id"] for acc in accounts_post_delete]

    # Step 4: Add a new (third) account again after deletion (should SUCCEED)
    res = module.add_dm_account(mno_id, "acc5", creds_template(5))
    assert res, "Module should allow new third account after one is deleted"
    assert len(module.list_dm_accounts(mno_id)) == 3

    # Step 5: Try to add yet another (fourth) account again (should FAIL)
    res = module.add_dm_account(mno_id, "acc6", creds_template(6))
    assert not res, "Module allowed fourth DM Account addition after reuse (limit not enforced across add/delete cycles)"

    # Final: Print the accounts for audit/debug
    accounts_final = module.list_dm_accounts(mno_id)
    print("Final DM Accounts for MNO:", accounts_final)

@pytest.mark.parametrize("start,should_pass", [
    (["acc1", "acc2", "acc3"], True),   # 3 accounts OK
    (["accX", "accY", "accZ", "accW"], False)  # 4th not OK
])
def test_dm_account_limit_bulk(module, start, should_pass):
    mno_id = "TESTBULK1"
    creds = {"username": "testuser", "password": "pwtest"}
    for account_id in start[:-1]:
        assert module.add_dm_account(mno_id, account_id, creds)
    result = module.add_dm_account(mno_id, start[-1], creds)
    if should_pass:
        assert result
    else:
        assert not result

```

---

**How to use/adapt:**
- Save as `tests/test_oma_dm_account_limit.py`.
- Replace `MockOmaDmModule` with your device’s real OMA DM account management interface for integration or automation.
- Run with:
  ```bash
  pytest tests/test_oma_dm_account_limit.py
  ```
- Assertions and comments directly match the required GSMA TS.34_5.10_REQ_012 logic and exit criteria.