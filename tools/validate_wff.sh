#!/bin/sh
set -eu
: "${WFF_VALIDATOR_JAR:?Set WFF_VALIDATOR_JAR (see SETUP.md)}"
: "${WFF_MEMORY_JAR:?Set WFF_MEMORY_JAR (see SETUP.md)}"
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
# The pinned validator can report an invalid schema with exit status zero.
report=$(java -jar "$WFF_VALIDATOR_JAR" 4 "$root/watchface/build/generated/daliclock/res/raw/watchface.xml" 2>&1)
printf '%s\n' "$report"
case "$report" in *'PASSED :'*) ;; *) exit 1 ;; esac
for artifact in "$root/watchface/build/outputs/apk/debug/watchface-debug.apk" "$root/watchface/build/outputs/bundle/release/watchface-release.aab"; do
    report=$(java -jar "$WFF_MEMORY_JAR" --watch-face "$artifact" --schema-version 4 \
        --ambient-limit-mb 10 --active-limit-mb 100 \
        --apply-v1-offload-limitations --estimate-optimization 2>&1)
    printf '%s\n' "$report"
    case "$report" in *'Watch Face has passed the memory footprint test.'*) ;; *) exit 1 ;; esac
done
