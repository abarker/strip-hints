#!/bin/bash
#
# Usage: strip_and_colordiff.bash [<pythonFile> [<pythonfile> ...]] | more

STRIP_HINTS="$(dirname "$0")/../bin/strip_hints.py"

# Python2 tests stripping better, since the AST of otherwise valid code with
# hints raises an error.  But the rest of the code obviously must be valid
# Python2 code for the AST to ever work.
#PYTHON="python2"
PYTHON="python3"
echo "Running strip_and_colordiff.bash with this Python command: '$PYTHON'"

CONTEXT_LINES=500
#STRIP_HINTS_ARGS="--to-empty"
#STRIP_HINTS_ARGS="--no-ast"
#STRIP_HINTS_ARGS="--only-assigns-and-defs"

TMPFILE="/tmp/test_strip_hints_xxxxx.py"

for i in "$@"
do
   echo
   echo "===== Running for file '$i' --========================================="
   diff --unified=$CONTEXT_LINES $i <($PYTHON $STRIP_HINTS $STRIP_HINTS_ARGS $i) | colordiff
   #$PYTHON $STRIP_HINTS $STRIP_HINTS_ARGS $i >$TMPFILE
   #vimdiff $i $TMPFILE
   echo "===== Finished with file '$i' ========================================="
   echo
   #echo -n "Hit enter to continue: "
   #read waitvar
done

