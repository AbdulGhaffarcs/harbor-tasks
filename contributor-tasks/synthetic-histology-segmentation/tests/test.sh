#!/bin/bash
set -uo pipefail
TESTS_DIR="/tests"
SCORE_FILE="${TESTS_DIR}/score.txt"
REWARD_DIR="/logs/verifier"
REWARD_FILE="${REWARD_DIR}/reward.txt"
mkdir -p "${REWARD_DIR}"
echo "0" > "${REWARD_FILE}"
rm -f "${SCORE_FILE}"
pip install --quiet --no-cache-dir \
    pytest==8.2.2 scikit-image==0.22.0 scipy==1.13.0 \
    Pillow==10.3.0 numpy==1.26.4 2>/dev/null || \
pip install --quiet --no-cache-dir --break-system-packages \
    pytest==8.2.2 scikit-image==0.22.0 scipy==1.13.0 \
    Pillow==10.3.0 numpy==1.26.4
pytest "${TESTS_DIR}/test_outputs.py" -v -s --tb=short --no-header || true
if [[ ! -f "${SCORE_FILE}" ]]; then
    echo "0" > "${REWARD_FILE}"; echo "REWARD=0.0"; exit 0
fi
SCORE=$(cat "${SCORE_FILE}")
python3 -c "
s=float('${SCORE}')
r=round(s/100,4)
open('${REWARD_FILE}','w').write(str(r))
print(f'REWARD={r}')
"
