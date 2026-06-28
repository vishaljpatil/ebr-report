"""
Zoho Projects API client — uses the OAuth token from auth.py.
READ-ONLY: GET requests only.
"""

import json
import urllib.parse
import urllib.request
import urllib.error

API_BASE = "https://projectsapi.zoho.in/restapi"


def _get(endpoint: str, params: dict, token: str) -> dict:
    url = f"{API_BASE}/{endpoint.lstrip('/')}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url, headers={
        "Authorization": f"Zoho-oauthtoken {token}",
    })
    try:
        with urllib.request.urlopen(req) as r:
            if r.status == 204:
                return {}
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"Zoho API {e.code} for {url}: {body}")


def get_projects(portal: str, token: str) -> list[dict]:
    projects, index = [], 1
    while True:
        data = _get(f"portal/{portal}/projects/", {"index": index, "range": 100}, token)
        page = data.get("projects", [])
        if not page:
            break
        projects.extend(page)
        index += len(page)
        if len(page) < 100:
            break
    return projects


def find_project_id(portal: str, project_name: str, token: str) -> str | None:
    projects = get_projects(portal, token)
    name_lower = project_name.strip().lower()
    for p in projects:
        if p.get("name", "").strip().lower() == name_lower:
            return str(p.get("id_string") or p.get("id"))
    # Partial match fallback
    for p in projects:
        if name_lower in p.get("name", "").strip().lower():
            return str(p.get("id_string") or p.get("id"))
    return None


def get_timelogs(portal: str, project_id: str, date_from: str, date_to: str, token: str) -> list[dict]:
    from datetime import datetime

    def fmt(d: str) -> str:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%m-%d-%Y")

    custom_date = json.dumps({"start_date": fmt(date_from), "end_date": fmt(date_to)})
    logs, index = [], 0

    while True:
        data = _get(f"portal/{portal}/projects/{project_id}/logs/", {
            "users_list":     "all",
            "view_type":      "custom_date",
            "date":           fmt(date_from),
            "custom_date":    custom_date,
            "bill_status":    "All",
            "component_type": "task",
            "index":          index,
            "range":          200,
        }, token)

        dates = data.get("timelogs", {}).get("date", [])
        if not dates:
            break

        page = []
        for d_entry in dates:
            log_date = d_entry.get("date", "")
            for log in d_entry.get("tasklogs", []):
                log["log_date"] = log_date
                log["member"]   = log.get("owner_name", "")
                page.append(log)

        logs.extend(page)
        index += len(page)
        if len(page) < 200:
            break

    return logs
