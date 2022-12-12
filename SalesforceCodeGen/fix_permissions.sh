#!/bin/bash

declare -a Folders=(
    "/home/t-haghakhani/codegen/backpropagation"
    "/storage/results"
    "/storage/resultsForPaper"
)

for f in ${Folders[@]}; do
    echo "Fixing permissions of $f..."
    chown -R REDMOND.t-haghakhani:REDMOND.domain\ users $f
    chmod go+rw $f
    find $f -type d -print0 | xargs -0 chmod go+rwx
    find $f -type f -print0 | xargs -0 chmod go+rw
    echo "Done."
done
