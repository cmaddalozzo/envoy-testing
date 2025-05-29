# Envoy test

Start mock servers:

```
python3.12 server/main.py --port 3000 --return-code 429 &
python3.12 server/main.py --port 3001 --return-code 429 &
python3.12 server/main.py --port 3002 --return-code 200 &
```

Start ext proc:

```
go run cmd/main.go
```

Start envoy:

```
envoy --config-path envoy-demo.yaml --component-log-level "ext_proc:debug"
```

Send a test request:

```
curl -d 'original payload' localhost:10000
```
