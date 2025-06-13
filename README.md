# Envoy test

Start mock servers:

```sh
./run-mock-servers.sh
```

Start ext proc (not needed for QoS demo):

```
go run cmd/main.go
```

Start envoy:

```
envoy --config-path envoy-demo.yaml
```

Send a test request:

```
curl -d 'original payload' localhost:10000
```

## QoS

Make sure you have the Python mock servers running.

Start envoy with:

```sh
envoy --config-path envoy-demo-qos.yaml
```

### Priority 3

Simulate a P3 request where there is available capacity. This should get routed to `pt1`.

```
curl -H 'x-priority: p3' -d @payloads/request.json -H 'Content-type: application/json' -v localhost:10000
```

Simulate a P3 request where there is no available capacity. The request will get immediately rejected with `429`.

```
curl -H 'x-overloaded: 1' -H 'x-priority: p3' -d @payloads/request.json -H 'Content-type: application/json' -v localhost:10000
```

### Priority 2

Simulate a P2 request where there is available capacity. This should get routed to `pt1`.

```
curl -H 'x-priority: p2' -d @payloads/request.json -H 'Content-type: application/json' -v localhost:10000
```

Simulate a P2 request where there is no available capacity. This should get routed to `od1`. Note: we are not simulating the case where P2 traffic should be fully rejected.

```
curl -H 'x-overloaded: 1' -H 'x-priority: p2' -d @payloads/request.json -H 'Content-type: application/json' -v localhost:10000
```

### Priority 1

Simulate a P1 request. This will always get routed to `pt1` regardless of whether we are overloaded.

```
curl -H 'x-overloaded: 1' -H 'x-priority: p1' -d @payloads/request.json -H 'Content-type: application/json' -v localhost:10000
```

### Failover

The config is setup to do attempts in the order of `pt1` -> `pt2` -> `od1` when a `429` is encountered. Which backends actually get utilized depends on the priority level and overloaded status. See the `filter.lua` file for the logic.


Simulate failover to OD with P1 traffic:

```sh
curl -H 'x-priority: p1' -H 'x-response-code: pt1=429 pt2=429' -d @payloads/request.json -H 'Content-type: application/json' -v localhost:10000
```

If we change the priority to P3 this will fail as we are not allowed to use OD:

```sh
curl -H 'x-priority: p3' -H 'x-response-code: pt1=429 pt2=429' -d @payloads/request.json -H 'Content-type: application/json' -v localhost:10000
```
