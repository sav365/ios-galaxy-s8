# Dream2lte FTS transport diagnostic, 2026-11-12

Observed on Galaxy S8+: the working fts-fixed image reaches the iOS UI but user reports no touch response. Fresh raw-event image retains its boot args (debug=0xc serial=3 cpus=2 -noprogress, a5fb_noconsole=1, sweetfb_native=1, s8touch=2). Both CPUs initialized, SGI1 verified; SpringBoard executes.

The raw log prints 80 identical packets: `00 36 70 01 00 26 23 00`, matching the chip-ID response. No down/up events or I2C failures appear. This suggests stale data or command/transaction handling, but does not prove the cause. Do not shift event offsets based on this packet.

Patch 0125 is an experimental isolation test: reset the touch HSI2C controller before each complete FTS operation and trace the first 16 transaction FIFO/state snapshots. It preserves repeated START, event parsing and FTS initialization commands. It does not reset the touchscreen or write firmware, calibration or NVM. The battery bus and S6SY761 path are unchanged.

Validation: tooling source matches patch 0124; patch 0125 applies to that source with the XNU prefix; FTS snippet passes clang syntax with warnings treated as errors. Hardware result pending.

Next: build XNU, package using the exact working boot arguments, preserve BOOT, flash BOOT only, then collect events after physical taps. If the image fails to boot, restore the saved working BOOT. Current device is in TWRP at this handoff.

Local logs, images and checkpoint details are kept in the Codex chat outputs, outside git. Preserve the repository's pre-existing modifications.
