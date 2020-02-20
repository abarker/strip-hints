#!/bin/bash

STRIP="python ../bin/strip_hints.py"
testfiles="really_simple_test.py simple_test.py testfile_strip_hints.py testfile_strip_classes.py"

echo "These tests pass if there is no diff output between calculated and saved results."
echo

for testfile in $testfiles
do
   echo "============ $testfile ======================================"

   $STRIP $testfile > tmp.results
   diff $testfile.results tmp.results
   rm tmp.results
done

echo
echo "These tests pass if all the runs say they are identical."
echo

for testfile in $testfiles
do
   echo "============ $testfile ======================================"
   python run_strip_from_string_test.py $testfile
done

