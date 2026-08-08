import logging
import time

import requests

logger = logging.getLogger(__name__)


class DataForSeoDashboardHelper:
    BASE_URL = "https://api.dataforseo.com/v3"

    def __init__(self, username, password):
        self.auth = (username, password)

    def fetch_cheapest_dashboard_data(self, keywords, target_domain, location_code=2840, language_code="en", pingback_url=None):
        if isinstance(keywords, str):
            keywords = [keywords]

        if not keywords:
            return []

        labs_url = f"{self.BASE_URL}/dataforseo_labs/google/keyword_overview/live"
        labs_payload = [
            {
                "keywords": keywords,
                "language_code": language_code,
            }
        ]

        labs_response = {}
        try:
            logger.info("DataForSEO Labs payload: %s", labs_payload)
            labs_res = requests.post(labs_url, json=labs_payload, auth=self.auth, timeout=60)
            logger.info("DataForSEO Labs status: %s", labs_res.status_code)
            logger.debug("DataForSEO Labs full response: %s", labs_res.text)
            labs_res.raise_for_status()
            labs_response = labs_res.json() or {}
        except Exception as exc:
            logger.error("DataForSEO Labs keyword_overview request failed: %s", exc)

        metrics_map = {}
        if labs_response.get("tasks"):
            for task in labs_response["tasks"]:
                result = task.get("result")
                if not result:
                    continue
                if isinstance(result, list) and result:
                    result = result[0]
                if not isinstance(result, dict):
                    continue

                items = result.get("items") or []
                if not isinstance(items, list) or not items:
                    logger.warning("DataForSEO Labs returned no items for task. Full result=%s", result)
                    continue

                item = items[0]
                keyword_properties = item.get("keyword_properties", {}) or {}
                keyword_info = item.get("keyword_info", {}) or {}
                avg_backlinks_info = item.get("avg_backlinks_info", {}) or {}
                search_intent_info = item.get("search_intent_info", {}) or {}

                keyword_text = item.get("keyword") or (task.get("data") or {}).get("keyword")
                if not keyword_text:
                    continue

                metrics_map[keyword_text] = {
                    "volume": keyword_info.get("search_volume"),
                    "kd": keyword_properties.get("keyword_difficulty"),
                    "cpc": keyword_info.get("cpc"),
                    "competition": keyword_info.get("competition"),
                    "intent": search_intent_info.get("main_intent"),
                    "backlinks": avg_backlinks_info.get("backlinks"),
                    "referring_domains": avg_backlinks_info.get("referring_domains"),
                }
                logger.info("DataForSEO Labs metrics for '%s': %s", keyword_text, metrics_map[keyword_text])

        serp_url = f"{self.BASE_URL}/serp/google/organic/live/advanced"
        serp_tasks = [
            {
                "keyword": kw,
                "location_code": location_code,
                "language_code": language_code,
                "device": "desktop",
                "depth": 100,
                "expand_ai_overview": True,
            }
            for kw in keywords
        ]

        serp_response = {}
        try:
            serp_res = requests.post(serp_url, json=serp_tasks, auth=self.auth, timeout=120)
            serp_res.raise_for_status()
            serp_response = serp_res.json() or {}
            logger.debug("DataForSEO SERP full response: %s", serp_response)
        except Exception as exc:
            logger.error("DataForSEO SERP live/advanced request failed: %s", exc)

        serp_map = {}
        if serp_response.get("tasks"):
            for task in serp_response["tasks"]:
                keyword_text = (task.get("data") or {}).get("keyword")
                if not keyword_text:
                    continue

                result_blocks = task.get("result", []) or []
                if isinstance(result_blocks, list) and result_blocks:
                    first_block = result_blocks[0]
                    serp_items = first_block.get("items", []) or []
                elif isinstance(result_blocks, dict):
                    serp_items = result_blocks.get("items", []) or []
                else:
                    serp_items = []

                detected_position = None
                has_aio_badge = None
                check_url = None

                for item in serp_items:
                    item_type = item.get("type", "")

                    if item_type == "organic" and item.get("url"):
                        if target_domain and target_domain.lower() in item.get("url", "").lower():
                            candidate_position = item.get("rank_absolute") or item.get("rank_group")
                            if candidate_position and (detected_position is None or candidate_position < detected_position):
                                detected_position = candidate_position
                            if not check_url:
                                check_url = item.get("url")

                    if item_type in ("local_pack", "map", "local_services", "knowledge_graph", "google_hotels"):
                        url = item.get("url") or ""
                        domain = item.get("domain") or ""
                        if target_domain and (target_domain.lower() in url.lower() or target_domain.lower() in domain.lower()):
                            if detected_position is None:
                                detected_position = 1
                            if not check_url:
                                check_url = url or f"https://{domain}" if domain else url

                    if item_type == "ai_overview":
                        references = item.get("ai_overview_reference", []) or item.get("references", []) or []
                        if isinstance(references, list):
                            for ref in references:
                                if ref and ref.get("url") and target_domain:
                                    if target_domain in ref.get("url", "").lower():
                                        has_aio_badge = "AIO"

                item_groups = first_block.get("item_groups", []) or []
                for group in item_groups:
                    group_type = group.get("type")
                    group_items = group.get("items", []) or []
                    if group_type == "ai_overview" and group_items and not has_aio_badge:
                        references = group_items[0].get("references", []) or group_items[0].get("ai_overview_reference", []) or []
                        if isinstance(references, list):
                            for ref in references:
                                if ref and ref.get("url") and target_domain:
                                    if target_domain in ref.get("url", "").lower():
                                        has_aio_badge = "AIO"

                serp_map[keyword_text] = {
                    "position": detected_position,
                    "ai_badge": has_aio_badge,
                    "check_url": check_url,
                }
                logger.info("DataForSEO SERP detection for '%s': position=%s, aio=%s, check_url=%s",
                            keyword_text, detected_position, has_aio_badge, check_url)

        final_table_rows = []
        for kw in keywords:
            kw_metrics = metrics_map.get(kw, {
                "volume": None, "kd": None, "cpc": None,
                "competition": None, "backlinks": None, "referring_domains": None,
                "intent": None,
            })
            serp_data = serp_map.get(kw, {})

            final_table_rows.append({
                "keyword": kw,
                "volume": kw_metrics.get("volume"),
                "kd": kw_metrics.get("kd"),
                "cpc": kw_metrics.get("cpc"),
                "competition": kw_metrics.get("competition"),
                "backlinks": kw_metrics.get("backlinks"),
                "referring_domains": kw_metrics.get("referring_domains"),
                "intent": kw_metrics.get("intent"),
                "position": serp_data.get("position"),
                "ai_badge": serp_data.get("ai_badge"),
                "check_url": serp_data.get("check_url"),
            })

        logger.info("DataForSEO dashboard fetch complete: %d keywords, %d with metrics, %d with SERP",
                    len(keywords), len(metrics_map), len(serp_map))
        return final_table_rows
