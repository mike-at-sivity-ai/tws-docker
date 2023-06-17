FROM debian:20-bullseye

ENV TZ=US/Eastern

# Upgrade & Install required packages
RUN echo "deb http://deb.debian.org/debian/ unstable main contrib non-free" >> /etc/apt/sources.list.d/debian.list \
    && apt-get update && \
    apt-get upgrade -y && \
    apt install --no-install-recommends -y \
    ca-certificates firefox git libxtst6 libgtk-3-0 openbox procps python3 socat tigervnc-standalone-server tzdata unzip wget2 xterm

# Setup noVNC for browser VNC access
RUN git clone --depth 1 https://github.com/novnc/noVNC.git && \
    chmod +x ./noVNC/utils/novnc_proxy && \
    git clone --depth 1 https://github.com/novnc/websockify.git /noVNC/utils/websockify

# Override default noVNC file listing
COPY image-files/index.html /noVNC
COPY image-files/tws.png /noVNC

ENV IBC_VERSION=3.16.2

# Download and setup IBC
RUN wget2 https://github.com/IbcAlpha/IBC/releases/download/${IBC_VERSION}/IBCLinux-${IBC_VERSION}.zip -O ibc.zip \
    && unzip ibc.zip -d /opt/ibc \
    && rm ibc.zip

# Download IB Gateway (which contains TWS) stable | latest
ENV TWS_VERSION=stable

RUN wget2 https://download2.interactivebrokers.com/installers/ibgateway/${TWS_VERSION}-standalone/ibgateway-${TWS_VERSION}-standalone-linux-x64.sh -O "tws-linux-x64.sh" 

RUN chmod +x "tws-linux-x64.sh" \
    && yes '' | "./tws-linux-x64.sh"  \
    && rm "tws-linux-x64.sh"

# Copy scripts
COPY image-files/start.sh ./

RUN mkdir -p ~/ibc && mv /opt/ibc/config.ini ~/ibc/config.ini

RUN chmod a+x *.sh /opt/ibc/*.sh /opt/ibc/scripts/*.sh

CMD [ "./start.sh" ]