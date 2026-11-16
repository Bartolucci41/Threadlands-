#!/usr/bin/env bash
# Copy map data to the Threadlands data store (Cloudflare R2). Needs R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY.
# Usage: pipeline/r2_sync.sh detail            (all block-level detail)
#        pipeline/r2_sync.sh detail/mexico-city (one place)
set -euo pipefail
if [ -z "${R2_ENDPOINT:-}" ] || [ -z "${R2_ACCESS_KEY_ID:-}" ]; then echo "R2 is not set up yet; skipping the upload."; exit 0; fi
export AWS_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID" AWS_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY" AWS_DEFAULT_REGION=auto
BUCKET="${R2_BUCKET:-threadlands-data}"
for p in "$@"; do
  [ -d "data/$p" ] || { echo "no data/$p"; continue; }
  aws s3 sync "data/$p" "s3://$BUCKET/$p" --endpoint-url "$R2_ENDPOINT" --size-only --no-progress \
    --content-type application/json --cache-control "public, max-age=3600"
  echo "Uploaded data/$p to R2."
done
