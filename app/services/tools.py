from agents import function_tool
import requests
import json
from app import CONFIG

ai_service_config = CONFIG.ai_service


@function_tool
def get_search_results_from_google_drive(query: str) -> str:
    """
    Provides search results from Google Drive based on the query.
    Args:
        query (str): The search query.
    Returns:
        str: Google Drive API response with all the relevant details.

    """
    n8n_webhook_url = (
        f"{ai_service_config.google_drive_search_webhook_url}?query={query}"
    )

    response = requests.get(n8n_webhook_url)
    response.raise_for_status()  # Raise an error for bad responses
    data = response.json()
    if not data:
        return json.dumps({"error": "Unable to find any results."})
    return data
