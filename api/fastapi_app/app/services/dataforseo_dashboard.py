import logging
import re
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
                "location_code": location_code,
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
                    "keyword": keyword_text,
                    "volume": keyword_info.get("search_volume"),
                    "kd": keyword_properties.get("keyword_difficulty"),
                    "cpc": keyword_info.get("cpc"),
                    "competition": keyword_info.get("competition"),
                    "competition_level": keyword_info.get("competition_level"),
                    "intent": search_intent_info.get("main_intent"),
                    "foreign_intent": search_intent_info.get("foreign_intent"),
                    "backlinks": avg_backlinks_info.get("backlinks"),
                    "dofollow": avg_backlinks_info.get("dofollow"),
                    "referring_pages": avg_backlinks_info.get("referring_pages"),
                    "referring_domains": avg_backlinks_info.get("referring_domains"),
                    "referring_main_domains": avg_backlinks_info.get("referring_main_domains"),
                    "domain_rank": avg_backlinks_info.get("main_domain_rank"),
                    "etv": avg_backlinks_info.get("etv"),
                    "categories": keyword_info.get("categories"),
                    "monthly_searches": keyword_info.get("monthly_searches"),
                    "search_volume_trend": keyword_info.get("search_volume_trend"),
                    "low_top_of_page_bid": keyword_info.get("low_top_of_page_bid"),
                    "high_top_of_page_bid": keyword_info.get("high_top_of_page_bid"),
                    "detected_language": keyword_properties.get("detected_language"),
                    "words_count": keyword_properties.get("words_count"),
                }
                logger.info("DataForSEO Labs metrics for '%s': volume=%s kd=%s cpc=%s competition=%s intent=%s",
                            keyword_text,
                            metrics_map[keyword_text].get("volume"),
                            metrics_map[keyword_text].get("kd"),
                            metrics_map[keyword_text].get("cpc"),
                            metrics_map[keyword_text].get("competition"),
                            metrics_map[keyword_text].get("intent"))

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
                ai_description = None

                for item in serp_items:
                    item_type = item.get("type", "")

                    if item_type == "organic" and item.get("url"):
                        if target_domain and target_domain.lower() in item.get("url", "").lower():
                            candidate_position = item.get("rank_group") or item.get("rank_absolute")
                            if candidate_position and (detected_position is None or candidate_position < detected_position):
                                detected_position = candidate_position
                            if not check_url:
                                check_url = item.get("url")

                    if item_type in ("local_pack", "map", "local_services", "knowledge_graph", "google_hotels"):
                        url = item.get("url") or ""
                        domain = item.get("domain") or ""
                        if target_domain and (target_domain.lower() in url.lower() or target_domain.lower() in domain.lower()):
                            if detected_position is None:
                                detected_position = item.get("rank_group") or item.get("rank_absolute") or 1
                            if not check_url:
                                check_url = url or f"https://{domain}" if domain else url

                    if item_type == "ai_overview":
                        if item.get("asynchronous_ai_overview") is True:
                            has_aio_badge = "AIO"
                        logger.info("AIO item fields for '%s': %s", keyword_text, list(item.keys()))
                        ai_description = item.get("description") or item.get("text") or item.get("content") or ai_description
                        if not ai_description and item.get("markdown"):
                            ai_description = item.get("markdown")
                        nested_items = item.get("items") or []
                        if isinstance(nested_items, list):
                            for nested in nested_items:
                                if not ai_description and nested and nested.get("description"):
                                    ai_description = nested.get("description")
                                if not ai_description and nested and nested.get("text"):
                                    ai_description = nested.get("text")
                        references = item.get("ai_overview_reference", []) or item.get("references", []) or []
                        if isinstance(references, list):
                            for ref in references:
                                if ref and ref.get("url") and target_domain:
                                    if target_domain in ref.get("url", "").lower():
                                        has_aio_badge = "AIO"
                        logger.info("AIO extracted for '%s': has_aio=%s description=%s", keyword_text, has_aio_badge, ai_description)

                    if item_type == "organic" and item.get("url"):
                        item_domain = (item.get("domain") or "").lower()
                        item_url = item.get("url") or ""
                        if target_domain and (target_domain.lower() in item_url.lower() or target_domain.lower() in item_domain):
                            if has_aio_badge != "AIO":
                                has_aio_badge = "AIO"
                            if not ai_description and item.get("description"):
                                ai_description = item.get("description")
                            if not check_url:
                                check_url = item_url

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
                    "ai_description": ai_description,
                    "check_url": check_url,
                }
                logger.info("DataForSEO SERP detection for '%s': position=%s, aio=%s, check_url=%s",
                            keyword_text, detected_position, has_aio_badge, check_url)

        final_table_rows = []
        for kw in keywords:
            kw_metrics = metrics_map.get(kw, {
                "keyword": kw,
                "volume": None, "kd": None, "cpc": None,
                "competition": None, "backlinks": None, "referring_domains": None,
                "intent": None, "foreign_intent": None, "competition_level": None,
                "dofollow": None, "referring_pages": None, "referring_main_domains": None,
                "domain_rank": None, "etv": None, "categories": None,
                "monthly_searches": None, "search_volume_trend": None,
                "low_top_of_page_bid": None, "high_top_of_page_bid": None,
                "detected_language": None, "words_count": None,
            })
            serp_data = serp_map.get(kw, {})

            merged = {**kw_metrics, **serp_data}
            final_table_rows.append(merged)

        logger.info("DataForSEO dashboard fetch complete: %d keywords, %d with metrics, %d with SERP",
                    len(keywords), len(metrics_map), len(serp_map))
        return final_table_rows
