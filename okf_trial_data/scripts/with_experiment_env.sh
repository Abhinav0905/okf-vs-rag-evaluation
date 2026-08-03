#!/usr/bin/env bash
# Run an experiment command with the correct environment.
#
# Why this wrapper exists
# -----------------------
# The shared project .env supplies AWS credentials, but it also sets DB_HOST,
# DB_PORT, DB_NAME, DB_USERNAME and DB_PASSWORD for an unrelated application
# database (wmp_cris on port 5432). The evaluation harness reads those same
# variable names, so sourcing .env silently points the retriever at the wrong
# database -- or, as of this writing, at one that does not exist.
#
# The evaluation corpus lives in `wmp_eval` on port 5433 (the pgvector container
# started by eval_harness/scripts/start_pgvector.sh). eval_config.yaml already
# declares those as defaults, so the fix is simply to remove the overrides after
# loading credentials.
#
# Usage:
#   scripts/with_experiment_env.sh .venv/bin/python scripts/run_generation.py ...
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Parse .env rather than sourcing it. The file contains at least one entry whose
# key is not a valid shell identifier (hyphens), which `source` would try to
# execute as a command. Only well-formed KEY=VALUE lines are exported, and
# surrounding quotes are stripped.
if [[ -f "${REPO_ROOT}/.env" ]]; then
  while IFS= read -r line || [[ -n "${line}" ]]; do
    [[ "${line}" =~ ^[[:space:]]*# ]] && continue
    [[ "${line}" =~ ^[[:space:]]*$ ]] && continue
    line="${line#export }"
    key="${line%%=*}"
    value="${line#*=}"
    [[ "${key}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
    value="${value%\"}"; value="${value#\"}"
    value="${value%\'}"; value="${value#\'}"
    export "${key}=${value}"
  done < "${REPO_ROOT}/.env"
fi

# Credentials are often pasted using the AWS credentials-file convention, which
# is lowercase (aws_access_key_id). boto3 only reads the uppercase environment
# variables, so a lowercase paste looks like "no credentials at all". Promote
# them, without overwriting an uppercase value that is already set.
for lower in aws_access_key_id aws_secret_access_key aws_session_token; do
  upper="$(printf '%s' "${lower}" | tr '[:lower:]' '[:upper:]')"
  lower_value="$(eval "printf '%s' \"\${${lower}:-}\"")"
  upper_value="$(eval "printf '%s' \"\${${upper}:-}\"")"
  if [[ -n "${lower_value}" && -z "${upper_value}" ]]; then
    export "${upper}=${lower_value}"
  fi
done

# Drop the application database overrides so eval_config.yaml defaults apply
# (localhost:5433, database wmp_eval, table wmp_chunks).
unset DB_HOST DB_PORT DB_NAME DB_USERNAME DB_PASSWORD

# Local sentence-transformers and cross-encoder models run on CPU for
# reproducible latency; override by exporting EVAL_DEVICE before this script.
export EVAL_DEVICE="${EVAL_DEVICE:-cpu}"
export AWS_REGION="${AWS_REGION:-us-west-2}"
# Keep tokenizer threading deterministic so latency records are comparable.
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"

if [[ -z "${AWS_ACCESS_KEY_ID:-}" ]]; then
  echo "with_experiment_env.sh: AWS credentials are not set; live runs will fail." >&2
fi

exec "$@"
