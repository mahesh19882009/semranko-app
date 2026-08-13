import logging
import warnings

from app.services.dataforseo_client import DataForSEOClient

logger = logging.getLogger(__name__)


class DataForSeoDashboardHelper:
    """Deprecated thin wrapper around DataForSEOClient.fetch_dashboard_data.

    This class exists only for backward compatibility during the transition
    period. All new code should use DataForSEOClient directly.
    """

    def __init__(self, username, password):
        warnings.warn(
            "DataForSeoDashboardHelper is deprecated. Use DataForSEOClient.fetch_dashboard_data instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    def fetch_cheapest_dashboard_data(self, keywords, target_domain, location_code=2840, language_code="en", pingback_url=None):
        return DataForSEOClient.fetch_dashboard_data(
            keywords,
            target_domain,
            location_code=location_code,
            language_code=language_code,
            pingback_url=pingback_url,
        )
