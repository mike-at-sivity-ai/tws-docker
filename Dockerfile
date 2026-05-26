FROM debian:bullseye-slim

ENV TZ=US/Eastern

# Upgrade & Install required packages
RUN apt-get update && \
    apt-get upgrade -y && \
    apt install --no-install-recommends -y \
    ca-certificates chromium git libxtst6 libgtk-3-0 nano openbox procps python3 socat tigervnc-standalone-server tint2 tzdata unzip wget2 wmctrl xdotool xterm

# Setup noVNC for browser VNC access
RUN git clone --depth 1 https://github.com/novnc/noVNC.git && \
    chmod +x ./noVNC/utils/novnc_proxy && \
    git clone --depth 1 https://github.com/novnc/websockify.git /noVNC/utils/websockify

# Override default noVNC file listing
COPY image-files/index.html /noVNC
COPY image-files/tws.png /noVNC

# Download and setup IBC
RUN wget2 https://github.com/IbcAlpha/IBC/releases/download/3.23.0/IBCLinux-3.23.0.zip -O ibc.zip \
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

# Copy openbox config (taskbar + window rules)
RUN mkdir -p /root/.config/openbox
COPY image-files/openbox/autostart /root/.config/openbox/autostart
COPY image-files/openbox/rc.xml /root/.config/openbox/rc.xml

# Copy tint2 config (no desktop pager, autohide enabled)
RUN mkdir -p /root/.config/tint2
COPY image-files/tint2/tint2rc /root/.config/tint2/tint2rc

RUN mkdir -p ~/ibc && mv /opt/ibc/config.ini ~/ibc/config.ini

COPY ./ibc/config.ini /root

ENV TWS_SETTINGS_PATH=/root
ENV BROWSER=/usr/local/bin/chromium

# Wrapper so chromium runs with --no-sandbox (required when running as root)
COPY image-files/chromium-wrapper /usr/local/bin/chromium
RUN chmod +x /usr/local/bin/chromium && \
    update-alternatives --install /usr/bin/x-www-browser x-www-browser /usr/local/bin/chromium 200

# Managed policy: disable bookmarks bar (overrides user prefs, survives profile resets)
RUN mkdir -p /etc/chromium/policies/managed
COPY image-files/chromium/policy.json /etc/chromium/policies/managed/policy.json

RUN chmod a+x *.sh /opt/ibc/*.sh /opt/ibc/scripts/*.sh

CMD [ "./start.sh" ]
