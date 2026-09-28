#!/usr/bin/env sh
# Build the dataset, fine-tune Laya on one GPU and evaluate it against the rule coder.
#   scorer/training/train.sh [version] [path/to/training.jsonl exported from /admin]
# Output: models/inkspect-laya-<version>/ (checkpoint) and models/laya-data-<version>/ (dataset + report).
set -eu
VERSION=${1:-v1}
OVERRIDES=${2:-}
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
BASE_REPO=convaiinnovations/laya
IMAGE=inkspect-laya-train
GPU=${GPU:-0}

docker build -q -t $IMAGE "$ROOT/scorer/training" >/dev/null
RUN="docker run --rm --gpus device=$GPU -u $(id -u):$(id -g) -e HOME=/tmp \
  -v ${HF_CACHE:-$HOME/.cache/inkspect-hf}:/cache/huggingface -v $ROOT:/work -w /work/scorer/training $IMAGE"

BASE=$($RUN python -c "from huggingface_hub import snapshot_download as s; \
print(s('$BASE_REPO', allow_patterns=['typed-decisions/*', 'typed-decisions/**']) + '/typed-decisions')" | tail -1)

EXTRA=""
if [ -n "$OVERRIDES" ]; then
  cp "$OVERRIDES" "$ROOT/models/overrides-$VERSION.jsonl"
  EXTRA="--overrides /work/models/overrides-$VERSION.jsonl"
fi
$RUN python build_dataset.py --out /work/models/laya-data-$VERSION $EXTRA
$RUN python finetune.py --data /work/models/laya-data-$VERSION --base "$BASE" --out /work/models/inkspect-laya-$VERSION
$RUN python evaluate.py --data /work/models/laya-data-$VERSION/val.jsonl /work/models/laya-data-$VERSION/test.jsonl \
  --checkpoint "base=$BASE" --checkpoint "fine-tuned=/work/models/inkspect-laya-$VERSION" \
  --out /work/models/laya-data-$VERSION/report.json | tee "$ROOT/models/laya-data-$VERSION/report.md"
