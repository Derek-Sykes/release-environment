#!/bin/sh
set -eu
export TMPDIR="$RELEASE_WORK_ROOT/_temp"
export VOICEVAULT_TEST_RUNNER="$(hostname)"
socket_gid="$(stat -c %g /var/run/docker.sock)"
socket_group="$(getent group "$socket_gid" | cut -d: -f1)"
if [ -z "$socket_group" ]; then
  groupadd --gid "$socket_gid" dockerhost
  socket_group=dockerhost
fi
usermod -aG "$socket_group" runner
mkdir -p "$TMPDIR"
chown runner:runner "$RELEASE_WORK_ROOT" "$TMPDIR"
cd /opt/runner
while [ ! -f .runner ]; do sleep 1; done
exec gosu runner ./run.sh
