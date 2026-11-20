#!/bin/sh
# Build a self-contained tmux for macOS (arm64 + x86_64 universal) and put it
# in vendor/bin/tmux. Run this on a Mac with Xcode command line tools and
# internet access (a build machine, not the offline work machine). The result
# links only to libraries every Mac ships (libSystem, libncurses, libresolv),
# so the committed binary runs without Homebrew.
set -eu

TMUX_VERSION=3.8
LIBEVENT_VERSION=2.1.13-stable

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
WORK=${TMPDIR:-/tmp}/omnigent-slim-tmux-build
rm -rf "$WORK"
mkdir -p "$WORK/src"
cd "$WORK/src"

curl -fsSLO "https://github.com/libevent/libevent/releases/download/release-${LIBEVENT_VERSION}/libevent-${LIBEVENT_VERSION}.tar.gz"
curl -fsSLO "https://github.com/tmux/tmux/releases/download/${TMUX_VERSION}/tmux-${TMUX_VERSION}.tar.gz"

build_arch() {
    arch=$1
    prefix="$WORK/$arch"
    flags="-arch $arch -mmacosx-version-min=12.0 -O2 -Werror=unguarded-availability-new"
    # config.sub predates the "arm64" spelling.
    case $arch in arm64) host=aarch64-apple-darwin ;; *) host=$arch-apple-darwin ;; esac
    # The SDK declares calls newer than the deployment target (e.g. pipe2 is
    # macOS 27+); tell configure they're missing so older Macs can run it.
    export ac_cv_func_pipe2=no
    mkdir -p "$prefix/build"
    cd "$prefix/build"
    tar xzf "$WORK/src/libevent-${LIBEVENT_VERSION}.tar.gz"
    tar xzf "$WORK/src/tmux-${TMUX_VERSION}.tar.gz"

    cd "libevent-${LIBEVENT_VERSION}"
    CFLAGS="$flags" ./configure --host="$host" --prefix="$prefix/deps" \
        --enable-static --disable-shared --disable-openssl --disable-samples \
        --disable-libevent-regress >/dev/null
    make -j8 >/dev/null
    make install >/dev/null
    cd ..

    cd "tmux-${TMUX_VERSION}"
    CFLAGS="$flags -I$prefix/deps/include" LDFLAGS="-arch $arch -L$prefix/deps/lib" \
        LIBEVENT_CFLAGS="-I$prefix/deps/include" LIBEVENT_LIBS="$prefix/deps/lib/libevent_core.a" \
        LIBNCURSES_CFLAGS="" LIBNCURSES_LIBS="-lncurses" \
        ./configure --host="$host" --disable-utf8proc --disable-jemalloc >/dev/null
    make -j8 >/dev/null
    cp tmux "$WORK/tmux-$arch"
}

build_arch arm64
build_arch x86_64

mkdir -p "$ROOT/vendor/bin"
lipo -create -output "$ROOT/vendor/bin/tmux" "$WORK/tmux-arm64" "$WORK/tmux-x86_64"
chmod 755 "$ROOT/vendor/bin/tmux"
echo "built: $("$ROOT/vendor/bin/tmux" -V)"
otool -L "$ROOT/vendor/bin/tmux"
