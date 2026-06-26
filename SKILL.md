# Growisto Timesheet EBR Skill (Python)

## What it does
Fetches timesheet data from Zoho Projects via a custom Zoho MCP, calculates EBR (Effective Billing Rate), and prints a formatted member-wise report.

**No Zoho API tokens needed in code** — auth is handled via one-time browser OAuth on first run.

---

## Setup (one time per machine)

### 1. Clone the repo
```bash
git clone <repo-url>
cd timesheet-python
```

### 2. Verify Python version
```bash
python3 --version   # needs 3.10+
```

### 3. Check config.json
```json
{
  "mcp_url": "https://timesheet-logs-mcp-60075680902.zohomcp.in/mcp/.../message",
  "portal": "growistoinc",
  "redirect_port": 8765
}
```
No credentials here — just the MCP URL and portal name.

### 4. Run
```bash
python3 main.py
```

On first run it opens your browser → log in with your Zoho account → tokens saved locally in `tokens.json` (gitignored).

---

## Usage

```
$ python3 main.py

========================================
  Growisto Timesheet EBR Skill
========================================

Project name [Kama Ayurveda]: 
Month or date range (YYYY-MM or YYYY-MM-DD:YYYY-MM-DD) [2026-06]:
Monthly Revenue (e.g. 5.5 lac, 550000, 7l) [550000]: 5.5 lac
Bill filter (All / Billable / Non Billable) [All]: 
```

Then it prints the full EBR report.

---

## EBR Formula

```
EBR Rate (₹/hr)  = Monthly Revenue ÷ Total Hours
Member Rev Share = (Member Hours ÷ Total Hours) × Monthly Revenue
```

---

## Files

| File | Purpose |
|------|---------|
| `main.py` | CLI entry point — collects inputs, calls MCP, prints report |
| `auth.py` | OAuth2 PKCE flow with dynamic client registration |
| `mcp_client.py` | MCP JSON-RPC HTTP client |
| `ebr.py` | EBR calculation + report formatting |
| `config.json` | MCP URL + portal (no secrets) |
| `tokens.json` | Auto-created after first auth — **gitignored** |

---

## Security
- `tokens.json` is gitignored — never committed
- `config.json` contains only the public MCP URL — safe to commit
- All Zoho API calls are READ-ONLY (scope: ZohoProjects.timesheets.READ)
