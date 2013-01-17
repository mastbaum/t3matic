#!/bin/bash

# sets up the environment, sets maximum data size to 2 GB, then
# runs the argument.

RAT_BIN=`dirname $1`
source $RAT_BIN/../env.sh
ulimit -d 2000000
exec "$@"

