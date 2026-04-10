#!/usr/bin/env bash
# tests/test.sh

set -uo pipefail

TESTS_DIR="/tests"
SCORE_FILE="${TESTS_DIR}/score.txt"
REWARD_DIR="/logs/verifier"
REWARD_FILE="${REWARD_DIR}/reward.txt"

mkdir -p "${REWARD_DIR}"
echo "0" > "${REWARD_FILE}"
rm -f "${SCORE_FILE}"

echo "=== Installing test dependencies ==="
pip install --quiet --no-cache-dir pytest==8.2.2 2>/dev/null || \
pip install --quiet --no-cache-dir --break-system-packages pytest==8.2.2

echo "=== Generating Ground Truth ==="
bash /solution/solve.sh

echo "=== Running test suite ==="
pytest "${TESTS_DIR}/test_outputs.py" -v -s --tb=short --no-header || true

echo "=== Computing reward ==="
if [[ ! -f "${SCORE_FILE}" ]]; then
    echo "score.txt not written — scoring test did not run"
    echo "0" > "${REWARD_FILE}"
    exit 0
fi

SCORE=$(cat "${SCORE_FILE}")

python3 -c "
score = float('${SCORE}')
reward = round(score / 100.0, 4)
print(f'Score: {score:.2f}/100  ->  Reward: {reward}')
with open('${REWARD_FILE}', 'w') as f:
    f.write(str(reward))
print(f'Written to ${REWARD_FILE}')
"