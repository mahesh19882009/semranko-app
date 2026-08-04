import requests
import json
import time
import logging
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class DataForSeoDashboardHelper:
    def __init__(self, username=None, password=None):
        self.auth = (
            username or settings.effective_serp_login,
            password or settings.effective_serp_key,
        )
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        # FIX 1: THE ACCURATE GLOBAL ROOT REMOVED. ENDPOINTS LINKED FULLY BELOW.

    # =========================================================================
    # MODULE 1: RANK TRACKER DASHBOARD (ASYNC PINGBACK)
    # =========================================================================
    def fetch_cheapest_dashboard_data(self, keywords, target_domain, location_code=2840, pingback_url=None, user_id=None, project_id=None):
        if isinstance(keywords, str):
            keywords = [keywords]

        # FIX 2: STRICT FULL UNIFIED SPECIFICATION ENDPOINT FOR SERP TRACKING
        target_endpoint_url = "https://dataforseo.com"

        serp_payload = []
        for kw in keywords:
            entry = {
                "keyword": kw,
                "location_code": location_code,
                "language_code": "en",
                "device": "desktop",
                "os": "windows",
            }
            if pingback_url:
                entry["pingback_url"] = f"{pingback_url}?user_id={user_id}&project_id={project_id}&keyword={kw}"
            serp_payload.append(entry)

        # Wrap in the strict JSON envelope wrapper array expected by DataForSEO's gateway
        master_envelope = serp_payload

        masked_auth = (
            (self.auth[0][:4] + "****" if self.auth[0] else "None"),
            (self.auth[1][:4] + "****" if self.auth[1] else "None"),
        )

        print("[DATAFORSEO DEBUG] ========== OUTGOING PAYLOAD ==========")
        print("[DATAFORSEO DEBUG] URL:", target_endpoint_url)
        print("[DATAFORSEO DEBUG] Headers:", self.headers)
        print("[DATAFORSEO DEBUG] Auth:", masked_auth)
        print("[DATAFORSEO DEBUG] Payload:", json.dumps(master_envelope, indent=2))
        print("[DATAFORSEO DEBUG] ===========================================")

        task_ids = []
        try:
            # Pass data explicitly dumped as clean JSON layout data bytes stream
            post_res = requests.post(
                target_endpoint_url,
                data=json.dumps(master_envelope),
                auth=self.auth,
                headers=self.headers,
                timeout=30,
            )
            print("[DATAFORSEO DEBUG] HTTP Status Code:", post_res.status_code)
            print("[DATAFORSEO DEBUG] Raw Text Response:", post_res.text)
        except Exception as e:
            print("[DATAFORSEO DEBUG] Network handshake failed entirely:", str(e))
            return []

        if post_res.status_code != 200:
            print("[DATAFORSEO DEBUG] Non-200 response received, returning empty task_ids")
            return []
            
        try:
            post_response = post_res.json()
            tasks = post_response.get("tasks", []) or []
            for task in tasks:
                if task and task.get("id"):
                    task_ids.append(task["id"])
            print("[DATAFORSEO DEBUG] Extracted task_ids:", task_ids)
        except Exception as json_err:
            print("[DATAFORSEO DEBUG] Failed to parse JSON response body payload:", str(json_err))
            return []

        return task_ids

    # =========================================================================
    # MODULE 2: KEYWORD RESEARCH (Labs Bulk Database Lookups)
    # =========================================================================
    def execute_keyword_research(self, seed_keyword, location_code=2840):
        # FIX 3: STRICT FULL PATH FOR DATA_LABS KEYWORD SUGGESTIONS
        url = "https://dataforseo.com"
        payload = [{
            "keyword": seed_keyword,
            "location_code": location_code,
            "limit": 100
        }]
        master_envelope = payload
        ideas = []
        try:
            res = requests.post(url, data=json.dumps(master_envelope), auth=self.auth, headers=self.headers, timeout=30)
            if res.status_code == 200:
                data = res.json()
                tasks = data.get("tasks", []) or []
                if tasks:
                    first_task = tasks[0] if isinstance(tasks, list) else tasks
                    result_list = first_task.get("result", []) or []
                    if result_list:
                        items = result_list[0].get("items", []) if isinstance(result_list, list) and len(result_list) > 0 else result_list.get("items", []) or []
                        for item in items:
                            ideas.append({
                                "Keyword": item.get("keyword"),
                                "Search Volume": item.get("keyword_info", {}).get("search_volume", "—"),
                                "CPC": item.get("keyword_info", {}).get("cpc", "—"),
                                "KD": item.get("keyword_properties", {}).get("keyword_difficulty", "—"),
                                "Intent": item.get("keyword_properties", {}).get("search_intent", "—")
                            })
        except Exception:
            pass
        return ideas

    # =========================================================================
    # MODULE 3: COMPETITOR SPY (Labs Bulk Database Lookups)
    # =========================================================================
    def execute_competitor_spy(self, competitor_domain, location_code=2840):
        # FIX 4: STRICT FULL PATH FOR DATA_LABS RANKED COMPETITORS LOOKUPS
        url = "https://dataforseo.com"
        payload = [{
            "target": competitor_domain,
            "location_code": location_code,
            "limit": 100
        }]
        master_envelope = payload
        rankings = []
        try:
            res = requests.post(url, data=json.dumps(master_envelope), auth=self.auth, headers=self.headers, timeout=30)
            if res.status_code == 200:
                data = res.json()
                tasks = data.get("tasks", []) or []
                if tasks:
                    first_task = tasks[0] if isinstance(tasks, list) else tasks
                    result_list = first_task.get("result", []) or []
                    if result_list:
                        items = result_list[0].get("items", []) if isinstance(result_list, list) and len(result_list) > 0 else result_list.get("items", []) or []
                        for item in items:
                            rankings.append({
                                "Keyword": item.get("keyword_data", {}).get("keyword"),
                                "Competitor Position": item.get("ranked_serp_element", {}).get("serp_item", {}).get("rank_absolute", "—"),
                                "Search Volume": item.get("keyword_data", {}).get("keyword_info", {}).get("search_volume", "—"),
                                "KD": item.get("keyword_data", {}).get("keyword_properties", {}).get("keyword_difficulty", "—"),
                                "Competitor URL": item.get("ranked_serp_element", {}).get("serp_item", {}).get("url", "—")
                            })
        except Exception:
            pass
        return rankings
