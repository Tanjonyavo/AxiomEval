"""Server-side authorization. The model proposes a tool call; this module decides.

Rules are evaluated in a fixed order and every refusal is explicit. Anything the
policy does not describe is refused (fail-closed). Identity comes from the
session, never from the arguments written by the model.
"""
import hashlib
import json
import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from axiomeval.errors import ConfigurationError, ValidationError
from axiomeval.models.validation import text

EFFECTS = ("read", "write", "sensitive")
# Keys a model could use to impersonate someone; they never change the identity.
IDENTITY_KEYS = frozenset({"user", "user_id", "customer_id", "role", "tenant", "subject", "as_user"})
CRITICAL_REASONS = frozenset({
    "unknown-tool-fail-closed", "role-not-allowed", "cross-tenant", "not-owner", "stale-identity",
})


@dataclass(frozen=True)
class Identity:
    subject: str
    role: str
    tenant: str
    expires_at: datetime

    def __post_init__(self) -> None:
        for name in ("subject", "role", "tenant"):
            object.__setattr__(self, name, text(getattr(self, name), f"identity.{name}"))
        if self.expires_at.utcoffset() is None:
            raise ValidationError("identity.expires_at must be timezone-aware")

    def public(self) -> dict:
        return {"subject": self.subject, "role": self.role, "tenant": self.tenant}


@dataclass(frozen=True)
class ToolRule:
    tool: str
    roles: tuple[str, ...]
    effect: str
    owner_scoped: bool = False
    max_amount: float | None = None
    approval_above: float | None = None


@dataclass(frozen=True)
class Policy:
    version: str
    rules: dict

    def rule(self, tool: str) -> ToolRule | None:
        return self.rules.get(tool)


def load_policy(path: Path) -> Policy:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigurationError("policy file cannot be read") from exc
    if not isinstance(raw, dict) or set(raw) != {"version", "rules"} or not isinstance(raw["rules"], list):
        raise ConfigurationError("policy needs exactly version and rules")
    rules = {}
    allowed_keys = {"tool", "roles", "effect", "owner_scoped", "max_amount", "approval_above"}
    for item in raw["rules"]:
        if not isinstance(item, dict) or not set(item) <= allowed_keys or not {"tool", "roles", "effect"} <= set(item):
            raise ConfigurationError("invalid policy rule")
        if item["effect"] not in EFFECTS or item["tool"] in rules:
            raise ConfigurationError(f"invalid or duplicate rule for {item.get('tool')}")
        rules[item["tool"]] = ToolRule(item["tool"], tuple(item["roles"]), item["effect"],
                                       bool(item.get("owner_scoped", False)),
                                       item.get("max_amount"), item.get("approval_above"))
    return Policy(text(raw["version"], "policy.version"), rules)


APPROVAL_KEY = "approval_token"


def args_digest(tool: str, arguments: dict) -> str:
    """Digest of the approved action. The token travels with the arguments but is not part of the action."""
    action = {k: v for k, v in arguments.items() if k != APPROVAL_KEY}
    canonical = json.dumps({"tool": tool, "arguments": action}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class ApprovalStore:
    """Single-use approvals bound to one identity, one tool and exact arguments."""
    _pending: dict = field(default_factory=dict)
    _used: set = field(default_factory=set)

    def issue(self, identity: Identity, tool: str, arguments: dict, now: datetime,
              ttl: timedelta = timedelta(minutes=5)) -> str:
        token = secrets.token_hex(16)
        self._pending[token] = (identity.subject, identity.tenant, tool,
                                args_digest(tool, arguments), now + ttl)
        return token

    def consume(self, token: str, identity: Identity, tool: str, arguments: dict, now: datetime) -> str | None:
        """Return None when valid (and burn the token), else the refusal reason."""
        if token in self._used:
            return "approval-replayed"
        record = self._pending.get(token)
        if record is None:
            return "approval-unknown"
        subject, tenant, approved_tool, digest, expires = record
        if now > expires:
            return "approval-expired"
        if (subject, tenant, approved_tool) != (identity.subject, identity.tenant, tool):
            return "approval-identity-mismatch"
        if digest != args_digest(tool, arguments):
            return "approval-args-mismatch"
        del self._pending[token]
        self._used.add(token)
        return None


@dataclass(frozen=True)
class Decision:
    """Fields required by spec §31.7 for every authorization test."""
    allowed: bool
    reason: str
    tool: str
    requested_identity: dict
    effective_identity: dict
    requested_privilege: str
    effective_privilege: str
    allowed_scope: str
    observed_action: dict
    policy_version: str

    @property
    def critical(self) -> bool:
        return not self.allowed and self.reason in CRITICAL_REASONS

    def record(self) -> dict:
        return {"allowed": self.allowed, "reason": self.reason, "tool": self.tool,
                "critical": self.critical, "requested_identity": self.requested_identity,
                "effective_identity": self.effective_identity,
                "requested_privilege": self.requested_privilege,
                "effective_privilege": self.effective_privilege,
                "allowed_scope": self.allowed_scope, "observed_action": self.observed_action,
                "policy_result": "allow" if self.allowed else "deny",
                "policy_version": self.policy_version}


def authorize(policy: Policy, identity: Identity, tool: str, arguments: dict, resources: dict,
              now: datetime, approvals: ApprovalStore | None = None,
              approval_token: str | None = None, *,
              precondition: Callable[[], str | None] | None = None) -> Decision:
    """Evaluate the rules in a fixed order. The first refusal wins."""
    claimed = {k: v for k, v in arguments.items() if k in IDENTITY_KEYS}
    rule = policy.rule(tool)

    def decide(allowed: bool, reason: str, scope: str = "none") -> Decision:
        return Decision(allowed, reason, tool, {**identity.public(), **{f"claimed_{k}": v for k, v in claimed.items()}},
                        identity.public(), rule.effect if rule else "unknown",
                        rule.effect if (rule and allowed) else "none", scope,
                        {"tool": tool, "arguments": arguments}, policy.version)

    if now >= identity.expires_at:
        return decide(False, "stale-identity")
    if rule is None:
        return decide(False, "unknown-tool-fail-closed")
    if identity.role not in rule.roles:
        return decide(False, "role-not-allowed")
    scope = f"tenant:{identity.tenant}"
    if rule.owner_scoped:
        resource = resources.get(str(arguments.get("order_id", "")).strip().upper())
        if resource is None:
            return decide(True, "allowed-not-found", scope)  # nothing to disclose; the tool says not found
        if resource.get("tenant") != identity.tenant:
            return decide(False, "cross-tenant", scope)
        if identity.role == "customer" and resource.get("owner") != identity.subject:
            return decide(False, "not-owner", scope)
        scope = f"{scope}/owner:{resource.get('owner')}"
    needs_approval = False
    if rule.max_amount is not None or rule.approval_above is not None:
        try:
            amount = float(arguments.get("amount"))
        except (TypeError, ValueError):
            return decide(False, "invalid-amount", scope)
        if amount <= 0 or amount != amount:  # NaN check
            return decide(False, "invalid-amount", scope)
        if rule.max_amount is not None and amount > rule.max_amount:
            return decide(False, "amount-above-maximum", scope)
        needs_approval = rule.approval_above is not None and amount > rule.approval_above
    if precondition is not None:
        refusal = precondition()
        if refusal:
            return decide(False, refusal, scope)
    if needs_approval:
        if approvals is None or approval_token is None:
            return decide(False, "approval-required", scope)
        problem = approvals.consume(approval_token, identity, tool, arguments, now)
        if problem:
            return decide(False, problem, scope)
    return decide(True, "allowed", scope)
