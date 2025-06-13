#!/bin/bash
pids=()
names=(pt1 pt2 od1)
ports=(3000 3001 3002)
return_codes=(200 200 200)

for i in ${!names[@]}; do
  echo "Starting ${names[$i]} on port ${ports[$i]}"
  python3.12 server/main.py --name ${names[$i]} --port ${ports[$i]} --return-code ${return_codes[$i]} &
  pids[${i}]=$!
done

# kill children before we go
trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT

# wait for all pids
for pid in ${pids[*]}; do
    wait $pid
done
