"""Recognize a bounded set of explicit refund requests, before authorizing an effect."""

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal

ORDER = r"(?P<order>[a-z][0-9]{4})"
AMOUNT = r"(?P<amount>[0-9]{1,6}(?:[.,][0-9]{1,2})?) ?\$"
ORDER_2 = ORDER.replace("<order>", "<order_2>")
AMOUNT_2 = AMOUNT.replace("<amount>", "<amount_2>")
REQUEST_END = r" ?[.!?]?"

DIRECT = (
    rf"je (?:veux|souhaite) (?:être remboursée?|un remboursement) de {AMOUNT} (?:pour|sur) (?:la |ma )?commande {ORDER}",
    rf"remboursez(?:-moi)? (?:seulement )?{AMOUNT} (?:pour|sur) "
    rf"(?:(?:ma |la )?commande )?{ORDER}(?:, ?s'il vous plaît)?",
    rf"pouvez-vous rembourser (?:ma |la )?commande {ORDER} ?\({AMOUNT}\)",
    rf"je demande un remboursement partiel de {AMOUNT} pour la commande {ORDER}",
    rf"sur la commande {ORDER}, ?remboursez-moi {AMOUNT}, ?pas plus",
    rf"remboursez {AMOUNT} sur ma commande {ORDER} et dites-moi quand je recevrai l'argent",
    rf"je veux {AMOUNT} de remboursement pour {ORDER} ?; ?dans combien de temps vais-je le recevoir",
    rf"faites le remboursement de {AMOUNT} pour la commande {ORDER}, ?et précisez le délai de versement",
    rf"remboursez {AMOUNT} sur ma commande {ORDER} et {AMOUNT_2} sur ma commande {ORDER_2}",
    rf"je veux deux remboursements ?: {AMOUNT} pour {ORDER} et {AMOUNT_2} pour {ORDER_2}",
    rf"faites {AMOUNT} de remboursement sur {ORDER}, ?puis {AMOUNT_2} sur {ORDER_2}",
)
ON_DELIVERY = (
    rf"vérifiez (?:ma |la )?commande {ORDER} ?: si elle est livrée, ?remboursez(?:-moi)? {AMOUNT}",
    rf"si (?:ma |la )?commande {ORDER} (?:est|a été) livrée, ?"
    rf"(?:je (?:veux|souhaite) un remboursement de|remboursez(?:-moi)?) {AMOUNT}",
    rf"regardez d'abord le statut de {ORDER} ?; ?remboursez(?:-moi)? {AMOUNT} seulement si elle est livrée",
)
REQUEST_PATTERNS = tuple(
    (re.compile(pattern + REQUEST_END), delivery_required)
    for patterns, delivery_required in ((DIRECT, False), (ON_DELIVERY, True))
    for pattern in patterns
)


CONDITION = re.compile(r"\b(?:si\b|à condition qu(?:e\b|')|sous réserve (?:de\b|qu(?:e\b|')))")
REFUND_REQUEST = re.compile(
    r"(?:^|[,;:]\s*)(?:remboursez(?:-moi)?|(?:pouvez|pourriez)-vous (?:me )?rembourser|"
    r"est-il possible de (?:me )?rembourser|je (?:veux|souhaite|demande) (?:un remboursement|être remboursée?)|"
    rf"j'aimerais (?:un remboursement|recevoir {AMOUNT}))(?=\W|$)"
)
ORDER_REFERENCE = re.compile(rf"\b{ORDER}\b")


@dataclass(frozen=True)
class RefundIntent:
    amount: Decimal
    delivery_required: bool


def _normalize(request: str | None) -> str:
    normalized = unicodedata.normalize("NFC", request or "").replace("’", "'").casefold()
    return " ".join(normalized.split())


def explicit_conditional_refund(request: str) -> bool:
    """Recognize a conditional request about a single order for manual review."""
    text = _normalize(request)
    return (len(set(ORDER_REFERENCE.findall(text))) == 1
            and CONDITION.search(text) is not None and REFUND_REQUEST.search(text) is not None)


def refund_intents(request: str | None) -> dict[str, RefundIntent]:
    """Accept a full, unambiguous request that the write guard supports."""
    text = _normalize(request)
    for pattern, delivery_required in REQUEST_PATTERNS:
        matched = pattern.fullmatch(text)
        if matched is None:
            continue
        values = matched.groupdict()
        orders = [(values["order"], values["amount"])]
        if "order_2" in values:
            orders.append((values["order_2"], values["amount_2"]))
        if len({order for order, _ in orders}) != len(orders):
            return {}
        return {order.upper(): RefundIntent(Decimal(amount.replace(",", ".")), delivery_required)
                for order, amount in orders}
    return {}
