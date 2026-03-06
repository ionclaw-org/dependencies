.PHONY: all clean ios tvos watchos visionos android macos maccatalyst linux windows

all: ios tvos watchos visionos android macos maccatalyst linux windows

clean:
	rm -rf output build

ios:
	@python scripts/build.py ios

tvos:
	@python scripts/build.py tvos

watchos:
	@python scripts/build.py watchos

visionos:
	@python scripts/build.py visionos

android:
	@python scripts/build.py android

macos:
	@python scripts/build.py macos

maccatalyst:
	@python scripts/build.py maccatalyst

linux:
	@python scripts/build.py linux

windows:
	@python scripts/build.py windows
