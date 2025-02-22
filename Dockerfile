FROM debian:bullseye-slim

ENV TZ=US/Eastern

# Upgrade & Install required packages
RUN apt-get update && \
    apt-get upgrade -y && \
    apt install --no-install-recommends -y \
    ca-certificates firefox-esr git libxtst6 libgtk-3-0 nano openbox procps python3 socat tigervnc-standalone-server tzdata unzip wget2 xterm 

# Setup noVNC for browser VNC access
RUN git clone --depth 1 https://github.com/novnc/noVNC.git && \
    chmod +x ./noVNC/utils/novnc_proxy && \
    git clone --depth 1 https://github.com/novnc/websockify.git /noVNC/utils/websockify

# Override default noVNC file listing
COPY image-files/index.html /noVNC
COPY image-files/tws.png /noVNC

# Download and setup IBC
RUN wget2 https://github.com/IbcAlpha/IBC/releases/download/3.21.0/IBCLinux-3.21.0.zip -O ibc.zip \
    && unzip ibc.zip -d /opt/ibc \
    && rm ibc.zip

# Download IB Gateway (which contains TWS) stable | latest
ENV TWS_VERSION=latest

RUN wget2 https://download2.interactivebrokers.com/installers/ibgateway/${TWS_VERSION}-standalone/ibgateway-${TWS_VERSION}-standalone-linux-x64.sh -O "tws-linux-x64.sh" 

RUN chmod +x "tws-linux-x64.sh" \
    && yes '' | "./tws-linux-x64.sh"  \
    && rm "tws-linux-x64.sh"

# Copy scripts
COPY image-files/start.sh ./

RUN mkdir -p ~/ibc && mv /opt/ibc/config.ini ~/ibc/config.ini

COPY ./ibc/config.ini /root

ENV TWS_SETTINGS_PATH=/root

RUN chmod a+x *.sh /opt/ibc/*.sh /opt/ibc/scripts/*.sh

CMD [ "./start.sh" ]
