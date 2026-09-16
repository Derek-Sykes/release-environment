FROM docker:28-cli@sha256:cd58b396e427d1ee8cddcc3f3b7e8d8c2ba45755c5dd5b821b6e615e1ccf4586 AS dockercli
FROM mcr.microsoft.com/dotnet/runtime-deps:8.0-noble@sha256:55cde4ac72e935f8a1ac5bd34f900127e6983d420be979a4b407d59ae17f883e
ARG RUNNER_VERSION=2.337.0
ARG RUNNER_SHA256=70920811a4f8ad4328818682bca5c6469c1c942fab52448868071d0063816613
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git python3 ripgrep sudo tini gosu \
    && rm -rf /var/lib/apt/lists/*
RUN usermod --login runner --home /home/runner --move-home ubuntu \
    && groupmod --new-name runner ubuntu \
    && mkdir -p /opt/runner/_work \
    && chown -R runner:runner /opt/runner /home/runner
COPY --from=dockercli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=dockercli /usr/local/libexec/docker/cli-plugins /usr/local/libexec/docker/cli-plugins
WORKDIR /opt/runner
RUN curl --fail --location --silent --show-error \
    "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz" \
    --output /tmp/runner.tar.gz \
    && printf '%s  /tmp/runner.tar.gz\n' "$RUNNER_SHA256" | sha256sum --check \
    && tar xzf /tmp/runner.tar.gz && rm /tmp/runner.tar.gz \
    && chown -R runner:runner /opt/runner
COPY start.sh /usr/local/bin/start-runner
RUN chmod 755 /usr/local/bin/start-runner
ENV HOME=/home/runner RUNNER_MANUALLY_TRAP_SIG=1 DOCKER_HOST=unix:///var/run/docker.sock
ENTRYPOINT ["tini", "--", "/usr/local/bin/start-runner"]
