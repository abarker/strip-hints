#!/bin/bash
#
# Usage: strip_and_colordiff.bash [<pythonFile> [<pythonfile> ...]] | more

STRIP_HINTS="$(dirname "$0")/../src/strip_hints/strip_hints.py"
PYTHON="python3"
CONTEXT_LINES=500

for i in "$@"
do
   echo
   echo "===== Running for file '$i' --========================================="
   diff --unified=$CONTEXT_LINES $i <($PYTHON $STRIP_HINTS $i) | colordiff
   echo "===== Finished with file '$i' ========================================="
   echo
   #echo -n "Hit enter to continue: "
   #read waitvar
done

