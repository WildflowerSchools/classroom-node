#!/bin/sh

# If a wildflower-config.yml file is mounted and available, we use that to configure the Minio bucket that videos are
# uploaded to. We also set the CLASSROOM_ENVIRONMENT_ID that's used for fetching data related to the camera's
# classroom
WF_CONFIG=/boot/wildflower-config.yml
if [ -f "${WF_CONFIG}" ]; then
    CAMERA_DEVICE_ID=`yq '.device_id' < "${WF_CONFIG}"`
    CLASSROOM_ENVIRONMENT_ID=`yq '.environment-id' < "${WF_CONFIG}"`

    export CLASSROOM_ENVIRONMENT_ID="${CLASSROOM_ENVIRONMENT_ID}"
    export MINIO_FOLDER="${CAMERA_DEVICE_ID}"
fi

service udev restart
udevadm control --reload

su docker --command "$@"
