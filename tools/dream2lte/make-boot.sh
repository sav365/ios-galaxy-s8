#!/usr/bin/env bash
# Galaxy S8+ Exynos first-stage XNU bring-up image. NEVER flashes anything.
set -euo pipefail
repo=$(cd "$(dirname "$0")/../.." && pwd)
if (( $# < 3 )); then
  echo "Usage: $0 XNU_KERNEL STOCK_G955F_BOOT.img OUT.img [boot-args...]" >&2
  exit 2
fi
stock=$(realpath "$2")
out=$(realpath -m "$3")
if [[ "$stock" == "$out" ]]; then
  echo "ERROR: output would overwrite the stock BOOT backup" >&2
  exit 2
fi
python3 "$repo/tools/dream2lte/validate-stock-boot.py" "$stock"
# An initial debug build deliberately does not mount or overwrite USERDATA.
# The resulting loader still needs actual G955F validation before a flash.
if (( $# == 3 )); then
  set -- "$1" "$2" "$3" \
    debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam \
    -noprogress wdt=-1 wdt_test=no_user_checkin \
    a5touchprobe=0 sweetfb_native=1
fi
S8_DEVICE=dream2lte bash "$repo/tools/dreamlte/make-boot.sh" "$@"
echo "S8+ image built for experimental bring-up ONLY. Not flashed."
