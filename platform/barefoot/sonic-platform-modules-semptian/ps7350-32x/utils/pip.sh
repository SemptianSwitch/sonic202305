#!/usr/bin/env bash

platform="onie_platform"
config_file="/host/machine.conf" 
cmd=`cat ${config_file} | awk -F'=' '{ if ($1=="'$platform'") {print $2}}'`
PLATFORM_NAME=`echo $cmd`
SONIC_PLATFORM_WHEEL="/usr/share/sonic/device/${PLATFORM_NAME}/sonic_platform-1.0-py3-none-any.whl"

# If the sonic-platform package is not installed, try to install it
pip show sonic-platform > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "sonic-platform package not installed, attempting to install..."
    if [ -e ${SONIC_PLATFORM_WHEEL} ]; then
       pip install ${SONIC_PLATFORM_WHEEL}
       if [ $? -eq 0 ]; then
          echo "Successfully installed ${SONIC_PLATFORM_WHEEL}"
       else
          echo "Error: Failed to install ${SONIC_PLATFORM_WHEEL}"
       fi
    else
       echo "Error: Unable to locate ${SONIC_PLATFORM_WHEEL}"
    fi
fi
