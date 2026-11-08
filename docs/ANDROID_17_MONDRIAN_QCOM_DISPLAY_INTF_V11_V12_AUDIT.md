# Stage 192 — Qualcomm display-commonsys-intf / AOSP 17 / mondrian

**2026-11-08. Device: POCO F5 Pro / Redmi K60 (mondrian, SM8475).**
**Result:** audit the 2024 archive, preserve it unchanged, and DO NOT import its old HIDL packaging or incomplete AIDL provider graph into the active pure AOSP17 ROM.

## 1. Historical source and what previous developers implemented

- Archive: https://github.com/PixelExperience-Reborn/vendor_qcom_opensource_commonsys-intf_display
- Historical seventeen HEAD: f75571a9d6947c4dc70f3e5138a0cd3df4302c71, commit 2024-01-04, Git source tree 8521ced92d33ee88e25393d4c8dd74426e05cc62. The commit merged Qualcomm/CLO tag LA.QSSI.14.0.r1-11200-qssi.0 into Lineage 21.0, with changes for idle content FPS, tracked-layer refresh voting and private gralloc dequeue-duration metadata. This is a Qualcomm interface archive, **not** a modern AOSP17 device-ready service.
- Real in-tree Soong module in root Android.bp: display_intf_headers (cc_library_headers, vendor_available). Its defaults refer to external GRALLOC_HANDLE_HAS_* compile flags, so correctness depends on the matching mapper/allocator/buffer handle layout.
- Several VINTF-stable AIDL contracts are present. Qualcomm display.config is frozen at V1..V11; Qualcomm composer3 extension is V1 with import android.hardware.graphics.composer3-V2; color, demura and postproc provide V1 interfaces. The extension IQtiComposer3Client is **not** the platform android.hardware.graphics.composer3.IComposer service.
- The tree also retains HIDL-era gralloc private handle types, GRALLOC1, packed native_handle_t, compositor extension C++ interfaces, and system/vendor product templates. It does **not** contain an entire HWC3 Composer/Allocator service, SDM implementation or SDE DRM source.
- Original product makefiles include vendor.display.config@1.x/@2.0, vendor.qti.hardware.display.composer@1.0/@2.0, vendor.qti.hardware.display.mapper@1.0..4.0 alongside composer3-V1-ndk; they list vendor.qti.hardware.display.config-V1..V10-ndk, **but not V11**, even though the AIDL contract has frozen V11. This is a static producer/packaging mismatch; not a demonstrated runtime failure.

## 2. Exact modern-source comparison: why this archive cannot simply be enabled

- Existing nondefault AOSP17 display-source candidate is Sony-hosted Qualcomm-derived hardware-qcom-display, pinned to baf61f736e2109522e3f72754ee7cfacbfa2dc6c (branch aosp/DISPLAY.LA.5.0.r1). It is not a known matching Xiaomi vendor HAL.
- Its composer/Android.bp requires **vendor.qti.hardware.display.config-V12-ndk** and **vendor.qti.hardware.display.aiqe-V2-ndk**, and has distinct HWC3 Composer AIDL V2/V3 paths.
- The 2024 PE interface archive offers display.config only through **V11** and no in-tree aiqe interface. Adding it cannot satisfy the V12/AIQE dependencies. Mixing the two archives without auditing the exact module providers risks unresolved modules, duplicate AIDL names, conflicting VINTF interfaces, or incorrect Qualcomm private gralloc metadata layouts.
- AOSP17 platform hardware/interfaces source remains the authority for stable Android graphics interfaces. A platform Composer3 V5 definition does not mean an older vendor implementation automatically supplies V5.
- Newer is not a sufficient reason to deploy a graphics stack. We prioritize independently pinned, compatible and appropriately frozen AIDL versions, and use HWC3/Stable-C where validated. Under AOSP Stable AIDL policy, do not hand-edit frozen snapshots or declare a new version by changing versions_with_info alone. Reference: https://source.android.com/docs/core/architecture/aidl/stable-aidl

## 3. Actual mondrian vendor-family evidence and blockers

Read-only hardware reference from LF52406/proprietary_vendor_xiaomi_sm8450-common and LF52406/mondrian_android_device_xiaomi_sm8450-common. The existing blob inventory includes vendor.display.color@1.0 HIDL services, vendor.display.color@1.x shared libraries and SDM color libraries. Their ABI is not known compatible with an independently sourced Qualcomm HWC3 V2/V3 + new QTI display.config V12. A source-only checkout and green AIDL validator cannot establish HWC3/allocator/mapper + panel readiness.

Do not enable the old HIDL Composer2/HIDL mapper in parallel with the selected AIDL Composer3/Allocator/Stable-C mapper. Do not copy Sony display panel configuration or Xiaomi stock properties without real SM8475/DSI/DSC/DRM and vendor-lib verification. The only current goal is a buildable, bootable AOSP17 device: verify matching basic panel initialization, buffer allocation/composition, protected-buffer correctness and absence of black-screen/reboot regressions. Additional display features are not part of this stage.

## 4. Source-only work in the audit branch

- Preserve historical Git ancestry, AIDL API snapshots, C++ headers, Makefiles and original Soong modules without modifying interface ABI or licences.
- Add tests that cross-check pinned old AIDL versions, the actual product-HIDL packaging and incomplete V11, pinned newer HWC3 display.config V12/AIQE V2 requirements, Qualcomm packed buffer handle ABI, official AOSP17 source owner and Xiaomi vendor blob evidence.
- CI uses sparse checkout and pinned commits; it does not execute Qualcomm services or pretend to compile the entire graphics stack.
- Manifest companion Draft PR #2 blocks the old repo via exact checkout path **and** known repo aliases across active and experimental XML profiles. Two regression tests inject the old archive and an aliased checkout. Update row 192 in the strict 135-repository matrix. Historical seventeen and AOSP17 default.xml stay unchanged.

## 5. Remaining gates before a modern Display HAL can be selected

1. Obtain verified matching Qualcomm SDM/DRM/KMS implementation and all closed Soong dependencies from a reviewed, licence-compatible source, including real AIDL V12/AIQE interface providers.
2. Confirm the actual Xiaomi vendor blob ELF DT_NEEDED/symbols, gralloc private-handle structure and metadata offsets, protected buffers, UBWC and ION/DMA-buf import/export with the correct kernel/userspace ABI.
3. Validate single-service ownership and exact VINTF/FCM for graphics Composer3 IComposer/default, Allocator IAllocator/default, Stable-C mapper provider, Qualcomm vendor display.config and color extension; no duplicate legacy HIDL registration.
4. Build full clean AOSP17 with required vendor modules; verify SELinux enforcing, VINTF/FCM and basic graphics CTS/VTS, successful boot to the launcher, stable panel output and Composer3/Allocator/Mapper operation on actual mondrian. Defer all nonessential display enhancements.
5. Roll back a mismatched display stack rather than weakening SELinux, forcing old VINTF versions or using unsafe panel tuning.

**No full repo sync, Soong build, HAL compilation, kernel build, vendor ABI closure, flash/boot or physical device tests were performed by this stage. This is an audited/excluded archival interface source, not a finished Android17 display implementation.**
