#!/bin/bash
#
# Just run the script with no arguments from the test directory.

# This picks up whatever Python is set in the virtualenv.  Explicitly change it
# to test other versions.
STRIP="python3.7 ../bin/strip_hints.py"

testfiles="really_simple_test.py
           simple_test.py
           testfile_strip_hints.py
           testfile_strip_classes.py
           test_NL_in_annotated_assigns_and_decls.py"

echo
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

