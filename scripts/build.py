#!/usr/bin/env python3
"""Builds Conan packages from conanfile.py and merges include/lib into one output per platform. Usage: python scripts/build.py <platform>"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

LIB_EXTENSIONS = (".a", ".so", ".lib")
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent


def run_cmd(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=cwd or ROOT, check=True)


def _is_deploy_package(pkg_dir: Path, exclude: Path | None) -> bool:
    """True if dir has include/ and lib/ with at least one library file."""
    if exclude is not None and pkg_dir.resolve() == exclude.resolve():
        return False

    inc = pkg_dir / "include"
    lib = pkg_dir / "lib"

    if not inc.is_dir() or not lib.is_dir():
        return False

    for f in lib.rglob("*"):
        if f.is_file() and f.suffix in LIB_EXTENSIONS:
            return True

    return False


def _copy_libs(src_lib: Path, lib_dst: Path) -> None:
    """Copies library files from src (and Release/Debug subdirs on Windows) into lib_dst."""
    for p in src_lib.iterdir():
        if p.is_file() and p.suffix in LIB_EXTENSIONS:
            shutil.copy2(p, lib_dst / p.name)

    for sub in ("Release", "Debug"):
        subdir = src_lib / sub

        if subdir.is_dir():
            for p in subdir.iterdir():
                if p.is_file() and p.suffix in LIB_EXTENSIONS:
                    shutil.copy2(p, lib_dst / p.name)


def _merge_include(src_include: Path, include_dst: Path) -> None:
    """Merges src_include into include_dst (overwrites existing dirs)."""
    for p in src_include.iterdir():
        dst = include_dst / p.name

        if p.is_dir():
            if dst.exists():
                shutil.rmtree(dst)

            shutil.copytree(p, dst)
        else:
            shutil.copy2(p, dst)


def build_single(profile: str, lib_dst: Path, include_dst: Path | None = None) -> None:
    """Runs Conan install for the profile and merges all deployed packages into lib_dst and include_dst."""
    build_dir = ROOT / "build" / profile
    lib_dst = lib_dst.resolve()

    if include_dst is not None:
        include_dst = include_dst.resolve()

    print(f"Building dependencies for profile: {profile}")

    build_dir.mkdir(parents=True, exist_ok=True)
    if lib_dst.exists():
        shutil.rmtree(lib_dst)

    lib_dst.mkdir(parents=True, exist_ok=True)

    profile_path = ROOT / "profiles" / f"{profile}.profile"
    if not profile_path.is_file():
        raise SystemExit(f"Error: profile not found: {profile_path}")

    subprocess.run(
        [
            "conan",
            "install",
            str(ROOT),
            f"--profile:host={profile_path}",
            "--profile:build=default",
            "--build=missing",
            "--deployer=full_deploy",
            f"--output-folder={build_dir}",
        ],
        cwd=ROOT,
        check=True,
    )

    deploy_dirs: list[Path] = []
    for d in build_dir.rglob("*"):
        if not d.is_dir():
            continue
        if _is_deploy_package(d, None):
            deploy_dirs.append(d)

    if not deploy_dirs:
        raise SystemExit("Error: no deployed packages found (check conanfile requires)")

    if include_dst is not None:
        include_dst.mkdir(parents=True, exist_ok=True)
    for pkg_dir in deploy_dirs:
        _copy_libs(pkg_dir / "lib", lib_dst)
        if include_dst is not None:
            _merge_include(pkg_dir / "include", include_dst)

    shutil.rmtree(build_dir, ignore_errors=True)
    print(f"Completed: {profile}")


def build_android() -> None:
    output = ROOT / "output" / "android"
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    build_single("android-arm64-v8a", output / "lib" / "arm64-v8a", output / "include")
    build_single("android-armeabi-v7a", output / "lib" / "armeabi-v7a")
    build_single("android-x86_64", output / "lib" / "x86_64")
    build_single("android-x86", output / "lib" / "x86")
    print(f"Android build complete: {output}")


def build_ios() -> None:
    output = ROOT / "output" / "ios"

    if output.exists():
        shutil.rmtree(output)

    output.mkdir(parents=True)

    build_single("ios-arm64", output / "lib" / "iphoneos" / "arm64", output / "include")
    build_single("ios-simulator-arm64", output / "lib" / "iphonesimulator" / "arm64")
    build_single("ios-simulator-x86_64", output / "lib" / "iphonesimulator" / "x86_64")

    sim_fat = output / "lib" / "_sim_fat"
    sim_fat.mkdir(parents=True, exist_ok=True)
    sim_arm = output / "lib" / "iphonesimulator" / "arm64"
    sim_x64 = output / "lib" / "iphonesimulator" / "x86_64"
    device_lib = output / "lib" / "iphoneos" / "arm64"
    include = output / "include"

    for f in sim_arm.iterdir():
        if not f.is_file() or f.suffix != ".a":
            continue

        other = sim_x64 / f.name

        if other.is_file():
            run_cmd(
                [
                    "lipo",
                    "-create",
                    str(sim_arm / f.name),
                    str(other),
                    "-output",
                    str(sim_fat / f.name),
                ]
            )
    for f in device_lib.iterdir():
        if not f.is_file() or f.suffix != ".a":
            continue

        sim_lib = sim_fat / f.name

        if not sim_lib.is_file():
            continue

        run_cmd(
            [
                "xcodebuild",
                "-create-xcframework",
                "-library",
                str(device_lib / f.name),
                "-headers",
                str(include),
                "-library",
                str(sim_lib),
                "-headers",
                str(include),
                "-output",
                str(output / "lib" / f"{f.stem}.xcframework"),
            ]
        )

    shutil.rmtree(sim_fat, ignore_errors=True)
    shutil.rmtree(output / "lib" / "iphoneos", ignore_errors=True)
    shutil.rmtree(output / "lib" / "iphonesimulator", ignore_errors=True)

    print(f"iOS build complete: {output}")


def build_macos() -> None:
    output = ROOT / "output" / "macos"

    if output.exists():
        shutil.rmtree(output)

    output.mkdir(parents=True)
    build_single("macos-arm64", output / "lib" / "_arm64", output / "include")
    build_single("macos-x86_64", output / "lib" / "_x86_64")

    lib_dir = output / "lib"
    arm_dir = lib_dir / "_arm64"
    x64_dir = lib_dir / "_x86_64"

    for f in arm_dir.iterdir():
        if not f.is_file() or f.suffix != ".a":
            continue

        other = x64_dir / f.name
        if not other.is_file():
            continue

        run_cmd(
            [
                "lipo",
                "-create",
                str(arm_dir / f.name),
                str(other),
                "-output",
                str(lib_dir / f.name),
            ]
        )

    shutil.rmtree(arm_dir, ignore_errors=True)
    shutil.rmtree(x64_dir, ignore_errors=True)

    print(f"macOS build complete: {output}")


def build_maccatalyst() -> None:
    output = ROOT / "output" / "maccatalyst"

    if output.exists():
        shutil.rmtree(output)

    output.mkdir(parents=True)
    build_single("maccatalyst-arm64", output / "lib" / "_arm64", output / "include")
    build_single("maccatalyst-x86_64", output / "lib" / "_x86_64")

    lib_dir = output / "lib"
    arm_dir = lib_dir / "_arm64"
    x64_dir = lib_dir / "_x86_64"

    for f in arm_dir.iterdir():
        if not f.is_file() or f.suffix != ".a":
            continue

        other = x64_dir / f.name
        if not other.is_file():
            continue

        run_cmd(
            [
                "lipo",
                "-create",
                str(arm_dir / f.name),
                str(other),
                "-output",
                str(lib_dir / f.name),
            ]
        )

    shutil.rmtree(arm_dir, ignore_errors=True)
    shutil.rmtree(x64_dir, ignore_errors=True)

    print(f"Mac Catalyst build complete: {output}")


def build_linux() -> None:
    for name, profile in [
        ("linux-x86_64", "linux-x86_64"),
        ("linux-aarch64", "linux-aarch64"),
    ]:
        output = ROOT / "output" / name

        if output.exists():
            shutil.rmtree(output)

        output.mkdir(parents=True)
        build_single(profile, output / "lib", output / "include")

    print("Linux build complete")


def build_tvos() -> None:
    output = ROOT / "output" / "tvos"

    if output.exists():
        shutil.rmtree(output)

    output.mkdir(parents=True)

    build_single(
        "tvos-arm64", output / "lib" / "appletvos" / "arm64", output / "include"
    )
    build_single("tvos-simulator-arm64", output / "lib" / "appletvsimulator" / "arm64")
    build_single(
        "tvos-simulator-x86_64", output / "lib" / "appletvsimulator" / "x86_64"
    )

    sim_fat = output / "lib" / "_sim_fat"
    sim_fat.mkdir(parents=True, exist_ok=True)
    sim_arm = output / "lib" / "appletvsimulator" / "arm64"
    sim_x64 = output / "lib" / "appletvsimulator" / "x86_64"
    device_lib = output / "lib" / "appletvos" / "arm64"
    include = output / "include"

    for f in sim_arm.iterdir():
        if not f.is_file() or f.suffix != ".a":
            continue

        other = sim_x64 / f.name

        if other.is_file():
            run_cmd(
                [
                    "lipo",
                    "-create",
                    str(sim_arm / f.name),
                    str(other),
                    "-output",
                    str(sim_fat / f.name),
                ]
            )
    for f in device_lib.iterdir():
        if not f.is_file() or f.suffix != ".a":
            continue

        sim_lib = sim_fat / f.name

        if not sim_lib.is_file():
            continue

        run_cmd(
            [
                "xcodebuild",
                "-create-xcframework",
                "-library",
                str(device_lib / f.name),
                "-headers",
                str(include),
                "-library",
                str(sim_lib),
                "-headers",
                str(include),
                "-output",
                str(output / "lib" / f"{f.stem}.xcframework"),
            ]
        )

    shutil.rmtree(sim_fat, ignore_errors=True)
    shutil.rmtree(output / "lib" / "appletvos", ignore_errors=True)
    shutil.rmtree(output / "lib" / "appletvsimulator", ignore_errors=True)

    print(f"tvOS build complete: {output}")


def build_watchos() -> None:
    output = ROOT / "output" / "watchos"

    if output.exists():
        shutil.rmtree(output)

    output.mkdir(parents=True)

    build_single(
        "watchos-arm64_32", output / "lib" / "watchos" / "arm64_32", output / "include"
    )
    build_single("watchos-simulator-arm64", output / "lib" / "watchsimulator" / "arm64")
    build_single(
        "watchos-simulator-x86_64", output / "lib" / "watchsimulator" / "x86_64"
    )

    sim_fat = output / "lib" / "_sim_fat"
    sim_fat.mkdir(parents=True, exist_ok=True)
    sim_arm = output / "lib" / "watchsimulator" / "arm64"
    sim_x64 = output / "lib" / "watchsimulator" / "x86_64"
    device_lib = output / "lib" / "watchos" / "arm64_32"
    include = output / "include"

    for f in sim_arm.iterdir():
        if not f.is_file() or f.suffix != ".a":
            continue

        other = sim_x64 / f.name

        if other.is_file():
            run_cmd(
                [
                    "lipo",
                    "-create",
                    str(sim_arm / f.name),
                    str(other),
                    "-output",
                    str(sim_fat / f.name),
                ]
            )

    for f in device_lib.iterdir():
        if not f.is_file() or f.suffix != ".a":
            continue

        sim_lib = sim_fat / f.name

        if not sim_lib.is_file():
            continue

        run_cmd(
            [
                "xcodebuild",
                "-create-xcframework",
                "-library",
                str(device_lib / f.name),
                "-headers",
                str(include),
                "-library",
                str(sim_lib),
                "-headers",
                str(include),
                "-output",
                str(output / "lib" / f"{f.stem}.xcframework"),
            ]
        )

    shutil.rmtree(sim_fat, ignore_errors=True)
    shutil.rmtree(output / "lib" / "watchos", ignore_errors=True)
    shutil.rmtree(output / "lib" / "watchsimulator", ignore_errors=True)

    print(f"watchOS build complete: {output}")


def build_visionos() -> None:
    output = ROOT / "output" / "visionos"

    if output.exists():
        shutil.rmtree(output)

    output.mkdir(parents=True)

    build_single(
        "visionos-arm64", output / "lib" / "xros" / "arm64", output / "include"
    )
    build_single("visionos-simulator-arm64", output / "lib" / "xrsimulator" / "arm64")
    build_single("visionos-simulator-x86_64", output / "lib" / "xrsimulator" / "x86_64")

    sim_fat = output / "lib" / "_sim_fat"
    sim_fat.mkdir(parents=True, exist_ok=True)
    sim_arm = output / "lib" / "xrsimulator" / "arm64"
    sim_x64 = output / "lib" / "xrsimulator" / "x86_64"
    device_lib = output / "lib" / "xros" / "arm64"
    include = output / "include"

    for f in sim_arm.iterdir():
        if not f.is_file() or f.suffix != ".a":
            continue

        other = sim_x64 / f.name

        if other.is_file():
            run_cmd(
                [
                    "lipo",
                    "-create",
                    str(sim_arm / f.name),
                    str(other),
                    "-output",
                    str(sim_fat / f.name),
                ]
            )

    for f in device_lib.iterdir():
        if not f.is_file() or f.suffix != ".a":
            continue

        sim_lib = sim_fat / f.name

        if not sim_lib.is_file():
            continue

        run_cmd(
            [
                "xcodebuild",
                "-create-xcframework",
                "-library",
                str(device_lib / f.name),
                "-headers",
                str(include),
                "-library",
                str(sim_lib),
                "-headers",
                str(include),
                "-output",
                str(output / "lib" / f"{f.stem}.xcframework"),
            ]
        )

    shutil.rmtree(sim_fat, ignore_errors=True)
    shutil.rmtree(output / "lib" / "xros", ignore_errors=True)
    shutil.rmtree(output / "lib" / "xrsimulator", ignore_errors=True)

    print(f"visionOS build complete: {output}")


def build_windows() -> None:
    for name, profile in [
        ("windows-x64", "windows-x64"),
        ("windows-x86", "windows-x86"),
        ("windows-arm64", "windows-arm64"),
    ]:
        output = ROOT / "output" / name

        if output.exists():
            shutil.rmtree(output)

        output.mkdir(parents=True)
        build_single(profile, output / "lib", output / "include")

    print("Windows build complete")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/build.py <platform>", file=sys.stderr)
        print(
            "Platforms: android, ios, macos, maccatalyst, linux, tvos, visionos, watchos, windows",
            file=sys.stderr,
        )

        sys.exit(1)

    platform = sys.argv[1].lower()
    builders = {
        "android": build_android,
        "ios": build_ios,
        "macos": build_macos,
        "maccatalyst": build_maccatalyst,
        "linux": build_linux,
        "tvos": build_tvos,
        "visionos": build_visionos,
        "watchos": build_watchos,
        "windows": build_windows,
    }

    if platform not in builders:
        print(f"Unknown platform: {platform}", file=sys.stderr)
        sys.exit(1)

    builders[platform]()


if __name__ == "__main__":
    main()
