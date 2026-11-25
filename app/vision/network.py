import requests as req
from app.core.logger import logger



LOCAL_HOST_URL = "http://localhost:5000"


class Network:
    def __init__(self, url: str = LOCAL_HOST_URL):
        self._url = url

    
    def send(self, data, timeout: int = 10) -> tuple[int | None, dict | None]:
        try:
            response = req.post(self._url, json=data, timeout=timeout)

            statusCode = response.status_code
            data       = response.json()

            return statusCode, data

        except req.RequestException as error:
            logger.error(f"Network error: {error}")
            return None, None
        


"""

    Probably data we recieve and send are both in dictionary

    # data that is going to send

    {
        "student_name
    }



"""


