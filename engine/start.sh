#!/bin/sh
set -eu
# Docker's loopback DNS resolver is not reachable from a nested build container.
# Relay through this engine's network address to the actual host/VPN resolver;
# do not substitute public DNS or persist a machine-specific resolver in source.
engine_address="$(hostname -i | awk '{print $1}')"
set --
for resolver in $(awk '$1 == "nameserver" {print $2}' /etc/resolv.conf); do
    set -- "$@" "--server=$resolver"
done
[ "$#" -gt 0 ] || { echo 'No host DNS resolver available.' >&2; exit 1; }
dnsmasq --no-daemon --no-resolv --no-hosts --bind-interfaces \
    --listen-address="$engine_address" --user=root --pid-file=/tmp/release-dns.pid "$@" &
exec dockerd-entrypoint.sh dockerd --host=unix:///var/run/docker.sock \
    --host=tcp://127.0.0.1:2375 --tls=false --dns="$engine_address"
