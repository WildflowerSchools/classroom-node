import json


class DatabaseConnectionSnoop():
    def write_datapoint_object_time_series(
        self,
        object_id,
        data
    ):
        value_dict = {
            'object_id': object_id
        }
        value_dict.update(data)
        value_dict['timestamp'] = value_dict['timestamp'].isoformat() if value_dict.get('timestamp', None) else None
        value_dict['socket_read_time'] = value_dict['socket_read_time'].isoformat() if value_dict.get('socket_read_time', None) else None
        print(json.dumps(value_dict))
