#!/usr/bin/env bash
# Run a full local code-review pipeline: tests, extractors, validators, linters, and metrics.
#
# Usage:
#   bash scripts/dev/run_code_review.sh
#   OR make it executable and run:
#   ./scripts/dev/run_code_review.sh
#
# The script:
# - Creates/uses a virtualenv at .venv (inside repo)
# - Installs required dependencies (from scripts/_ia/requirements.txt when present)
# - Runs pytest, extractors, validators, linters and static analyzers
# - Writes per-step logs to scripts/_ia/logs/
# - Prints and writes a summary report (scripts/_ia/logs/summary.json)
#
# Exit codes:
#  0 = all critical checks passed
#  1 = one or more critical checks failed (tests or validators)
#  2 = critical checks passed but non-critical checks failed (linters/metrics)
#  3 = fatal error setting up environment / preconditions
#
# Notes:
# - Run this from the repository root (script will attempt to detect repo root).
# - The script runs all commands non-interactively and captures stdout/stderr to log files.
# - You can inspect logs in scripts/_ia/logs/ if something fails.

set -u

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$REPO_ROOT" ]; then
  echo "[ERROR] Not a git repository or git not available. Run this script from inside a git repo."
  exit 3
fi
cd "$REPO_ROOT" || exit 3

VENV_DIR=".venv"
LOG_DIR="scripts/_ia/logs"
mkdir -p "$LOG_DIR"

TIMESTAMP() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

# Tracking
declare -A STEP_STATUS
declare -A STEP_CODE
declare -A STEP_LOG

OVERALL_CRITICAL_FAILED=0
OVERALL_NONCRITICAL_FAILED=0

run_step() {
  # run_step "<id>" "<label>" "<critical: yes|no>" "<command...>"
  local id="$1"; shift
  local label="$1"; shift
  local critical="$1"; shift
  local logfile="$LOG_DIR/${id}.log"
  STEP_LOG["$id"]="$logfile"

  echo "----"
  echo "[$(TIMESTAMP)] Running step: $label"
  echo "[$(TIMESTAMP)] Command: $*"
  echo "[$(TIMESTAMP)] Logging to: $logfile"
  echo "[$(TIMESTAMP)] START $label" >"$logfile"

  # Execute the command; capture exit code
  # Use a subshell so environment changes inside command do not leak
  (
    set -o pipefail
    "$@" 2>&1
  ) | tee -a "$logfile"
  local code=${PIPESTATUS[0]:-$?}

  if [ "$code" -eq 0 ]; then
    STEP_STATUS["$id"]="PASS"
  else
    STEP_STATUS["$id"]="FAIL"
    STEP_CODE["$id"]="$code"
    if [ "$critical" = "yes" ]; then
      OVERALL_CRITICAL_FAILED=1
    else
      OVERALL_NONCRITICAL_FAILED=1
    fi
  fi

  echo "[$(TIMESTAMP)] END $label (code=$code)" | tee -a "$logfile"
  echo
  return $code
}

echo "=== Local Code Review Script ==="
echo "Repo root: $REPO_ROOT"
echo "Logs dir : $LOG_DIR"
echo "Timestamp: $(TIMESTAMP)"
echo

# 1) Basic repo checks (non-critical)
run_step "00_repo_info" "Repo info & branch" "no" bash -lc "git status --porcelain; echo; git rev-parse --abbrev-ref HEAD; echo; git --no-pager log -n3 --oneline"

# 2) Create / activate venv and install deps (critical)
if [ ! -d "$VENV_DIR" ]; then
  echo "[INFO] Creating virtualenv at $VENV_DIR"
  python -m venv "$VENV_DIR" 2>/dev/null || { echo "[ERROR] Failed creating venv"; exit 3; }
fi

# Activate venv in this script
# shellcheck source=/dev/null
. "$VENV_DIR/bin/activate"

# Upgrade pip
run_step "01_pip_upgrade" "Upgrade pip" "no" python -m pip install --upgrade pip

# Install requirements if exists, otherwise minimal set
if [ -f "scripts/_ia/requirements.txt" ]; then
  run_step "02_install_reqs" "Install project IA requirements" "yes" python -m pip install -r scripts/_ia/requirements.txt
else
  run_step "02_install_reqs" "Install minimal requirements (PyYAML, jsonschema, pytest...)" "yes" python -m pip install PyYAML>=6.0.1 jsonschema>=4.21.0 pytest radon lizard flake8 black isort mypy bandit coverage || true
fi

# Ensure some tooling is present (best-effort)
run_step "02b_install_extra" "Install recommended tools (radon, lizard, bandit)" "no" python -m pip install radon lizard bandit || true

# 3) Run pytest (critical)
run_step "10_pytest" "Run pytest" "yes" pytest -q

# 4) Run extractors / generators (non-critical but needed for validators)
# Primary extractor for quality gates
run_step "20_extractor_quality" "Extractor: extract-quality-gates" "yes" python scripts/_ia/extractors/extract-quality-gates.py --output docs/_ai/_specs/quality-gates.yml --allow-fallback

# Additional generators (non-critical)
run_step "21_generator_handshake" "Generator: handshake template" "no" python scripts/_ia/generators/generate-handshake-template.py || true
run_step "22_generator_invocation" "Generator: invocation-examples" "no" python scripts/_ia/generators/generate-invocation-examples.py || true
run_step "23_generator_checklist" "Generator: checklist-models" "no" python scripts/_ia/generators/generate-checklist-yml.py || true

# 5) Schema validation (critical)
run_step "30_validate_schema" "Validate quality-gates schema" "yes" python scripts/_ia/validators/validate-quality-gates-schema.py

# 6) Run quality gates validator (critical if you want to enforce)
run_step "31_validate_quality_gates" "Validate quality gates (radon/lizard checks)" "yes" python scripts/_ia/validators/validate-quality-gates.py || true

# 7) Validate approved commands (critical)
run_step "32_validate_approved" "Validate approved commands (whitelist)" "yes" python scripts/_ia/validators/validate-approved-commands.py || true

# 8) Linters / formatters / static analysis (non-critical)
run_step "40_black" "Black formatting check" "no" black --check . || true
run_step "41_isort" "isort check" "no" isort --check-only . || true
run_step "42_flake8" "flake8 lint" "no" flake8 || true
run_step "43_mypy" "mypy type check" "no" mypy . || true

# 9) Complexity metrics (non-critical)
run_step "50_radon" "radon cc - average complexity" "no" bash -lc 'radon cc -s -a .' || true
run_step "51_lizard" "lizard complexity" "no" lizard . || true

# 10) Security scan (non-critical)
run_step "60_bandit" "bandit security scan" "no" bandit -r . -q || true

# Build summary
SUMMARY_FILE="$LOG_DIR/summary.json"
echo "{" > "$SUMMARY_FILE"
echo "  \"generated_at\": \"$(TIMESTAMP)\"," >> "$SUMMARY_FILE"
echo "  \"results\": {" >> "$SUMMARY_FILE"

first=true
for id in "${!STEP_STATUS[@]}"; do
  if [ "$first" = true ]; then
    first=false
  else
    echo "," >> "$SUMMARY_FILE"
  fi
  status="${STEP_STATUS[$id]}"
  code="${STEP_CODE[$id]:-0}"
  log="${STEP_LOG[$id]}"
  echo -n "    \"${id}\": { \"status\": \"${status}\", \"code\": ${code}, \"log\": \"${log}\" }" >> "$SUMMARY_FILE"
done

echo "" >> "$SUMMARY_FILE"
echo "  }" >> "$SUMMARY_FILE"
echo "}" >> "$SUMMARY_FILE"

# Print summary to stdout (human readable)
echo
echo "=== SUMMARY ==="
printf "%-6s %-60s %6s %10s\n" "STEP" "DESCRIPTION" "CODE" "STATUS"
echo "-----------------------------------------------------------------------------------------"
# Print in a predictable order by reading log files created earlier
for id in $(ls "$LOG_DIR"/*.log 2>/dev/null | sed -e "s@.*/@@g" -e "s/.log$//g" | sort); do
  label="$id"
  status="${STEP_STATUS[$id]:-SKIP}"
  code="${STEP_CODE[$id]:-0}"
  printf "%-6s %-60s %6s %10s\n" "$id" "$label" "$code" "$status"
done

echo
if [ "$OVERALL_CRITICAL_FAILED" -eq 1 ]; then
  echo "[RESULT] One or more CRITICAL checks failed. See logs in $LOG_DIR for details."
  exit 1
elif [ "$OVERALL_NONCRITICAL_FAILED" -eq 1 ]; then
  echo "[RESULT] Critical checks passed, but some non-critical checks failed. See logs in $LOG_DIR."
  exit 2
else
  echo "[RESULT] All critical checks passed. Non-critical checks also passed."
  exit 0
fi