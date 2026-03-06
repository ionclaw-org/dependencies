include(default)

[settings]
os=Linux
arch=armv8
build_type=Release
compiler=gcc
compiler.version=11
compiler.libcxx=libstdc++11

[buildenv]
CC=aarch64-linux-gnu-gcc
CXX=aarch64-linux-gnu-g++
