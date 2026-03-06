[settings]
os=Android
os.api_level=24
arch=armv8
compiler=clang
compiler.version=18
compiler.cppstd=17
compiler.libcxx=c++_shared
build_type=Release

[tool_requires]
android-ndk/r27c

[buildenv]
LDFLAGS=-Wl,-z,max-page-size=16384
