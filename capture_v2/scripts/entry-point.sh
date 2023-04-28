#!/bin/sh

service udev restart
udevadm control --reload

su docker --command "$@"
