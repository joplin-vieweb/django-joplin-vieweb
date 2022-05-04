import requests
import logging

class Api():
    def __init__(self, url: str) -> None:
        self.url = url
        if not self.url.endswith("/"):
            self.url = self.url + "/"

    def _request(self, method: str, path: str, data = None) -> requests.models.Response:
        password_safe_data = None
        if data is not None:
            password_safe_data = {key: value if not "password" in key.lower() else "*****" for key, value in data.items()}

        logging.debug(f"joplin-x-api: {method} request: path={path}, data={password_safe_data}")
        try:
            response: requests.models.Response = getattr(requests, method)(
                f"{self.url}{path}",
                json=data
            )
            logging.debug(f"joplin-x-api: response {response.text}")
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            err.args = err.args + (response.text,)
            raise
        return response

    def get_conf(self):
        return self._request("get", "joplin/config").json()

    def set_conf(self, config_data):
        return self._request("post", "joplin/config", data=config_data)

    def test_conf(self, config_data):
        return self._request("post", "joplin/config/test", data=config_data)

    def start_synch(self):
        self._request("post", "joplin/synch/")

    def get_synch(self):
        return self._request("get", "joplin/synch").json()

    def e2ee_decrypt(self, password):
        return self._request("post", "joplin/e2ee/decrypt", data={"password": password})
