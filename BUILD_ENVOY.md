## Build Envoy

Create a Bazel config to setup the Java truststore:

```sh
> user.bazelrc <<EOF
startup --host_jvm_args='-Dhttp.proxyHost=proxy.bloomberg.com'
startup --host_jvm_args='-Dhttps.proxyHost=proxy.bloomberg.com'
startup --host_jvm_args='-Dhttp.proxyPort=80'
startup --host_jvm_args='-Dhttps.proxyPort=80'
startup --host_jvm_args='-Dhttp.nonProxyHosts="localhost|127.*|[::1]|*.bloomberg.com"'
startup --host_jvm_args='-Djavax.net.ssl.trustStore=/source/clipKeystore'
startup --host_jvm_args='-Djavax.net.ssl.trustStorePassword=changeit'
EOF
```

Create a volume to hold build files:

```sh
docker volume create envoy-docker-build
```

Update the `STARTUP_COMMAND` in `./ci/run_envoy_docker.sh` to add the following line:

```
&& update-ca-certificates \
```

This ensure that Bloomberg's CA certificates are added to the OS's trusted CAs.


Launch the Envoy build container:

```sh
ENVOY_DOCKER_BUILD_DIR=envoy-docker-build \
ENVOY_DOCKER_OPTIONS="-v $HOME/bb-cert:/usr/local/share/ca-certificates" \
SSH_AUTH_SOCK="" \
/ci/run_envoy_docker.sh 'bash'
```

Run the build (inside the docker container):
```sh
BAZEL_OPTIONS='--spawn_strategy=standalone' ./ci/do_ci.sh dev
```
