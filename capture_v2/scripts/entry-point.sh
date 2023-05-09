#!/bin/sh

# If a wildflower-config.yml file is mounted and available, we use that to configure the Minio bucket that videos are
# uploaded to. We also use the values in the config to add additional hosts to /etc/hosts.
WF_CONFIG=/boot/wildflower-config.yml
if [ -f "${WF_CONFIG}" ]; then
    CAMERA_DEVICE_ID=`yq '.device_id' < "${WF_CONFIG}"`

    export MINIO_FOLDER="${CAMERA_DEVICE_ID}"
fi

service udev restart
udevadm control --reload

su docker --command "$@"
