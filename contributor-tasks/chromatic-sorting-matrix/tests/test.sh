#!/usr/bin/env bash

set -uo pipefail

TESTS_DIR="/tests"
SCORE_FILE="${TESTS_DIR}/score.txt"
REWARD_DIR="/logs/verifier"
REWARD_FILE="${REWARD_DIR}/reward.txt"

mkdir -p "${REWARD_DIR}"
echo "0" > "${REWARD_FILE}"
rm -f "${SCORE_FILE}"

pip install --quiet --no-cache-dir pytest==8.2.2 2>/dev/null || \
pip install --quiet --no-cache-dir --break-system-packages pytest==8.2.2

bash /solution/solve.sh

pytest "${TESTS_DIR}/test_outputs.py" -v -s --tb=short --no-header || true

if [[ -f "${SCORE_FILE}" ]]; then
    SCORE=$(cat "${SCORE_FILE}")
    python3 -c "
score = float('${SCORE}')
reward = round(score / 100.0, 4)
with open('${REWARD_FILE}', 'w') as f:
    f.write(str(reward))
"
fi