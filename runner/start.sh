#!/bin/sh
set -eu
mkdir -p "$TMPDIR"
chown -R runner:runner /opt/runner/_work
cd /opt/runner
while [ ! -f .runner ]; do sleep 1; done
exec gosu runner ./run.sh
