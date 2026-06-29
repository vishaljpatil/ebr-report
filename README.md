# Growisto Timesheet EBR Skill

A Claude Code skill that generates Effort-to-Billing Ratio (EBR) reports by pulling live timesheet data from Zoho Projects.

---

## Install

```bash
git clone https://github.com/vishaljpatil/ebr-report.git ~/.claude/skills/ebr-skill
```

Requires Python 3.10+. No pip install needed.

---

## Use

Open Claude Code and type:

```
/ebr
```

Claude will ask for the project name, month, and revenue — then print the EBR report.

**First run only:** a browser opens for Zoho login with your Growisto account. Never asked again after that.

---

## Update

```bash
cd ~/.claude/skills/ebr-skill && git pull
```

---

## EBR Formula

```
EBR Rate (₹/hr)  = Monthly Revenue ÷ Total Hours
Member Rev Share = (Member Hours ÷ Total Hours) × Monthly Revenue
```
