import logging
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

DELHI_BBOX = "76.84,28.40,77.35,28.88"  # lon_min,lat_min,lon_max,lat_max
PARAMETERS = {"pm25", "pm10", "no2", "o3", "so2", "co"}


class OpenAQClient:
    BASE_URL = "https://api.openaq.org/v3"

    def __init__(self, api_key: str, request_delay: float = 0.3):
        self.api_key = api_key
        self.request_delay = request_delay
        self._session = self._build_session()

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=5,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.headers.update({"X-API-Key": self.api_key})
        return session

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{self.BASE_URL}{path}"
        time.sleep(self.request_delay)
        resp = self._session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_delhi_locations(self) -> list[dict]:
        """Fetch all monitoring locations inside Delhi NCR bounding box."""
        locations = []
        page = 1
        while True:
            data = self._get(
                "/locations", {"bbox": DELHI_BBOX, "limit": 100, "page": page}
            )
            results = data.get("results", [])
            if not results:
                break
            locations.extend(results)
            logger.info(f"  page {page}: +{len(results)} (total {len(locations)})")
            if len(results) < 100:
                break
            page += 1
        return locations

    def get_sensors(self, location_id: int) -> list[dict]:
        """Fetch sensors for a location, keeping only target parameters."""
        data = self._get(f"/locations/{location_id}/sensors")
        return [
            s
            for s in data.get("results", [])
            if s.get("parameter", {}).get("name", "").lower() in PARAMETERS
        ]

    def get_measurements(
        self, sensor_id: int, date_from: str, date_to: str
    ) -> list[dict]:
        """Fetch daily measurements for a sensor, paginating to completion."""
        measurements = []
        page = 1
        while True:
            data = self._get(
                f"/sensors/{sensor_id}/days",
                {
                    "date_from": date_from,
                    "date_to": date_to,
                    "limit": 1000,
                    "page": page,
                },
            )
            results = data.get("results", [])
            if not results:
                break
            measurements.extend(results)
            if len(results) < 1000:
                break
            page += 1
        return measurements
