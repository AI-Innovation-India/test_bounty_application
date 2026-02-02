import requests
from typing import Dict, Any, Optional, List
import json

from src.utils.logger import logger

class APITestEngine:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url.rstrip('/') if base_url else ""
        self.session = requests.Session()

    def set_headers(self, headers: Dict[str, str]):
        """Set default headers for the session."""
        self.session.headers.update(headers)

    def make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make an HTTP request and return details.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}" if self.base_url else endpoint
        
        try:
            response = self.session.request(method, url, **kwargs)
            
            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": None,
                "error": None,
                "elapsed": response.elapsed.total_seconds()
            }

            try:
                result["body"] = response.json()
            except ValueError:
                result["body"] = response.text

            return result

        except Exception as e:
            logger.error(f"API Request failed: {e}")
            return {
                "status_code": 0,
                "error": str(e)
            }

    def validate_response(self, response: Dict[str, Any], expected_status: int, schema: Optional[Dict] = None) -> bool:
        """
        Validate response status and optional schema.
        """
        if response["status_code"] != expected_status:
            return False
        
        # Simple schema validation (keys check)
        if schema and isinstance(response["body"], dict):
            return all(key in response["body"] for key in schema.keys())
            
        return True
