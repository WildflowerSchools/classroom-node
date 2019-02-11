import logging

from honeycomb import HoneycombClient
from camnode.decawaves import DecawaveCollector


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
    client_credentials = {
        "token_uri": "https://wildflowerschools.auth0.com/oauth/token",
        "audience": "https://honeycomb.api.wildflowerschools.org",
        "client_id": "EM2pKhXppSchfOW3v0Mp8gn9MVrFn2Mr",
        "client_secret": "rER306LHMq4hA4KuIum6EWsM0l1HDtLrcT8RgekfIOnIWEn-8cjpK8SonPffV84H",
    }

    honeycomb_client = HoneycombClient(client_credentials=client_credentials)
    enviros = honeycomb_client.query.findEnvironment(name="Developer Lounge")
    environment_id = enviros.data[0].get("environment_id")
    logging.debug("environment %s found", environment_id)
    collector = DecawaveCollector(environment_id, honeycomb_client)
    collector.start()
