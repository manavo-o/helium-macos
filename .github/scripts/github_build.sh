#!/bin/bash -eux

# Build one CI phase, leaving time to upload a checkpoint before the job limit.

_target_cpu="${1:-x86_64}"

_root_dir="$(dirname "$(greadlink -f "$0")")"
source "$_root_dir/devutils/shared.sh"
epoch_job_start=$(cat "$_root_dir/epoch_job_start.txt")
# Stop compilation at 4h30 elapsed, leaving 90 minutes for checkpoint packing,
# signing and uploads. Setup and preflight time count against this deadline.
_remaining_time=$(( 270*60 - $(date +%s) + epoch_job_start ))

cd "$_src_dir"

echo $(date +%s) | tee -a "$_root_dir/build_times_$_target_cpu.log"
echo "status=running" >> $GITHUB_OUTPUT

if ! env | grep -q SCCACHE; then
    export SCCACHE_GHA_ENABLED=on
    export SCCACHE_GHA_VERSION="$_target_cpu"
fi

export SCCACHE_WEBDAV_KEY_PREFIX="$_target_cpu"

if [ "$_remaining_time" -le 0 ]; then
    echo 'Compile deadline reached; saving the checkpoint for the next phase.'
    exit 0
fi

_error_code=0
export SISO_PATH="${SISO_PATH:-$_siso_path}"
# This artifact is the browser and its installer; ChromeDriver is not packaged.
timeout -k 30s -s SIGTERM "${_remaining_time}s" \
    python3 "$_depot_tools_dir/autoninja.py" -C "$_out_dir" \
    chrome chrome/installer/mac || _error_code=$?

if [ "$_error_code" -eq 124 ] || {
    [ "$_error_code" -eq 137 ] &&
    [ "$(( $(date +%s) - epoch_job_start ))" -ge "$((270*60))" ];
}; then
    exit 0
fi
[ "$_error_code" -ne 0 ] && exit "$_error_code"

echo $(date +%s) | tee "$_root_dir/build_finished_$_target_cpu.log"
echo "status=finished" >> $GITHUB_OUTPUT
