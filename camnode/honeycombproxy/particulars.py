import os

from redis import Redis

from honeycomb import HoneycombClient
from camnode.workers.honeycomb import send_data


class Particulars:

    def __init__(self):
        self.__honeycomb = HoneycombClient()
        # redis for cache
        cache_redis_args = {}
        if "CACHE_REDIS_HOST" in os.environ:
            cache_redis_args["host"] = os.environ["CACHE_REDIS_HOST"]
        if "CACHE_REDIS_PORT" in os.environ:
            cache_redis_args["port"] = os.environ["CACHE_REDIS_PORT"]
        if "CACHE_REDIS_PASS" in os.environ:
            cache_redis_args["password"] = os.environ["CACHE_REDIS_PASS"]
        if "CACHE_REDIS_DB" in os.environ:
            cache_redis_args["db"] = os.environ["CACHE_REDIS_DB"]
        self.__cache_redis = Redis(**cache_redis_args)

    def get_environment_info(self):
        """Environment Info from Honeycomb

        Fetches the environment info from honeycomb.
        This data could be from a local cache.
        """
        pass

    def get_assignments(self):
        """List of assignments for this environment

        Fetches the environment assignments from honeycomb.
        This data could be from a local cache.
        """
        pass

    def device_check(self, device_id):
        """Is the specified device in the environment

        Returns the device details about the assignment.
        This data could be from a local cache.
        """
        pass

    def device_data_handler(self, device_id, data):
        """Queue the data for honeycomb"""
        send_data.apply_async()
