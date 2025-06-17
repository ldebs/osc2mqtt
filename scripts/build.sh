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
cp -r "$root/src"/* "$root/build/"
cp "$root/docker/Dockerfile" "$root/build/"
cp -r "$root/config" "$root/build/"

cd "$root/build"
docker build -t osc2mqtt .
docker tag ldebs/osc2mqtt:latest ldebs/osc2mqtt:$(date +"%y%m%d")_$(git rev-parse --short HEAD)
