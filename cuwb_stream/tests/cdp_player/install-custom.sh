#!/usr/bin/env bash

REPO_URL='ppa.cuwb.io'

if [[ -z "${REPO_NAME}" ]]; then
  echo "Cmd line arg 'REPO_NAME' missing. Required to download from proper Ciholas PPA.";
  exit 1;
fi


CUWB_SERVER_DB_DIR='/var/lib/cuwb/server/db-files/uwb/saved/'

# util function to make wait for dpkg lock
function waitForDpkg() {
    while fuser /var/lib/dpkg/lock >/dev/null 2>&1
        do sleep 1
    done
}

# check if user is in sudoers
if groups $(whoami) | grep &>/dev/null '\bsudo\b'; then
    echo 'User is a sudoer'
else
    echo 'You must belong to the sudo group to complete installation of CUWB Package Installer'
    exit 1
fi

# check if current env headless or not
HEADLESS=true
waitForDpkg
if dpkg -l ubuntu-desktop &>/dev/null; then
    echo 'GUI environment detected'
    HEADLESS=false
fi

# check for 16.04 or 18.04 or 20.04
DISTRO=$(lsb_release -cs)
echo "Detected distribution: $DISTRO"
if [[ $DISTRO == 'xenial' ]]; then
    echo 'WARNING: Ubuntu 16.04 (xenial) is deprecated.  You may be unable to upgrade to the newest CUWB package versions.  It is recommended that you upgrade to a newer Ubuntu LTS version.'
elif [[ $DISTRO != 'bionic' ]] && [[ $DISTRO != 'focal' ]]; then
    echo 'This distribution is not currently supported. Bailing!'
    exit 1
fi

# PPA to sources.list install logic
function add_ppa_if_needed() {
    echo 'Adding Ciholas key'
    sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 13FB78B5
    if [ $? -ne 0 ]; then
        echo 'Adding Ciholas key failed via hkp. You may be behind a proxy. Attempting alternate route.'
        wget -qO - https://cuwb.io/ciholas.pgp | sudo apt-key add -
        if [ $? -ne 0 ]; then
            echo 'Adding Ciholas trusted key failed. Installation will halt. Please contact cuwb.support@ciholas.com for assistance with the above log output.'
            exit 1
        fi
    fi
    grep ^ /etc/apt/sources.list /etc/apt/sources.list.d/* | grep "$REPO_URL/$REPO_NAME" &>/dev/null
    if [ $? -ne 0 ]; then
        echo 'Adding CUWB PPA'
        source /etc/lsb-release
        echo "deb [arch=amd64] https://$REPO_URL/$REPO_NAME/ $DISTRIB_CODENAME main" |
            sudo tee /etc/apt/sources.list.d/cuwb.list
    fi
}

# CDP Logger
function install_cdp_logger() {
    waitForDpkg
    echo 'Installing CDP Logger'
    sudo apt install -y cdp-logger
}

# save references to stdout and stderr because whiptail necessitates doing some return through stderr
exec {STDOUTBACK}>&1
exec {STDERRBACK}>&2

# Restore fds
exec 1>&$STDOUTBACK
exec 2>&$STDERRBACK

# Close temporal fds
exec {STDOUTBACK}>&-
exec {STDERRBACK}>&-

add_ppa_if_needed
sudo apt update
waitForDpkg

install_cdp_logger

exit 0
