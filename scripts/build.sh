#!/bin/bash
handle_error() {
    msg="Error [$1] occured on command [$2: $3]"
    echo "$msg" >&2
    echo >&2
    echo "Fatal error" >&2
    exit 1
}
set -E # the ERR trap is inherited by shell functions
trap 'handle_error "$?" "$LINENO" "$(eval echo "$BASH_COMMAND")"' ERR

set -x

root="$(realpath "$(dirname "$0")/..")"
mkdir -p "$root/build"
rm -rf "$root/build"/*
cp -r "$root/src"/* "$root/build/"
cp "$root/docker/Dockerfile" "$root/build/"

cd "$root/build"
docker build -t osc2mqtt:latest .
docker tag osc2mqtt:latest osc2mqtt:$(date +"%y%m%d")_$(git rev-parse --short HEAD)
