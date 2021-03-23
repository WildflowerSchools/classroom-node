import json


class DatabaseConnectionSnoop():
    def write_datapoint_object_time_series(
        self,
        timestamp,
        object_id,
        data
    ):
        value_dict = {
            'timestamp': timestamp.isoformat(),
            'object_id': object_id
        }
        value_dict.update(data)
        value_dict['timestamp'] = value_dict['timestamp'].isoformat()
        print(json.dumps(value_dict))
