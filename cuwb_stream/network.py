import requests
from tenacity import retry, wait_random_exponential


HOSTNAME = "10.22.0.110:5000"

BASE_URL = f"http://{HOSTNAME}"


def get_networks():
    res = requests.get("/".join([BASE_URL, "cuwbnets"]))
    return res.json()


def start_network(name):
    res = requests.post("/".join(([BASE_URL, "cuwbnets", name])), json={"action": "start"})
    return res.json().get("status") == "success"


def stop_network(name):
    res = requests.post("/".join(([BASE_URL, "cuwbnets", name])), json={"action": "stop"})
    return res.json().get("status") == "success"


def is_network_running(name):
    res = requests.get("/".join(([BASE_URL, "cuwbnets", name])))
    cuwbnets = res.json().get("cuwbnets")
    if cuwbnets:
        return cuwbnets[0].get("running")
    return False


class FailedToStart(Exception):

    def __init__(self, name):
        super().__init__(f"Failed to start `{name}` cuwbnet")


class FailedToStop(Exception):

    def __init__(self, name):
        super().__init__(f"Failed to stop `{name}` cuwbnet")


@retry(wait=wait_random_exponential(multiplier=1, max=10))
def ensure_network_is_running(name):
    if not is_network_running(name):
        start_network(name)
        if not is_network_running(name):
            raise FailedToStart(name)


@retry(wait=wait_random_exponential(multiplier=1, max=10))
def ensure_network_is_stopped(name):
    if is_network_running(name):
        stop_network(name)
        if is_network_running(name):
            raise FailedToStop(name)
