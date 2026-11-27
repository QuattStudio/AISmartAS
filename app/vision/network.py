

import requests as req

from core.logger import logger


# LOCAL_HOST_URL = "http://127.0.0.1:5000"
LOCAL_HOST_URL = "http://192.168.1.67:5000"



class Network:

    def __init__(self, url: str = LOCAL_HOST_URL):
        self._url = url.rstrip("/")

    def _post(self, endpoint, data, timeout=10):

        try:
            response = req.post(
                self._url + endpoint,
                json=data,
                timeout=timeout
            )

            try:
                result = response.json()
            except ValueError:
                result = None

            return response.status_code, result

        except req.RequestException as error:
            logger.error(f"Network error: {error}")
            return None, None

    def register_student(self, data):
        return self._post(
            "/api/registration",
            data
        )

    def register_person(self, data):
        return self._post("/api/registration", data)

    def send_attendance(self, person_type, person_id):
        return self._post(
            "/api/attendance",
            {
                "person_type": person_type,
                "person_id": person_id,
            }
        )

    def get_embeddings(self, timeout=30):

        try:
            response = req.get(
                self._url + "/api/students/embeddings",
                timeout=timeout
            )

            response.raise_for_status()

            result = response.json()

            if not result.get("success"):
                return None

            return result.get("students", [])

        except (req.RequestException, ValueError) as error:
            logger.error(f"Embedding download failed: {error}")
            return None




