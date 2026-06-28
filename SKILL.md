# Growisto Timesheet EBR Skill

Generate an Effort-to-Billing Ratio (EBR) report for any Growisto client project by pulling live timesheet data from Zoho Projects.

## Trigger

`/ebr`

## What this skill does

When invoked, this skill:
1. Asks the user for project name, month, revenue, and bill filter
2. Pulls timelog data from Zoho Projects via the Growisto MCP integration
3. Calculates EBR (hours per member, revenue share, ₹/hr rate)
4. Prints a formatted report and offers to save it as a file

## One-time setup (per machine)

```bash
# 1. Clone into your Claude skills folder
git clone https://github.com/vishaljpatil/ebr-report.git ~/.claude/skills/ebr-skill

# 2. Verify Python 3.10+
python3 --version
```

On first run, a browser window opens for Zoho login. After that it runs silently — no repeated logins.

---

## Instructions for Claude

When the user runs `/ebr`, execute the following steps exactly:

### Step 1 — Find the skill directory

The skill lives at `~/.claude/skills/ebr-skill/`. Confirm it exists:

```bash
ls ~/.claude/skills/ebr-skill/main.py
```

If not found, tell the user to run the one-time setup above and stop.

### Step 2 — Run the skill

```bash
cd ~/.claude/skills/ebr-skill && python3 main.py
```

The script is fully interactive — it will prompt for:
- **Project name** — must match Zoho exactly (e.g. `Kama Ayurveda`)
- **Month** — format `YYYY-MM` or date range `YYYY-MM-DD:YYYY-MM-DD` (default: current month)
- **Monthly Revenue** — accepts `7l`, `5.5lac`, `550000`, `7 lakh` etc.
- **Bill filter** — `All`, `Billable`, or `Non Billable` (default: All)

### Step 3 — First run only (auth)

If the script opens a browser for Zoho login, tell the user:
> "Please log in with your Growisto Zoho account. This is a one-time step — you won't be asked again."

After login the tokens are saved locally and all future runs are silent.

### Step 4 — Report output

The script prints the full EBR report to the terminal. If the user wants to save it, the script will prompt for that too.

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
| `main.py` | CLI entry point |
| `auth.py` | OAuth2 PKCE — one-time browser login, silent refresh after |
| `mcp_client.py` | Zoho MCP JSON-RPC client |
| `zoho_api.py` | Zoho Projects REST API (timelogs) |
| `ebr.py` | EBR calculation + report formatting |
| `config.json` | MCP URL + portal + project ID cache (no secrets) |
| `tokens.json` | Auto-created after first auth — **gitignored, never committed** |

---

## Adding a new project

If a project isn't found, ask the Claude Code team to update the skill repo — they can look up the project ID and add it to `config.json` in one step.

---

## Security

- `tokens.json` is gitignored — never committed
- `config.json` contains only the public MCP URL and project IDs — safe to commit
- All Zoho API calls are **READ-ONLY**
