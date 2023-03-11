from datetime import datetime
import json


class UWBConnectionSnoop:
    def write_uwb_network_message(self, object_id, data, msg_type):
        value_dict = {
            "object_id": object_id,
        }
        value_dict.update(data)
        value_dict["timestamp"] = datetime.utcnow().isoformat()
        value_dict["type"] = msg_type
        print(json.dumps(value_dict))
        return value_dict

    def write_uwb_socket_message(self, object_id, data):
        value_dict = {"object_id": object_id}
        value_dict.update(data)
        value_dict["timestamp"] = (
            value_dict["timestamp"].isoformat()
            if value_dict.get("timestamp", None)
            else None
        )
        value_dict["socket_read_time"] = (
            value_dict["socket_read_time"].isoformat()
            if value_dict.get("socket_read_time", None)
            else None
        )
        print(json.dumps(value_dict))
        return value_dict
