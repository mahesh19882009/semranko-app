import requests
import json
import time

class DataForSeoDashboardHelper:
    def __init__(self, username, password):
        self.auth = (username, password)
        self.headers = {"Content-Type": "application/json"}

    # =========================================================================
    # MODULE 1: RANK TRACKER DASHBOARD (Weekly Update)
    # =========================================================================
    def fetch_cheapest_dashboard_data(self, keywords, target_domain, location_code=2840):
        if isinstance(keywords, str):
            keywords = [keywords]

        serp_post_url = "https://dataforseo.com"
        serp_payload = []
        for kw in keywords:
            serp_payload.append({
                "keyword": kw,
                "location_code": location_code,
                "language_code": "en",
                "device": "desktop",
                "os": "windows"
            })
            
        post_res = requests.post(serp_post_url, json=serp_payload, auth=self.auth, headers=self.headers, timeout=30)
        task_ids = []
        try:
            post_response = post_res.json()
            tasks = post_response.get("tasks", []) or []
            for task in tasks:
                if task.get("id"):
                    task_ids.append(task["id"])
        except Exception:
            return []

        if not task_ids:
            return []

        final_table_rows = []
        for task_id in task_ids:
            get_url = f"https://dataforseo.com{task_id}"
            max_retries = 15
            task_processed = False
            get_response = {}

            for attempt in range(max_retries):
                try:
                    get_res = requests.get(get_url, auth=self.auth, headers=self.headers, timeout=20)
                    if get_res.status_code == 200:
                        get_response = get_res.json()
                        status = get_response.get("status_message", "")
                        if "Ok" in status:
                            task_processed = True
                            break
                except Exception:
                    pass
                time.sleep(10)

            if not task_processed:
                continue
            
            tasks_data = get_response.get("tasks", []) or []
            for task_data in tasks_data:
                current_keyword = task_data.get("data", {}).get("keyword")
                if not current_keyword:
                    continue
                    
                detected_position = "—"
                has_aio_badge = "No"
                keyword_difficulty = "—"
                cost_per_click = "—"
                competition_level = "—"
                search_intent = "—"
                backlinks_count = "—"
                referring_domains = "—"
                
                results_list = task_data.get("result", []) or []
                if isinstance(results_list, list) and len(results_list) > 0:
                    first_block = results_list[0] if isinstance(results_list, list) else {}
                    
                    keyword_properties = first_block.get("keyword_properties", {})
                    if not isinstance(keyword_properties, dict):
                        keyword_properties = {}
                    try:
                        keyword_difficulty = keyword_properties.get("keyword_difficulty", "—")
                        search_intent = keyword_properties.get("search_intent", "—")
                    except Exception:
                        keyword_difficulty = "—"
                        search_intent = "—"
                    
                    keyword_info = first_block.get("keyword_info", {})
                    if not isinstance(keyword_info, dict):
                        keyword_info = {}
                    try:
                        cost_per_click = keyword_info.get("cpc", "—")
                        competition_level = keyword_info.get("competition", "—")
                    except Exception:
                        cost_per_click = "—"
                        competition_level = "—"
                    
                    serp_items = first_block.get("items", []) or []
                    if not isinstance(serp_items, list):
                        serp_items = []
                    for item in serp_items:
                        if not item:
                            continue
                        try:
                            if item.get("type") == "organic" and item.get("url") and target_domain in item.get("url", ""):
                                detected_position = item.get("rank_absolute", "—")
                                backlink_info = item.get("backlinks_info", {})
                                if isinstance(backlink_info, dict):
                                    backlinks_count = backlink_info.get("backlinks", "—")
                                    referring_domains = backlink_info.get("referring_domains", "—")
                        except Exception:
                            pass
                    
                    try:
                        if item.get("type") == "ai_overview":
                            references = item.get("ai_overview_reference", []) or []
                            if isinstance(references, list):
                                for ref in references:
                                    if ref and ref.get("url") and target_domain in ref.get("url", ""):
                                        has_aio_badge = "AIO"
                    except Exception:
                        pass

                final_table_rows.append({
                    "Keyword": current_keyword,
                    "KD": keyword_difficulty,
                    "CPC": cost_per_click,
                    "Competition": competition_level,
                    "Backlinks": backlinks_count,
                    "Domains": referring_domains,
                    "Intent": search_intent,
                    "Position": detected_position,
                    "AI": has_aio_badge
                })

        return final_table_rows

    # =========================================================================
    # MODULE 2: KEYWORD RESEARCH (On-Demand Module)
    # =========================================================================
    def execute_keyword_research(self, seed_keyword, location_code=2840):
        """
        Deducts 1 platform credit from user. Returns 100+ related keyword ideas instantly.
        """
        url = "https://dataforseo.com"
        payload = [{
            "keyword": seed_keyword,
            "location_code": location_code,
            "limit": 100
        }]
        res = requests.post(url, json=payload, auth=self.auth, headers=self.headers)
        
        ideas = []
        try:
            data = res.json()
            items = data["tasks"][0]["result"][0]["items"]
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
    # MODULE 3: COMPETITOR SPY (On-Demand Module)
    # =========================================================================
    def execute_competitor_spy(self, competitor_domain, location_code=2840):
        """
        Deducts 20 platform credits from user. Returns everything a competitor ranks for instantly.
        """
        url = "https://dataforseo.com"
        payload = [{
            "target": competitor_domain,
            "location_code": location_code,
            "limit": 100
        }]
        res = requests.post(url, json=payload, auth=self.auth, headers=self.headers)
        
        rankings = []
        try:
            data = res.json()
            items = data["tasks"][0]["result"][0]["items"]
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
