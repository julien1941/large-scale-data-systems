#!/bin/bash
echo "Simple script for testing. Launching every Raft Server in localhost, starting from port 8000"

correct_fraction=$1
flight_computers=$2

# Check args
if ! [ $1 ];
then
  correct_fraction=1.0
fi

if ! [ $2 ];
then
  flight_computers=2
fi

port=8000
host="127.0.0.1"
echo "" > pid.txt 2>&1

for i in `seq 1 $flight_computers`;
do
  let "current_port = port + i"
  python flask_raft.py  --port $current_port --host $host &
  echo "processus pid $!" >> pid.txt 2>&1
done
