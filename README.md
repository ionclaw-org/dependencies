# Conan Dependency Builder

Builds and packages the libs declared in `conanfile.py`. One static `include/` and `lib/` per platform, one archive per platform in Releases. Use the archive as the source of truth and link what you need. If the prebuilt is not there, fall back to the system.

## Editing dependencies

Edit `conanfile.py`: change `requires` and the options in `configure()`. To add another package, add it to `requires` and set its options in `configure()`. The build script merges all Conan-deployed packages into one output per platform. All libs are static.

Project version is in `CMakeLists.txt`. Bump it when releasing.

## Supported platforms

| Platform | Architectures | Output |
|----------|---------------|--------|
| iOS | arm64 (device), arm64 + x86_64 (simulator) | `.a` + `.xcframework` |
| tvOS | arm64 (device), arm64 + x86_64 (simulator) | `.a` + `.xcframework` |
| watchOS | arm64_32 (device), arm64 + x86_64 (simulator) | `.a` + `.xcframework` |
| visionOS | arm64 (device), arm64 + x86_64 (simulator) | `.a` + `.xcframework` |
| Android | arm64-v8a, armeabi-v7a, x86_64, x86 | `.a` |
| macOS | arm64 + x86_64 (universal) | `.a` |
| Mac Catalyst | arm64 + x86_64 (universal) | `.a` |
| Linux | x86_64, aarch64 | `.a` |
| Windows | x64, x86, arm64 | `.lib` |

## Using the prebuilt

Download the archive for your platform from Releases (e.g. `deps-ios.zip`, `deps-linux-x86_64.zip`), extract it. You get `include/` and `lib/` with all packaged libs. Point your build at that folder and link the libs you need (e.g. zlib: link `z` or `zlib`).

**Example (zlib):** use the package when present, otherwise fall back to the system.

```cmake
set(DEPS_ROOT "path/to/extracted/archive" CACHE PATH "Prebuilt deps (e.g. from Releases)")

if(DEPS_ROOT AND EXISTS "${DEPS_ROOT}/include" AND EXISTS "${DEPS_ROOT}/lib")
  add_library(zlib INTERFACE IMPORTED GLOBAL)
  set_target_properties(zlib PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES "${DEPS_ROOT}/include"
    INTERFACE_LINK_DIRECTORIES "${DEPS_ROOT}/lib"
    INTERFACE_LINK_LIBRARIES "z")
else()
  find_package(ZLIB REQUIRED)
  add_library(zlib ALIAS ZLIB::ZLIB)
endif()

target_link_libraries(your_target PRIVATE zlib)
```

Same idea for any other lib in the bundle: use `DEPS_ROOT` and the lib name(s) from `lib/` when the prebuilt exists, otherwise `find_package(...)` and link the system target.

## Archives per platform

| Platform | Archive |
|----------|---------|
| iOS | `deps-ios.zip` |
| tvOS | `deps-tvos.zip` |
| watchOS | `deps-watchos.zip` |
| visionOS | `deps-visionos.zip` |
| Android | `deps-android.zip` |
| macOS | `deps-macos.zip` |
| Mac Catalyst | `deps-maccatalyst.zip` |
| Linux x86_64 | `deps-linux-x86_64.zip` |
| Linux aarch64 | `deps-linux-aarch64.zip` |
| Windows x64 | `deps-windows-x64.zip` |
| Windows x86 | `deps-windows-x86.zip` |
| Windows arm64 | `deps-windows-arm64.zip` |

## Building from source

When you don't use the prebuilt, build from source. Output layout is the same: `include/` and `lib/` per platform.

**Prerequisites:** Python 3, [Conan 2](https://conan.io/) (`pip install conan`), and platform toolchains (Xcode, Android NDK, MSVC, etc.).

```bash
conan profile detect --force
```

**Build:**

```bash
make all
```

Or per platform: `make ios`, `make macos`, `make linux`, `make windows`, etc.

```bash
python scripts/build.py <platform>
```

Output goes to `output/`. One `include/` and one `lib/` per platform. On Apple mobile (iOS/tvOS/watchOS/visionOS), `lib/` contains one `.xcframework` per library.

## GitHub Actions

Per-platform workflows: `build-ios.yml`, `build-macos.yml`, `build-linux.yml`, etc. Trigger via `workflow_dispatch`. On tag `vX.Y.Z`, `release.yml` runs all builds and uploads the archives to the Release.

## License

MIT License. See [LICENSE](LICENSE) for details.
