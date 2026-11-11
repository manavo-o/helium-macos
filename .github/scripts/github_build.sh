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

# Functional UI changes require freshly compiled regressions before the browser
# target. Both compilation and execution share the existing phase deadline.
export SISO_PATH="${SISO_PATH:-$_siso_path}"
_validation_plan=$(python3 -c 'import json,pathlib,sys; p=pathlib.Path(sys.argv[1]); print(json.loads(p.read_text()).get("test_plan", "link-only") if p.is_file() else "link-only")' "$_root_dir/.github/arc-checkpoint-delta.json")

if [ "${XENON_FRESH_SOURCE:-}" = true ] && [ "$_validation_plan" != visual-only ]; then
    _validation_plan=xenon-native-v1
fi

phase_step() {
    _remaining_time=$(( 270*60 - $(date +%s) + epoch_job_start ))
    if [ "$_remaining_time" -le 0 ]; then
        return 124
    fi
    timeout -k 30s -s SIGTERM "${_remaining_time}s" "$@"
}

check_phase_result() {
    local phase_result="$1"
    if [ "$phase_result" -eq 124 ] || {
        [ "$phase_result" -eq 137 ] &&
        [ "$(( $(date +%s) - epoch_job_start ))" -ge "$((270*60))" ];
    }; then
        echo 'Phase deadline reached; retaining test/build outputs for continuation.'
        exit 0
    fi
    [ "$phase_result" -eq 0 ] || exit "$phase_result"
}

if [ "$_validation_plan" = xenon-native-v1 ]; then
    _test_check=0
    python3 "$_root_dir/.github/scripts/github_run_xenon_tests.py" \
        --arch "$_target_cpu" --check-stamp || _test_check=$?
    if [ "$_test_check" -eq 1 ]; then
        _test_result=0
        phase_step python3 "$_root_dir/.github/scripts/github_restore_xenon_test_inputs.py" || _test_result=$?
        check_phase_result "$_test_result"
        if [ "${XENON_FRESH_SOURCE:-}" = true ]; then
            phase_step python3 "$_depot_tools_dir/autoninja.py" -C "$_out_dir" \
                chrome/test/data/webui:build_grd || _test_result=$?
            check_phase_result "$_test_result"
        fi
        phase_step python3 "$_depot_tools_dir/autoninja.py" -C "$_out_dir" \
            browser_tests chrome/browser/ui/views/tabs/vertical:arc_routing_tests \
            ui/views:arc_bubble_lifecycle_tests || _test_result=$?
        check_phase_result "$_test_result"
        _test_result=0
        phase_step python3 "$_root_dir/.github/scripts/github_run_xenon_tests.py" \
            --arch "$_target_cpu" || _test_result=$?
        check_phase_result "$_test_result"
        python3 "$_root_dir/.github/scripts/github_run_xenon_tests.py" \
            --arch "$_target_cpu" --check-stamp
    elif [ "$_test_check" -ne 0 ]; then
        exit "$_test_check"
    fi
elif [ "$_validation_plan" = visual-only ]; then
    echo 'Browser-test compilation disabled by visual validation policy.'
    echo 'Visual acceptance remains pending in the GitHub-built macOS app.'
elif [ "$_validation_plan" != link-only ]; then
    echo "Unknown validation plan: $_validation_plan" >&2
    exit 1
fi

# Tests can consume part or all of the phase. Never grant a fresh full budget.
_remaining_time=$(( 270*60 - $(date +%s) + epoch_job_start ))
if [ "$_remaining_time" -le 0 ]; then
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

if [ "${XENON_FRESH_SOURCE:-}" = true ]; then
    _link_result=0
    phase_step python3 "$_root_dir/.github/scripts/github_check_arc_swift_link.py" || _link_result=$?
    check_phase_result "$_link_result"
fi

echo $(date +%s) | tee "$_root_dir/build_finished_$_target_cpu.log"
echo "status=finished" >> $GITHUB_OUTPUT
