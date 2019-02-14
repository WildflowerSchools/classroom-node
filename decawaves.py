import logging

from honeycomb import HoneycombClient
from camnode.decawaves import DecawaveCollector


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
    client_credentials = {
    # fill this in to use
    }

    honeycomb_client = HoneycombClient(client_credentials=client_credentials)
    enviros = honeycomb_client.query.findEnvironment(name="deco-nook")
    environment_id = enviros.data[0].get("environment_id")
    logging.debug("environment %s found", environment_id)
    collector = DecawaveCollector(environment_id, honeycomb_client)
    collector.start()
