#!/bin/sh
set -eu
: "${WFF_VALIDATOR_JAR:?Set WFF_VALIDATOR_JAR (see SETUP.md)}"
: "${WFF_MEMORY_JAR:?Set WFF_MEMORY_JAR (see SETUP.md)}"
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
java -jar "$WFF_VALIDATOR_JAR" 4 "$root/watchface/build/generated/melt/res/raw/watchface.xml"
for artifact in "$root/watchface/build/outputs/apk/debug/watchface-debug.apk" "$root/watchface/build/outputs/bundle/release/watchface-release.aab"; do
    java -jar "$WFF_MEMORY_JAR" --watch-face "$artifact" --schema-version 4 \
        --ambient-limit-mb 10 --active-limit-mb 100 \
        --apply-v1-offload-limitations --estimate-optimization
done
