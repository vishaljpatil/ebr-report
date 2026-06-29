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

### 2. Pull latest cache before running
Always run this first to make sure the project list is up to date:

```bash
cd ~/.claude/skills/ebr-skill && git pull
```

### 3. Collect inputs from the user
Ask the user for:
- **Project name** — before running the script, check `config.json` for an exact or close match. If the user's input does not exactly match a key in `project_ids`, show them the closest matches and ask them to confirm the correct one. Do NOT silently guess.
- **Month** — `YYYY-MM` or date range `YYYY-MM-DD:YYYY-MM-DD` (default: current month)
- **Monthly Revenue** — accepts `7l`, `5.5lac`, `550000`
- **Bill filter** — `All`, `Billable`, or `Non Billable` (default: All)

To find close matches in the cache:
```bash
python3 -c "
import json
config = json.load(open('/root/.claude/skills/ebr-skill/config.json'))
q = 'USER_INPUT'.lower()
matches = [k for k in config['project_ids'] if q in k.lower()]
print('\n'.join(matches[:10]))
"
```

Show the matches to the user and wait for confirmation before proceeding.

### 4. Run the script
Once the exact project name is confirmed:

```bash
cd ~/.claude/skills/ebr-skill && python3 main.py
```

Pass the confirmed project name when prompted.

### 5. If "No entries returned"
This means no hours were logged for that project in the selected period. Tell the user:
> "No timelog entries found for '[project]' in [month]. Either no hours were logged this period, or the project name doesn't exactly match Zoho. Please verify in Zoho Projects."

Do NOT edit `config.json` locally. If a project is genuinely missing from the cache, ask the user to raise it with the Claude Code admin team to update the central repo.

### 6. First-run auth
If the script says "Opening browser for Zoho login", tell the user:
> "Please log in with your Growisto Zoho account. This is a one-time step — you won't be asked again."

After login, tokens are saved locally and all future runs are completely silent.

### 7. Done
The script prints the full EBR report. If the user wants to save it, the script will ask — answer `y` or `n`.
