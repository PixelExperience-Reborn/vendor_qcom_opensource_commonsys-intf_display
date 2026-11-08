#!/usr/bin/env python3
"""PE-Reborn Android17 stage 192: archived Qualcomm display-interface source gate.

Checks immutable Git history, frozen AIDL modules, packaging, vendor ABI and
the mismatch with an independently pinned new HWC3 source candidate.
NO device HAL build, ABI validation or physical mondrian runtime is implied.
"""
import os
from pathlib import Path
import re
import subprocess
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_COMMIT = "f75571a9d6947c4dc70f3e5138a0cd3df4302c71"
ARCHIVE_TREE = "8521ced92d33ee88e25393d4c8dd74426e05cc62"
SOURCE_PATH = "vendor/qcom/opensource/commonsys-intf/display"
SOURCE_NAME = "vendor_qcom_opensource_commonsys-intf_display"
OFFICIAL_COMPOSER = "platform/hardware/interfaces"
SONY_NEW_CONFIG = "vendor.qti.hardware.display.config-V12-ndk"
SONY_NEW_AIQE = "vendor.qti.hardware.display.aiqe-V2-ndk"


def git(*args):
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True,
        check=True,
    ).stdout.strip()


def tree_item(revision, path):
    line = git("ls-tree", revision, "--", path)
    if not line:
        raise AssertionError("no Git tree entry: " + path)
    prefix, returned_path = line.split("\t", 1)
    mode, kind, sha = prefix.split()
    if returned_path != path:
        raise AssertionError("unexpected Git path: " + returned_path)
    return mode, kind, sha


def external(name):
    source = os.environ.get(name)
    if not source or not Path(source).is_file():
        raise AssertionError("missing pinned reference " + name)
    return Path(source).read_text(encoding="utf-8")


class DisplayCommonsysIntfBoundary(unittest.TestCase):
    def test_archived_2024_qualcomm_merge_is_kept_in_history(self):
        result = subprocess.run(
            ["git", "-C", str(ROOT), "merge-base", "--is-ancestor",
             ARCHIVE_COMMIT, "HEAD"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(git("rev-parse", ARCHIVE_COMMIT + "^{tree}"),
                         ARCHIVE_TREE)

    def test_original_interfaces_headers_and_packaging_unchanged(self):
        # Whole original trees, including AIDL API snapshots, stay untouched.
        for item in ("aidl", "config", "gralloc", "include",
                     "libqdmetadata", "services"):
            with self.subTest(item=item):
                self.assertEqual(tree_item("HEAD", item),
                                 tree_item(ARCHIVE_COMMIT, item))
        self.assertEqual(tree_item("HEAD", "Android.bp"),
                         tree_item(ARCHIVE_COMMIT, "Android.bp"))

    def test_repo_exposes_headers_and_aidl_not_complete_composer_service(self):
        root = (ROOT / "Android.bp").read_text(encoding="utf-8")
        self.assertIn('name: "display_intf_headers"', root)
        self.assertIn("cc_library_headers", root)
        self.assertIn("export_include_dirs:", root)
        # No in-tree Composer3 IComposer/default service source is installed.
        for bp in (ROOT / "Android.bp", *sorted((ROOT / "aidl").glob("*/Android.bp"))):
            self.assertNotIn("cc_binary {", bp.read_text(encoding="utf-8"))
        self.assertFalse((ROOT / "composer").exists())
        self.assertFalse((ROOT / "sdm").exists())
        self.assertFalse((ROOT / "sde-drm").exists())

    def test_original_display_config_frozen_1_to_11_not_v12(self):
        src = (ROOT / "aidl/config/Android.bp").read_text(encoding="utf-8")
        self.assertIn('name: "vendor.qti.hardware.display.config"', src)
        self.assertIn('stability: "vintf"', src)
        self.assertIn('"android.hardware.common-V2"', src)
        self.assertIn("frozen: true", src)
        versions = [int(v) for v in re.findall(r'version:\s*"(\d+)"', src)]
        self.assertEqual(versions, list(range(1, 12)))
        self.assertTrue((ROOT / "aidl/config/aidl_api/vendor.qti.hardware.display.config/11/.hash").is_file())
        self.assertFalse((ROOT / "aidl/config/aidl_api/vendor.qti.hardware.display.config/12").exists())

    def test_composer3_extension_v1_imports_android_composer3_v2(self):
        src = (ROOT / "aidl/composer3/Android.bp").read_text(encoding="utf-8")
        self.assertIn('name: "vendor.qti.hardware.display.composer3"', src)
        self.assertIn('"android.hardware.graphics.composer3-V2"', src)
        self.assertIn("frozen: true", src)
        self.assertEqual(re.findall(r'version:\s*"(\d+)"', src), ["1"])
        code = (ROOT / "aidl/composer3/vendor/qti/hardware/display/composer3/IQtiComposer3Client.aidl").read_text(encoding="utf-8")
        self.assertIn("@VintfStability", code)
        self.assertIn("qtiExecuteCommands", code)
        # This is Qualcomm's extension; it does NOT provide android.hardware.graphics.composer3.IComposer.

    def test_frozen_optional_color_demura_postproc_do_not_prove_services(self):
        for name in ("color", "demura", "postproc"):
            with self.subTest(name=name):
                src = (ROOT / f"aidl/{name}/Android.bp").read_text(encoding="utf-8")
                self.assertIn('stability: "vintf"', src)
                self.assertIn('version: "1"', src)
        self.assertFalse((ROOT / "aidl/aiqe").exists())

    def test_old_product_mixes_hidl_and_aidl_and_omits_config_v11(self):
        vendor = (ROOT / "config/display-interfaces-product.mk").read_text(encoding="utf-8")
        system = (ROOT / "config/display-product-system.mk").read_text(encoding="utf-8")
        self.assertIn("vendor.qti.hardware.display.composer@2.0.vendor", vendor)
        self.assertIn("vendor.qti.hardware.display.mapper@4.0.vendor", vendor)
        self.assertIn("vendor.display.config@2.0.vendor", vendor)
        self.assertIn("vendor.qti.hardware.display.composer3-V1-ndk.vendor", vendor)
        self.assertIn("vendor.qti.hardware.display.config-V10-ndk.vendor", vendor)
        self.assertNotIn("vendor.qti.hardware.display.config-V11-ndk.vendor", vendor)
        self.assertNotIn("vendor.qti.hardware.display.config-V11-ndk", system)
        self.assertNotIn(SONY_NEW_CONFIG, vendor + system)
        self.assertNotIn(SONY_NEW_AIQE, vendor + system)
        # Never inherit either product makefile into an unreviewed AOSP17 product.

    def test_archive_contains_vendor_private_gralloc_handle_layout(self):
        src = (ROOT / "gralloc/gr_priv_handle.h").read_text(encoding="utf-8")
        self.assertIn("#pragma pack(push, 4)", src)
        self.assertIn("private_handle_t : public native_handle_t", src)
        self.assertIn("GRALLOC1_FUNCTION_PERFORM", src)
        self.assertIn("GRALLOC_HANDLE_HAS_RESERVED_SIZE", src)
        self.assertIn("fd_metadata", src)
        # ABI depends on struct layout, metadata, vendor blobs, mapper and selected Soong defaults.

    def test_new_qcom_hwc3_candidate_requires_missing_interfaces(self):
        modern = external("PE_NEW_QCOM_COMPOSER_BP")
        self.assertIn(SONY_NEW_CONFIG, modern)
        self.assertIn(SONY_NEW_AIQE, modern)
        self.assertIn('"android.hardware.graphics.composer3-V3-ndk"', modern)
        self.assertIn('"android.hardware.graphics.composer3-V2-ndk"', modern)
        self.assertNotIn('version: "12"', (ROOT / "aidl/config/Android.bp").read_text(encoding="utf-8"))
        self.assertFalse((ROOT / "aidl/aiqe").exists())
        # The 2024 archive does not close the pinned modern HWC3 candidate dependencies.

    def test_vendor_blob_reference_requires_display_abi_review(self):
        blobs = external("PE_MONDRIAN_BLOBS")
        self.assertIn("vendor/bin/hw/vendor.display.color@1.0-service", blobs)
        self.assertIn("vendor/lib64/vendor.display.color@1.0.so", blobs)
        self.assertIn("vendor/lib64/libsdm-color.so", blobs)
        # Existing Xiaomi vendor HIDL display consumers are not implicitly AIDL/V12 compatible.

    def test_official_aosp17_graph_does_not_import_archived_interface(self):
        root = ET.fromstring(external("PE_AOSP17_REFERENCE"))
        self.assertEqual(root.find("default").get("revision"),
                         "refs/tags/android-17.0.0_r1")
        projects = list(root.iter("project"))
        names = {p.get("path"): p.get("name") for p in projects}
        self.assertEqual(names["hardware/interfaces"], OFFICIAL_COMPOSER)
        self.assertNotIn(SOURCE_PATH, names)
        self.assertNotIn(SOURCE_NAME, names.values())

    def test_active_entrypoint_is_unchanged_not_candidate(self):
        root = ET.fromstring(external("PE_AOSP17_DEFAULT"))
        includes = [x.get("name") for x in root.findall("include")]
        self.assertEqual(includes, ["aosp17_pe_p2_kernel_configs.xml"])
        self.assertFalse(any(p.get("path") == SOURCE_PATH or
                             p.get("name") == SOURCE_NAME
                             for p in root.iter("project")))

if __name__ == "__main__":
    unittest.main(verbosity=2)
