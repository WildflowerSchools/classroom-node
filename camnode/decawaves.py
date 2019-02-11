"""
Worker that talks to decawave devices, currently over BLE

TODO:
- reload the environment periodically
- safe kill function for the device thread (Queue?)
- push the data to celery for honeycomb upload

"""
from datetime import datetime
import logging
import threading
import time

import decawave_ble

# from camnode.workers import app


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


ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def in_date_range(date=None, start=None, end=None):
    if date is None:
        return False
    cmp = datetime.strptime(date, ISO_FORMAT)
    if start is not None:
        st_cmp = datetime.strptime(start, ISO_FORMAT)
        if cmp < st_cmp:
            return False
    if end is not None:
        end_cmp = datetime.strptime(end, ISO_FORMAT)
        if cmp > end_cmp:
            return False
    return True



class DecawaveCollector:

    def __init__(self, environment_id, honeycomb_client):
        self.environment_id = environment_id
        self.honeycomb_client = honeycomb_client
        self.device_map = dict()
        self.assignment_map = dict()

    def start(self):
        logging.debug("starting decawave data collection")
        devices = self.resolve_devices()
        # self.poll_devices(devices)

    def resolve_devices(self):
        target_device_names = self.get_env_device_list()
        if len(target_device_names):
            decawave_devices = self.do_scan()
            return {name: decawave_devices.get(name) for name in target_device_names}
        return dict()

    def get_env_device_list(self):
        environment = self.honeycomb_client.query.query("""query getEnvironment ($environment_id: ID!) {
              getEnvironment(environment_id: $environment_id) {
                assignments {
                  start
                  end
                  assigned {
                    ... on Device {
                      device_id
                      part_number
                    }
                  }
                }
              }
            }
            """, {"environment_id": self.environment_id}).get("getEnvironment")
        print(environment)
        assignments = environment.get("assignments")
        now = datetime.utcnow().strftime(ISO_FORMAT)
        valid_assignments = [ass for ass in assignments if in_date_range(now, ass.get("start"), ass.get("end"))]
        logging.debug("loaded environment %s and found %s devices assinged, %s are current", self.environment_id, len(assignments), len(valid_assignments))
        valid = set([va.get("assigned", {}).get("part_number") for va in valid_assignments])
        for assignment in valid_assignments:
            self.assignment_map[assignment.get("assigned", {}).get("part_number")] = assignment
        to_kill = set(self.assignment_map.keys()) - valid
        if len(to_kill):
            # TODO - kill devices that should be killed
            logging.debug("TOO MANY DEVICES: %s", to_kill)
        return list(valid)

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
