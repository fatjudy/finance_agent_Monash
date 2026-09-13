from __future__ import annotations
import argparse
import uuid
from decimal import Decimal
from datetime import date
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from src.models import ProcessingRequest
from src.agent.graph import build_graph

DB_PATH = Path(__file__).parent.parent / "runs" / "checkpoints.sqlite"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _print_result(state: dict) -> None:
    result = state.get("result")
    if not result:
        return
    print("recommendation:", result.recommendation.next_action.value,
          f"({result.recommendation.confidence.value})")
    print("rationale:", result.recommendation.rationale)
    print("calculations:", {k: str(v) for k, v in result.calculations.items()})
    print("policy_findings:", result.policy_findings)
    print("actions_taken:", result.actions_taken)


def cmd_start(args: argparse.Namespace) -> None:
    thread_id = args.thread or f"{args.case}-{uuid.uuid4().hex[:8]}"
    req = ProcessingRequest(
        case_id=args.case, invoice_ref=args.invoice, vendor=args.vendor,
        amount=Decimal(args.amount), currency=args.currency,
        invoice_date=date.fromisoformat(args.date), po_number=args.po,
    )
    with SqliteSaver.from_conn_string(str(DB_PATH)) as cp:
        graph = build_graph(cp)
        out = graph.invoke({"request": req}, _config(thread_id))
    print("run_id:", thread_id)
    if "__interrupt__" in out:
        print("status: AWAITING_APPROVAL")
        print("approval_request:", out["__interrupt__"][0].value)
        print(f"\nTo resolve:  python -m src.cli approve --thread {thread_id}   (add --reject to reject)")
    else:
        print("status:", out.get("status"))
        _print_result(out)


def cmd_get(args: argparse.Namespace) -> None:
    with SqliteSaver.from_conn_string(str(DB_PATH)) as cp:
        graph = build_graph(cp)
        snap = graph.get_state(_config(args.thread))
    if not snap.values:
        print("run_id:", args.thread, "-> not found")
        return
    state = snap.values
    pending = snap.next
    print("run_id:", args.thread)
    print("status:", "AWAITING_APPROVAL" if pending else state.get("status", "unknown"))
    if pending:
        print("paused_at:", pending)
    print("steps:", state.get("steps"))
    print("audit:")
    for a in state.get("audit", []):
        print("  ", a)
    _print_result(state)


def cmd_approve(args: argparse.Namespace) -> None:
    approved = not args.reject
    with SqliteSaver.from_conn_string(str(DB_PATH)) as cp:
        graph = build_graph(cp)
        final = graph.invoke(Command(resume={"approved": approved}), _config(args.thread))
    print("run_id:", args.thread, "| resumed with approved =", approved)
    print("status:", final.get("status"))
    if final.get("decision"):
        print("decision:", final["decision"].status, "| action:", final["decision"].action.value)
    _print_result(final)


def cmd_eval(args: argparse.Namespace) -> None:
    from src.eval import evaluate
    results = evaluate()
    for name, ok, detail in results:
        print(("PASS" if ok else "FAIL"), "|", name, "|", detail)
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} cases passed")


def main() -> None:
    parser = argparse.ArgumentParser(prog="finance-agent")
    sub = parser.add_subparsers(dest="command", required=True)

    s = sub.add_parser("start", help="Start a run from a financial case")
    s.add_argument("--case", required=True)
    s.add_argument("--invoice", required=True)
    s.add_argument("--vendor", required=True)
    s.add_argument("--amount", required=True)
    s.add_argument("--currency", default="AUD")
    s.add_argument("--date", required=True, help="invoice date, YYYY-MM-DD")
    s.add_argument("--po", default=None)
    s.add_argument("--thread", default=None, help="optional explicit run id")
    s.set_defaults(func=cmd_start)

    g = sub.add_parser("get", help="Get a run's status, audit, and result")
    g.add_argument("--thread", required=True)
    g.set_defaults(func=cmd_get)

    a = sub.add_parser("approve", help="Approve (or --reject) a pending run and resume it")
    a.add_argument("--thread", required=True)
    a.add_argument("--reject", action="store_true")
    a.set_defaults(func=cmd_approve)

    e = sub.add_parser("eval", help="Run the FIN evaluation cases and report pass/fail")
    e.set_defaults(func=cmd_eval)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
