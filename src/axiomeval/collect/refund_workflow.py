"""Execute an explicit delivery-conditioned refund through the authorized tools."""

import json

from axiomeval.collect.agent import call_tool, record_answer
from axiomeval.collect.oracle import Task
from axiomeval.collect.refund_request import explicit_conditional_refund, refund_intents
from axiomeval.collect.secure_tools import SecureToolbox
from axiomeval.collect.trace import TraceRecorder


def run_conditional_refund(task: Task, toolbox: SecureToolbox, recorder: TraceRecorder,
                           output_guard=None, *, route_reviews: bool = False) -> str | None:
    """Return an answer for a supported request or let the agent handle the request."""
    intents = refund_intents(task.question)
    if not intents and route_reviews and explicit_conditional_refund(task.question):
        recorder.add("input", task_id=task.id, question=task.question, route="refund-review")
        status, *_ = call_tool(toolbox, recorder, "escalate_to_human",
                               {"reason": "Vérification d’une demande de remboursement conditionnel."}, output_guard)
        if status == "executed":
            answer = "Votre demande a été transmise à un agent. Aucun remboursement n’a été effectué."
        else:
            answer = "Je ne peux pas transmettre cette demande. Aucun remboursement n’a été effectué."
        return record_answer(answer, recorder, output_guard)
    if len(intents) != 1:
        return None
    order_id, intent = next(iter(intents.items()))
    if not intent.delivery_required:
        return None

    recorder.add("input", task_id=task.id, question=task.question, route="conditional-refund")
    toolbox.begin_step()
    lookup = call_tool(toolbox, recorder, "lookup_order_status", {"order_id": order_id}, output_guard)
    status = json.loads(lookup[1]).get("statut") if lookup[0] == "executed" else None
    if not status:
        answer = "Je ne peux pas vérifier cette commande. Aucun remboursement n’a été effectué."
    elif status != "livrée":
        answer = "La commande n’est pas marquée livrée. Aucun remboursement n’a été effectué."
    else:
        toolbox.begin_step()
        refund = call_tool(toolbox, recorder, "refund_order",
                           {"order_id": order_id, "amount": float(intent.amount)}, output_guard)
        if refund[0] == "executed" and json.loads(refund[1]).get("remboursement") == "effectué":
            answer = f"La commande est livrée et le remboursement de {intent.amount:.2f} $ a été effectué."
        elif len(refund) == 3 and refund[2].reason == "approval-required":
            answer = "Une approbation humaine est nécessaire. Aucun remboursement n’a été effectué."
        else:
            answer = "Le remboursement n’a pas été effectué."
    return record_answer(answer, recorder, output_guard)
