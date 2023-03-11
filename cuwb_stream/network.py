import os

import requests
from tenacity import retry, wait_random_exponential


class FailedToStart(Exception):
    def __init__(self, name):
        super().__init__(f"Failed to start `{name}` cuwbnet")


class FailedToStop(Exception):
    def __init__(self, name):
        super().__init__(f"Failed to stop `{name}` cuwbnet")


class CUWBNetwork:
    def __init__(self, host=None, port=None):
        self.host = host
        if self.host is None:
            self.host = os.getenv("CUWB_NETWORK_IP", "0.0.0.0")

        self.port = port
        if self.port is None:
            self.port = os.getenv("CUWB_NETWORK_PORT", "5000")

        self.url = f"http://{self.host}:{self.port}/cuwbnets"

    def _request(self, method="GET", path="/", json=None):
        url = "/".join(p.strip("/") for p in [self.url, path]).strip("/")
        res = requests.request(method=method, headers={"Content-Type": "application/json"}, url=url, json=json, timeout=10)
        return res.json()

    def _get(self, path="/"):
        return self._request(method="GET", path=path)

    def _post(self, path="/", json=None):
        return self._request(method="POST", path=path, json=json)

    def get_networks(self):
        return self._get().get("cuwbnets", [])

    def get_devices(self, network_name):
        return self._get(f"{network_name}/devices").get("devices", [])

    def get_settings(self, network_name):
        return self._get(f"{network_name}/settings").get("settings", [])

    def start_network(self, network_name):
        res = self._post(f"{network_name}", json={"action": "start"})
        return res.get("status") == "success"

    def stop_network(self, network_name):
        res = self._post(f"{network_name}", json={"action": "stop"})
        return res.get("status") == "success"

    def is_network_running(self, network_name):
        res = self._get(f"{network_name}")
        cuwbnets = res.get("cuwbnets")
        if cuwbnets:
            return cuwbnets[0].get("running")
        return False

    @retry(wait=wait_random_exponential(multiplier=1, max=10))
    def ensure_network_is_running(self, name):
        if not self.is_network_running(name):
            self.start_network(name)
            if not self.is_network_running(name):
                raise FailedToStart(name)

    @retry(wait=wait_random_exponential(multiplier=1, max=10))
    def ensure_network_is_stopped(self, name):
        if self.is_network_running(name):
            self.stop_network(name)
            if self.is_network_running(name):
                raise FailedToStop(name)
