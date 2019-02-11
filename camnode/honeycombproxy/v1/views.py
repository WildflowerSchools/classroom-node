from flask import make_response, Blueprint, jsonify


v1 = Blueprint('v1', __name__)


@v1.route("/device/{device_id}", methods=['GET'])
def device_handler():
    """Device register

    A device when coming on line should call this endpoint to determine the
    environment state. The call sends the device id that is set by Honeycomb.
    The proxy should have been configured with an environment id so it can
    confirm that the device should be connected to this proxy. The response
    from this will contain details about the environment state and what state
    the device should be in.

    Response looks like this:
    ```
    {
        "status": "ok",
        "environment": "<environment_id>",
        "state": "<ACTIVE|INACTIVE|ERROR>",
        "device": {
            "valid": <true|false>,
            "config": {
                <key>: <value>,
                ...
            }
        },
        "poll": <0 or positive integer>,
    }
    ```

    `status` will always be ok unless a serious error has occurred.

    `environment` is the id of the environment in Honeycomb, if this is
    `None` then the proxy device has not been setup and the device should
    poll this endpoint again after the number of seconds the `poll` value
    states in the response.

    `state` reflects the current state of the environment. `ACTIVE` means
    the environment is in it's normal active state and devices should be
    sending data if told to do so. If this is `INACTIVE` or `ERROR` then
    devices should not send data regardless of the `mode` specified. Devices
    can however queue data points for a reasonable time until the next poll.
    If the environment changes to `ACTIVE` then the queued data points can be
    sent. The device should not send points older than the most recent `INACTIVE`
    poll response.

    `device` instructs the device on how to set it's state. `valid` should be
    true, if it is not then the device is not assigned to this environment and
    should not send data to this proxy. The device can ping the proxy again on
    the poll interval to see if it has been added to the environment. It can
    follow the same advice for queuing data as the `state` setting advises.
    `config` is the device configuration for this environment assignment. When
    received the device should determine if it has changed and if it should
    reconfigure itself.

    `poll` is an integer that instructs the calling device to callback after
    that many seconds to determine if there is a state change for that device
    or this environment.
    """
    return make_response(jsonify({"status": "not-implemented"}), 200)


@v1.route("/device/{device_id}/data", methods=['PUT'])
def put_data_handler(device_id):
    """Data point creation

    A device will call this when appropriate to have data sent to Honeycomb.
    The proxy augments the data with some meta-data about the assignment.
    """
    return make_response(jsonify({"status": "not-implemented"}), 200)
