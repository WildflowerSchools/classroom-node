"""
Worker that talks to decawave devices, currently over BLE

TODO:
- reload the environment periodically
- safe kill function for the device thread (Queue?)
- push the data to celery for honeycomb upload

"""
import logging
import threading
import time

import decawave_ble

from camnode.workers import app


def device_thread(device, collector, sleep_time=0.1):
    if device is None:
        logging.debug("device %s not available", threading.current_thread().name)
        return
    peripheral = decawave_ble.get_decawave_peripheral(device)
    try:
        while True:
            data = decawave_ble.get_location_data_from_peripheral(peripheral)
            logging.debug(data)
            collector.queue_data_point(data)
            time.sleep(sleep_time)
    finally:
        logging.debug("device %s disconnected", device.device_name)
        peripheral.disconnect()


class DecawaveCollector:

    def __init__(self, environment_id, honeycomb_client):
        self.honeycomb_client = honeycomb_client
        self.device_map = dict()

    def start(self):
        logging.debug("starting decawave data collection")
        devices = self.resolve_devices()
        self.poll_devices(devices)

    def resolve_devices(self):
        decawave_devices = self.do_scan()
        target_device_names = self.get_env_device_list()
        return {name: decawave_devices.get(name) for name in target_device_names}

    def get_env_device_list(self):
        self.honeycomb_client
        return [
            "DW4B94",
            "DWD538",
            "DW0D9F",
            "DW088C",
            "DW0000",
        ]

    def do_scan(self):
        """Scans for decawave devices in range"""
        return decawave_ble.scan_for_decawave_devices()

    def poll_devices(self, devices):
        """Loops over the devices and requests location data for each.

        For each device that data is found for the data is queued to be sent to honeycomb."""
        threads = [threading.Thread(target=device_thread, name=name, args=[device, self, 0.01]) for name, device in devices.items()]
        for thread in threads:
            thread.start()

    def queue_data_point(self, data):
        """Puts data on the queue"""
        app.send_task("honeycomb-send-data", args=[assignment_id, parent_data_point_id, data])

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
    honeycomb_client = HoneycombClient("http://localhost:4000/graphql", "")
    enviros = honeycomb_client.query.findEnvironment(name="Developer Lounge")
    environment_id = enviros.data[0].environment_id
    logging.debug("environment %s found", environment_id)
    # collector = DecawaveCollector()
    # collector.start()
