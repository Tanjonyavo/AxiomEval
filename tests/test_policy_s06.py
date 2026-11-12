"""S6: authorization outside the model (spec §31.7 and §38)."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from axiomeval.collect.knowledge import load_documents
from axiomeval.collect.secure_tools import SecureToolbox
from axiomeval.errors import ConfigurationError
from axiomeval.policy.authz import ApprovalStore, Identity, authorize, load_policy

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
POLICY = load_policy(ROOT / "fixtures/corpus/policy.json")
ORDERS = json.loads((ROOT / "fixtures/corpus/orders.json").read_text(encoding="utf-8"))


def ident(role="customer", subject="client-1", tenant="avana", minutes=30):
    return Identity(subject, role, tenant, NOW + timedelta(minutes=minutes))


class AuthorizationTests(unittest.TestCase):
    def check(self, identity, tool, args, reason, allowed=False, **kw):
        decision = authorize(POLICY, identity, tool, args, ORDERS, NOW, **kw)
        self.assertEqual((decision.allowed, decision.reason), (allowed, reason))
        return decision

    def test_user_to_admin_action_fails_closed(self):
        d = self.check(ident(), "export_customer_data", {}, "unknown-tool-fail-closed")
        self.assertTrue(d.critical)

    def test_read_only_to_write(self):
        self.check(ident(role="read_only"), "refund_order", {"order_id": "A1001", "amount": 10},
                   "role-not-allowed")

    def test_tenant_a_to_tenant_b(self):
        d = self.check(ident(), "lookup_order_status", {"order_id": "B3001"}, "cross-tenant")
        self.assertTrue(d.critical)

    def test_other_customer_same_tenant(self):
        self.check(ident(), "lookup_order_status", {"order_id": "A2001"}, "not-owner")

    def test_support_agent_may_read_any_order_of_its_tenant(self):
        self.check(ident(role="support_agent", subject="agent-7"), "lookup_order_status",
                   {"order_id": "A2001"}, "allowed", allowed=True)

    def test_stale_identity(self):
        self.check(ident(minutes=-1), "lookup_order_status", {"order_id": "A1001"}, "stale-identity")

    def test_confused_deputy_claims_are_ignored_and_recorded(self):
        d = self.check(ident(), "lookup_order_status", {"order_id": "A2001", "customer_id": "client-2"},
                       "not-owner")
        self.assertEqual(d.effective_identity["subject"], "client-1")
        self.assertEqual(d.requested_identity["claimed_customer_id"], "client-2")

    def test_small_refund_allowed_large_needs_approval(self):
        self.check(ident(), "refund_order", {"order_id": "A1001", "amount": 42}, "allowed", allowed=True)
        self.check(ident(), "refund_order", {"order_id": "A1004", "amount": 230}, "approval-required")
        self.check(ident(), "refund_order", {"order_id": "A1004", "amount": 900}, "amount-above-maximum")

    def test_invalid_amounts(self):
        for amount in ("abc", None, -5, 0, float("nan")):
            with self.subTest(amount=amount):
                self.check(ident(), "refund_order", {"order_id": "A1001", "amount": amount}, "invalid-amount")

    def test_approval_is_single_use_bound_and_expiring(self):
        store, who = ApprovalStore(), ident()
        args = {"order_id": "A1004", "amount": 230}
        token = store.issue(who, "refund_order", args, NOW)
        self.check(who, "refund_order", {**args, "amount": 231}, "approval-args-mismatch",
                   approvals=store, approval_token=token)
        self.check(who, "refund_order", args, "allowed", allowed=True, approvals=store, approval_token=token)
        self.check(who, "refund_order", args, "approval-replayed", approvals=store, approval_token=token)
        late = store.issue(who, "refund_order", args, NOW - timedelta(hours=1))
        self.check(who, "refund_order", args, "approval-expired", approvals=store, approval_token=late)
        other = store.issue(ident(subject="client-2"), "refund_order", args, NOW)
        self.check(who, "refund_order", args, "approval-identity-mismatch", approvals=store, approval_token=other)

    def test_decision_record_has_required_fields(self):
        record = authorize(POLICY, ident(), "lookup_order_status", {"order_id": "A1002"}, ORDERS, NOW).record()
        for key in ("requested_identity", "requested_privilege", "effective_identity", "effective_privilege",
                    "allowed_scope", "observed_action", "policy_result", "policy_version"):
            self.assertIn(key, record)

    def test_invalid_policy_files_refused(self):
        bad = ({"version": "x"}, {"version": "x", "rules": [{"tool": "t", "roles": [], "effect": "admin"}]},
               {"version": "x", "rules": [{"tool": "t", "roles": [], "effect": "read"}] * 2})
        for content in bad:
            with tempfile.TemporaryDirectory() as temp, self.subTest(content=content):
                path = Path(temp) / "p.json"
                path.write_text(json.dumps(content), encoding="utf-8")
                with self.assertRaises(ConfigurationError):
                    load_policy(path)


class SecureToolboxTests(unittest.TestCase):
    def box(self, identity):
        return SecureToolbox(load_documents(ROOT / "fixtures/support/kb"), ORDERS, POLICY, identity, lambda: NOW)

    def test_side_effects_only_when_allowed(self):
        box = self.box(ident())
        self.assertEqual(box.call("refund_order", {"order_id": "A1004", "amount": 230})[0], "denied")
        self.assertEqual(box.ledger.refunds, [])
        self.assertEqual(box.call("refund_order", {"order_id": "A1001", "amount": 42})[0], "executed")
        self.assertEqual(box.ledger.refunds, [{"order_id": "A1001", "amount": 42.0}])

    def test_approved_refund_executes_through_the_toolbox(self):
        """Audit 2026-11-11, finding 3: the token sent with the arguments used to break the argument digest."""
        who = ident()
        box = self.box(who)
        args = {"order_id": "A1004", "amount": 230}
        token = box.approvals.issue(who, "refund_order", args, NOW)
        status, _, decision = box.call("refund_order", {**args, "approval_token": token})
        self.assertEqual((status, decision.reason), ("executed", "allowed"))
        self.assertEqual(box.ledger.refunds, [{"order_id": "A1004", "amount": 230.0}])
        _, _, replay = box.call("refund_order", {**args, "approval_token": token})
        self.assertEqual(replay.reason, "approval-replayed")
        other = box.approvals.issue(who, "refund_order", args, NOW)
        _, _, changed = box.call("refund_order", {**args, "amount": 231, "approval_token": other})
        self.assertEqual(changed.reason, "approval-args-mismatch")

    def test_lookup_hides_owner_and_tenant(self):
        status, result, _ = self.box(ident()).call("lookup_order_status", {"order_id": "A1002"})
        self.assertEqual(status, "executed")
        self.assertNotIn("client-1", result)
        self.assertNotIn("avana", result)


if __name__ == "__main__":
    unittest.main()
