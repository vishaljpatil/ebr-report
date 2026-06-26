"""
EBR (Effective Billing Rate) calculator.
Input: list of timelog entries from Zoho MCP.
Output: formatted EBR report.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MemberStats:
    name: str
    total_mins: int = 0
    billable_mins: int = 0
    non_billable_mins: int = 0
    log_count: int = 0


def _fmt_hours(mins: int) -> str:
    return f"{mins // 60}h {mins % 60}m"


def _fmt_inr(amount: float) -> str:
    # Indian number format: 1,00,000
    s = f"{amount:.0f}"
    if len(s) <= 3:
        return f"₹{s}"
    last3 = s[-3:]
    rest = s[:-3]
    parts = []
    while len(rest) > 2:
        parts.append(rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.append(rest)
    return "₹" + ",".join(reversed(parts)) + "," + last3


def calculate(logs: list[dict], revenue: float, bill_filter: str = "All") -> dict:
    """
    logs: list of dicts with keys: date, member, hours, minutes, bill_status, task, tasklist
    revenue: monthly revenue in INR
    bill_filter: 'All', 'Billable', 'Non Billable'
    """
    filtered = []
    for log in logs:
        status = (log.get("bill_status") or "Non Billable").strip()
        if bill_filter != "All":
            if bill_filter.lower() == "billable" and "non" in status.lower():
                continue
            if bill_filter.lower() == "non billable" and "non" not in status.lower():
                continue
        filtered.append(log)

    members: dict[str, MemberStats] = {}
    total_mins = 0
    billable_mins = 0
    non_billable_mins = 0

    for log in filtered:
        name = log.get("member") or log.get("owner_name") or "Unknown"
        hrs = int(log.get("hours", 0))
        mins = int(log.get("minutes", 0))
        entry_mins = hrs * 60 + mins
        status = (log.get("bill_status") or "Non Billable").strip()
        is_billable = "non" not in status.lower()

        total_mins += entry_mins
        if is_billable:
            billable_mins += entry_mins
        else:
            non_billable_mins += entry_mins

        if name not in members:
            members[name] = MemberStats(name=name)
        m = members[name]
        m.total_mins += entry_mins
        m.log_count += 1
        if is_billable:
            m.billable_mins += entry_mins
        else:
            m.non_billable_mins += entry_mins

    total_hrs = total_mins / 60 if total_mins else 0
    ebr_rate = revenue / total_hrs if total_hrs else 0

    sorted_members = sorted(members.values(), key=lambda x: x.total_mins, reverse=True)

    return {
        "total_logs": len(filtered),
        "total_mins": total_mins,
        "total_hrs": total_hrs,
        "billable_mins": billable_mins,
        "non_billable_mins": non_billable_mins,
        "ebr_rate": ebr_rate,
        "revenue": revenue,
        "members": sorted_members,
        "logs": filtered,
    }


def render_report(result: dict, project: str, date_from: str, date_to: str, bill_filter: str) -> str:
    r = result
    rev = r["revenue"]
    ebr = r["ebr_rate"]
    lines = []

    lines.append("=" * 70)
    lines.append("  GROWISTO — PROJECT EBR REPORT")
    lines.append("=" * 70)
    lines.append(f"  Project      : {project}")
    lines.append(f"  Period       : {date_from}  to  {date_to}")
    lines.append(f"  Revenue      : {_fmt_inr(rev)}")
    lines.append(f"  Bill Filter  : {bill_filter}")
    lines.append("=" * 70)
    lines.append("")
    lines.append("SUMMARY")
    lines.append("-" * 40)
    lines.append(f"  Total Log Entries  : {r['total_logs']}")
    lines.append(f"  Total Hours        : {_fmt_hours(r['total_mins'])}")
    lines.append(f"  Billable Hours     : {_fmt_hours(r['billable_mins'])}")
    lines.append(f"  Non-Billable Hours : {_fmt_hours(r['non_billable_mins'])}")
    lines.append(f"  Total Members      : {len(r['members'])}")
    lines.append(f"  EBR Rate           : {_fmt_inr(ebr)}/hr")
    lines.append("")
    lines.append("EBR FORMULA")
    lines.append("-" * 40)
    lines.append(f"  EBR Rate = {_fmt_inr(rev)} ÷ {r['total_hrs']:.2f}h = {_fmt_inr(ebr)}/hr")
    lines.append(f"  Member Share = (Member Hours ÷ Total Hours) × {_fmt_inr(rev)}")
    lines.append("")
    lines.append("MEMBER WISE BREAKDOWN")
    lines.append("-" * 100)
    hdr = f"  {'#':<3} {'Member':<25} {'Total Hrs':<12} {'Billable':<12} {'Non-Bill':<12} {'Hour %':<8} {'Rev Share':>14} {'EBR Rate':>12}"
    lines.append(hdr)
    lines.append("  " + "-" * 97)

    for i, m in enumerate(r["members"], 1):
        pct = (m.total_mins / r["total_mins"] * 100) if r["total_mins"] else 0
        share = (m.total_mins / r["total_mins"] * rev) if r["total_mins"] else 0
        row = (
            f"  {i:<3} {m.name:<25} {_fmt_hours(m.total_mins):<12} "
            f"{_fmt_hours(m.billable_mins):<12} {_fmt_hours(m.non_billable_mins):<12} "
            f"{pct:<8.1f} {_fmt_inr(share):>14} {_fmt_inr(ebr)+'/hr':>12}"
        )
        lines.append(row)

    lines.append("")
    return "\n".join(lines)
