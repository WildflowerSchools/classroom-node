import logging
import os

from honeycomb import HoneycombClient
from honeycomb.models import DatapointInput, S3FileInput

from camnode.workers import app


client_credentials = {
# fill this in to use
}
honeycomb_client = HoneycombClient(client_credentials=client_credentials)


@app.task(name="honeycomb-send-data")
def send_data(assignment_id, ts, format, data, name):
    logging.debug("received data request for %s", assignment_id)
    dp = DatapointInput(
        observer=assignment_id,
        format=format,
        file=S3FileInput(
            name=name,
            contentType=format,
            data=data,
        ),
        observed_time=ts,
    )
    result = honeycomb_client.mutation.createDatapoint(dp)
    print(result.data_id)
