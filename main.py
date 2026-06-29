#!/usr/bin/env python3
"""
Growisto Timesheet EBR Skill — Python CLI
Uses Zoho custom MCP URL (no hardcoded API tokens).
First run opens browser for one-time Zoho login.
Each user logs in with their own Zoho account — project access is enforced by Zoho.
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple

from auth import get_access_token
from zoho_api import find_project_id, get_timelogs
from ebr import calculate, render_report

CONFIG_FILE = Path(__file__).parent / "config.json"


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        print("ERROR: config.json not found.")
        sys.exit(1)
    return json.loads(CONFIG_FILE.read_text())


def ask(prompt: str, default: str = "") -> str:
    val = input(f"{prompt} [{default}]: ").strip() if default else input(f"{prompt}: ").strip()
    return val or default


def parse_revenue(s: str) -> float:
    s = s.strip().lower().replace(",", "").replace("₹", "").replace("rs", "").replace("inr", "").strip()
    if s.endswith("lac") or s.endswith("l"):
        s = s.rstrip("lac").rstrip("l").strip()
        return float(s) * 100000
    if s.endswith("k"):
        return float(s[:-1]) * 1000
    return float(s)


def month_range(year: int, month: int) -> Tuple[str, str]:
    from calendar import monthrange
    _, last = monthrange(year, month)
    return f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last:02d}"


def parse_date_range(raw: str) -> Tuple[str, str]:
    if ":" in raw:
        parts = raw.split(":")
        return parts[0].strip(), parts[1].strip()
    parts = raw.split("-")
    if len(parts) == 2:
        return month_range(int(parts[0]), int(parts[1]))
    if len(parts) == 3:
        return raw, raw
    today = date.today()
    return month_range(today.year, today.month)


def parse_logs_from_mcp(result: dict) -> Tuple[List[dict], Optional[str]]:
    """
    Returns (logs, error_message).
    error_message is set if Zoho returned an access/permission error.
    """
    logs = []
    raw_texts = []

    content = result.get("content", [])
    for item in content:
        if item.get("type") == "text":
            text = item["text"]
            raw_texts.append(text)
            try:
                data = json.loads(text)

                # Check for Zoho error responses
                if isinstance(data, dict):
                    err_code = data.get("error_code") or data.get("errorCode") or ""
                    err_msg = data.get("message") or data.get("error") or ""
                    status = str(data.get("status", "")).lower()

                    if err_code in ("NO_ACCESS", "PERMISSION_DENIED", "INVALID_PROJECT", "PROJECT_NOT_FOUND"):
                        return [], f"Project not found or you don't have access to it in Zoho. ({err_code})"
                    if status == "failure" or (err_msg and not data.get("timelogs") and not data.get("logs")):
                        return [], f"Zoho returned an error: {err_msg or data}"

                if isinstance(data, list):
                    logs.extend(data)
                elif isinstance(data, dict):
                    if "logs" in data:
                        logs.extend(data["logs"])
                    elif "timelogs" in data:
                        tl = data["timelogs"]
                        if isinstance(tl, list):
                            logs.extend(tl)
                        elif isinstance(tl, dict) and "date" in tl:
                            for d_entry in tl["date"]:
                                log_date = d_entry.get("date", "")
                                for log in d_entry.get("tasklogs", []):
                                    log["date"] = log_date
                                    log["member"] = log.get("owner_name", "")
                                    logs.append(log)
                    elif "data" in data:
                        logs.extend(data["data"] if isinstance(data["data"], list) else [])

            except (json.JSONDecodeError, KeyError):
                pass

    return logs, None


def main():
    parser = argparse.ArgumentParser(description="Growisto Timesheet EBR Report")
    parser.add_argument("--project", help="Project name in Zoho")
    parser.add_argument("--month", help="Month (YYYY-MM) or date range (YYYY-MM-DD:YYYY-MM-DD)")
    parser.add_argument("--revenue", help="Monthly revenue e.g. 5.5lac, 550000, 7l")
    parser.add_argument("--bill", help="Bill filter: All / Billable / Non Billable", default=None)
    args = parser.parse_args()

    print("\n========================================")
    print("  Growisto Timesheet EBR Skill")
    print("========================================\n")

    config = load_config()
    mcp_url = config["mcp_url"]
    portal = config.get("portal", "growistoinc")
    today = date.today()

    # Collect inputs — use CLI args if provided, else ask interactively
    project    = args.project  or ask("Project name (must match Zoho exactly, e.g. Kama Ayurveda)")
    if not project.strip():
        print("ERROR: Project name is required.")
        sys.exit(1)
    month_raw  = args.month    or ask("Month or date range (YYYY-MM or YYYY-MM-DD:YYYY-MM-DD)", f"{today.year}-{today.month:02d}")
    rev_raw    = args.revenue  or ask("Monthly Revenue (e.g. 5.5 lac, 550000, 7l)")
    bill_filter= args.bill     or ask("Bill filter (All / Billable / Non Billable)", "All")

    try:
        revenue = parse_revenue(rev_raw)
    except ValueError:
        print(f"ERROR: Could not parse revenue '{rev_raw}'. Use formats like: 5.5lac, 550000, 7l")
        sys.exit(1)

    date_from, date_to = parse_date_range(month_raw)

    print(f"\nProject  : {project}")
    print(f"Period   : {date_from}  →  {date_to}")
    print(f"Revenue  : ₹{revenue:,.0f}")
    print(f"Filter   : {bill_filter}\n")

    # Auth — browser login on first run, silent refresh after that
    try:
        token = get_access_token(mcp_url, port=config.get("redirect_port", 8765))
    except Exception as e:
        print(f"Auth failed: {e}")
        sys.exit(1)

    # Resolve project name → project ID (config cache first, then Zoho REST API)
    project_id = config.get("project_ids", {}).get(project)

    if not project_id:
        print("Looking up project in Zoho...")
        try:
            project_id = find_project_id(portal, project, token)
        except Exception as e:
            print(f"\nERROR connecting to Zoho: {e}")
            sys.exit(1)

        if not project_id:
            print(f"\nERROR: Project '{project}' not found in Zoho.")
            sys.exit(1)

    # Fetch timelogs directly from Zoho Projects API
    print("Fetching timelogs from Zoho...")
    try:
        logs = get_timelogs(portal, project_id, date_from, date_to, token)
    except Exception as e:
        print(f"\nERROR fetching timelogs: {e}")
        sys.exit(1)

    if not logs:
        print(f"\nNo timelog entries found for '{project}' between {date_from} and {date_to}.")
        print("Possible reasons:")
        print("  • No hours were logged in this period")
        print("  • Project name doesn't match — check spelling in Zoho")
        print("  • You are not assigned to this project in Zoho")
        sys.exit(0)

    print(f"Found {len(logs)} log entries.\n")

    # Calculate and display
    data   = calculate(logs, revenue, bill_filter)
    report = render_report(data, project, date_from, date_to, bill_filter)
    print(report)

    # Offer to save
    save = ask("Save report to file? (y/n)", "n")
    if save.lower() == "y":
        fname = f"ebr_{project.lower().replace(' ', '_')}_{date_from[:7]}.txt"
        fpath = Path(__file__).parent / fname
        fpath.write_text(report)
        print(f"Saved: {fpath}")


if __name__ == "__main__":
    main()
