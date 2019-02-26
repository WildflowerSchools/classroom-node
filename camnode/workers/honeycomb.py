import logging
import os

from honeycomb import HoneycombClient
from honeycomb.models import DatapointInput, S3FileInput

from camnode.workers import app


client_credentials = {
    "token_uri": "https://wildflowerschools.auth0.com/oauth/token",
    "audience": "https://honeycomb.api.wildflowerschools.org",
    "client_id": "EM2pKhXppSchfOW3v0Mp8gn9MVrFn2Mr",
    "client_secret": "rER306LHMq4hA4KuIum6EWsM0l1HDtLrcT8RgekfIOnIWEn-8cjpK8SonPffV84H",
}
honeycomb_client = HoneycombClient(uri="https://honeycomb.api.wildflower-tech.org/graphql", client_credentials=client_credentials)


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
