FROM docker:28-dind@sha256:9a06753d2401cd049b34cd27dbbc3e0db717d4c1db7bc7f2efad1c187e00bf5a
RUN apk add --no-cache dnsmasq
COPY start.sh /usr/local/bin/release-engine
RUN chmod 755 /usr/local/bin/release-engine
ENTRYPOINT ["release-engine"]
