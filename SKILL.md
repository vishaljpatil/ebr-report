Generate a Growisto Timesheet EBR (Effort-to-Billing Ratio) report for any client project. Pulls live timesheet data from Zoho Projects and calculates revenue share and ₹/hr rate per team member.

## When to use
When the user wants an EBR report — they may say "run EBR", "timesheet report", "effort billing report", or just "/ebr".

## Instructions for Claude

### 1. Locate the skill directory
The skill script lives at `~/.claude/skills/ebr-skill/main.py`. Check it exists:

```bash
ls ~/.claude/skills/ebr-skill/main.py
```

If missing, tell the user:
> "EBR skill not installed. Run this once to install it:"
> ```bash
> git clone https://github.com/vishaljpatil/ebr-report.git ~/.claude/skills/ebr-skill
> ```
> Then try `/ebr` again.

### 2. Run the skill
```bash
cd ~/.claude/skills/ebr-skill && python3 main.py
```

The script is interactive — it prompts for:
- **Project name** — must match Zoho exactly (e.g. `Kama Ayurveda`)
- **Month** — `YYYY-MM` or `YYYY-MM-DD:YYYY-MM-DD` (default: current month)
- **Monthly Revenue** — accepts `7l`, `5.5lac`, `550000`
- **Bill filter** — `All`, `Billable`, or `Non Billable` (default: All)

### 3. First-run auth
If the script says "Opening browser for Zoho login", tell the user:
> "Please log in with your Growisto Zoho account. This is a one-time step."

After login, tokens are saved locally and all future runs are completely silent.

### 4. Done
The script prints the full EBR report. If the user wants to save it, the script will ask — answer `y` or `n`.
