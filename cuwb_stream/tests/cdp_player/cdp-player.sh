#!/bin/sh

trap 'exit 130' INT

INTERFACE_IP=$(ip addr show eth0 | grep "inet\b" | awk '{print $2}' | cut -d/ -f1)
UDP_IP_PORT=$(nslookup host.docker.internal | grep -Po 'Address:\s*[0-9.]+' | tail -1 | sed -e 's/Address:\s*//g')

cdp-player -l -f /cdp-logger/cdplog-2022-11-08.00 -s 2.0 -i $INTERFACE_IP -u $UDP_IP_PORT:7667
