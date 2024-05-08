#!/bin/bash

# Fail fast
set -Eeuo pipefail

export DISPLAY=:0

# Clear previous lockfile
rm -f /tmp/.X0-lock

# Start VNC server
Xvnc -SecurityTypes None -AlwaysShared=1 -geometry 1920x1080 :0 &

# Start noVNC server
./noVNC/utils/novnc_proxy --vnc localhost:5900 &

# Start openbox
openbox &

if [[ ${IBC_TradingMode:-live} = "live" ]]; then
    # TWS Live
    port=7496
else
    # TWS Paper
    port=7497
fi


printf "Listening for incoming API connections on %s\n" $port
socat -d -d TCP-LISTEN:8888,fork TCP:127.0.0.1:${port} &

# Hacky way to get the major version for IB Gateway/TWS
TWS_MAJOR_VERSION=$(ls ~/Jts/ibgateway/.)

sed -i -e "s|IbLoginId=edemo|IbLoginId=$IB_USERNAME|g" ~/config.ini
sed -i -e "s|IbPassword=demouser|IbPassword=$IB_PASSWORD|g" ~/config.ini

exec /opt/ibc/scripts/ibcstart.sh "${TWS_MAJOR_VERSION}" "--ibc-ini=/root/config.ini" "--on2fatimeout=restart"