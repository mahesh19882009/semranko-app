import requests
import json
import time

class DataForSeoDashboardHelper:
    BASE_URL = "https://dataforseo.com"
    
    def __init__(self, username, password):
        self.auth = (username, password)

    def fetch_cheapest_dashboard_data(self, keywords, target_domain, location_code=2840):
        if isinstance(keywords, str):
            keywords = [keywords]

        # -------------------------------------------------------------
        # LAYER A: Fetch Macro Metrics (KD, CPC, Intent, etc.) in Bulk
        # -------------------------------------------------------------
        labs_url = f"{self.BASE_URL}/dataforseo_labs/google/keyword_overview/live"
        labs_payload = [{
            "keywords": keywords,
            "location_code": location_code
        }]
        
        labs_res = requests.post(labs_url, json=labs_payload, auth=self.auth)
        
        if "application/json" not in labs_res.headers.get("Content-Type", ""):
            print(f"\n❌ Error from Labs API: {labs_res.text}\n")
            return []

        labs_response = labs_res.json()
        
        metrics_map = {}
        if "tasks" in labs_response and labs_response["tasks"]:
            for task in labs_response["tasks"]:
                items = task.get("result", {}).get("items", []) if task.get("result") else []
                for item in items:
                    kw = item.get("keyword")
                    if kw:
                        metrics_map[kw] = {
                            "kd": item.get("keyword_properties", {}).get("keyword_difficulty", "—"),
                            "cpc": item.get("keyword_info", {}).get("cpc", "—"),
                            "competition": item.get("keyword_info", {}).get("competition", "—"),
                            "intent": item.get("keyword_properties", {}).get("search_intent", "—"),
                            "backlinks": item.get("avg_backlinks_info", {}).get("backlinks", "—"),
                            "domains": item.get("avg_backlinks_info", {}).get("referring_domains", "—"),
                        }

        # -------------------------------------------------------------
        # LAYER B: Fetch Positions & AI Rankings via the Cheap Queue
        # -------------------------------------------------------------
        serp_post_url = f"{self.BASE_URL}/serp/google/organic/task_post"
        serp_payload = []
        for kw in keywords:
            serp_payload.append({
                "keyword": kw,
                "location_code": location_code,
                "depth": 100
            })
            
        post_res = requests.post(serp_post_url, json=serp_payload, auth=self.auth)
        
        if "application/json" not in post_res.headers.get("Content-Type", ""):
            print(f"\n❌ Error posting to SERP Queue API: {post_res.text}\n")
            return []

        post_response = post_res.json()
        
        task_ids = []
        if "tasks" in post_response and post_response["tasks"]:
            for task in post_response["tasks"]:
                if task.get("id"):
                    task_ids.append(task["id"])

        if not task_ids:
            print(f"⚠️ No tasks were successfully queued.")
            return []

        # -------------------------------------------------------------
        # LAYER C: Retrieve Queue Results with Smart Retries & Merge
        # -------------------------------------------------------------
        final_table_rows = []
        
        for task_id in task_ids:
            get_url = f"{self.BASE_URL}/serp/google/organic/task_get/advanced/{task_id}"
            
            # Smart Retry Loop: Try up to 6 times (checking every 5 seconds)
            max_retries = 6
            task_processed = False
            get_response = {}

            for attempt in range(max_retries):
                print(f"Checking task status (Attempt {attempt + 1}/{max_retries})...")
                get_res = requests.get(get_url, auth=self.auth)
                
                if "application/json" in get_res.headers.get("Content-Type", ""):
                    get_response = get_res.json()
                    # Check if DataForSEO status changed from "Queued" to finished
                    status = get_response.get("status_message", "")
                    if "Ok" in status:
                        task_processed = True
                        break
                
                # If it's still processing, pause for 5 seconds before checking again
                time.sleep(5)

            if not task_processed:
                print(f"⚠️ Task {task_id} took too long to process. Skipping.")
                continue
            
            if "tasks" in get_response and get_response["tasks"]:
                for task_data in get_response["tasks"]:
                    current_keyword = task_data.get("data", {}).get("keyword")
                    if not current_keyword:
                        continue
                        
                    detected_position = "—"
                    has_aio_badge = "No"
                    
                    results_block = task_data.get("result", [])
                    # Safely handle if result block is a list or dictionary
                    if isinstance(results_block, list) and len(results_block) > 0:
                        serp_items = results_block[0].get("items", [])
                    elif isinstance(results_block, dict):
                        serp_items = results_block.get("items", [])
                    else:
                        serp_items = []
                    
                    for item in serp_items:
                        if item.get("type") == "organic" and item.get("url") and target_domain in item.get("url", ""):
                            detected_position = item.get("rank_absolute", "—")
                        
                        if item.get("type") == "ai_overview":
                            references = item.get("ai_overview_reference", [])
                            for ref in references:
                                if ref.get("url") and target_domain in ref.get("url", ""):
                                    has_aio_badge = "AIO"

                    kw_metrics = metrics_map.get(current_keyword, {
                        "kd": "—", "cpc": "—", "competition": "—", "intent": "—", "backlinks": "—", "domains": "—"
                    })

                    final_table_rows.append({
                        "Keyword": current_keyword,
                        "KD": kw_metrics["kd"],
                        "CPC": kw_metrics["cpc"],
                        "Competition": kw_metrics["competition"],
                        "Backlinks": kw_metrics["backlinks"],
                        "Domains": kw_metrics["domains"],
                        "Intent": kw_metrics["intent"],
                        "Position": detected_position,
                        "AI": has_aio_badge
                    })

        return final_table_rows
