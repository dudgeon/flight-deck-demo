#!/bin/sh
# Build a Mac app that starts omnigent-slim and opens its UI, for the Dock.
#
#   scripts/make_dock_app.sh                 build ~/Applications/Product Aviator.app
#   scripts/make_dock_app.sh --add-to-dock   same, then pin it to the Dock
#   scripts/make_dock_app.sh --browser default --name "Aviator" --dest ~/Desktop
#
# Clicking the app runs ./start.sh --no-open (it starts the server only if it
# isn't running, and takes about two seconds when it is), then opens the UI:
# in its own app-style Chrome window (--app=URL) when Google Chrome is
# installed, otherwise in your default browser (--browser default forces that).
#
# Everything is local: the app is a small folder of text files plus an icon
# made here with sips and iconutil. Nothing is downloaded, and a locally built
# app is never quarantined, so there is no Gatekeeper flag to clear. If you
# move this repo folder, run this script again.
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
NAME="Product Aviator"
DEST="$HOME/Applications"
BROWSER=auto
ADD_TO_DOCK=0
while [ $# -gt 0 ]; do
    case $1 in
        --name) NAME=$2; shift ;;
        --dest) DEST=$2; shift ;;
        --browser) BROWSER=$2; shift ;;
        --add-to-dock) ADD_TO_DOCK=1 ;;
        -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
    shift
done
case $BROWSER in auto|chrome|default) ;; *) echo "--browser is auto, chrome or default" >&2; exit 2 ;; esac
[ "$(uname -s)" = Darwin ] || { echo "make_dock_app: macOS only." >&2; exit 1; }

APP="$DEST/$NAME.app"
# Dock-launched apps get a bare PATH, so remember where claude lives now.
CLAUDE_DIR=$(dirname "$(command -v claude 2>/dev/null || echo "$HOME/.local/bin/claude")")

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/app/Contents/MacOS" "$tmp/app/Contents/Resources"

# Icon: the committed 1024px PNG (scripts/dock/app-icon.svg is its source),
# resized with sips and packed with iconutil.
iconset="$tmp/AppIcon.iconset"
mkdir -p "$iconset"
for size in 16 32 128 256 512; do
    sips -z $size $size "$ROOT/scripts/dock/app-icon.png" --out "$iconset/icon_${size}x${size}.png" >/dev/null
    double=$((size * 2))
    sips -z $double $double "$ROOT/scripts/dock/app-icon.png" --out "$iconset/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$iconset" -o "$tmp/app/Contents/Resources/AppIcon.icns"

cat > "$tmp/app/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>$NAME</string>
    <key>CFBundleDisplayName</key><string>$NAME</string>
    <key>CFBundleIdentifier</key><string>local.omnigent-slim.launcher</string>
    <key>CFBundleExecutable</key><string>launch</string>
    <key>CFBundleIconFile</key><string>AppIcon</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleShortVersionString</key><string>1.0</string>
    <key>CFBundleVersion</key><string>1</string>
    <key>LSMinimumSystemVersion</key><string>13.0</string>
    <key>LSUIElement</key><true/>
</dict>
</plist>
EOF

# The launcher. Values from this build are written in; the rest runs on click.
{
    echo '#!/bin/sh'
    echo "# Built by scripts/make_dock_app.sh. Starts omnigent-slim and opens its UI."
    printf 'ROOT=%s\n' "'$(printf %s "$ROOT" | sed "s/'/'\\\\''/g")'"
    printf 'BROWSER=%s\n' "$BROWSER"
    printf 'export PATH=%s\n' "'$(printf %s "$CLAUDE_DIR:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" | sed "s/'/'\\\\''/g")'"
    cat <<'EOF'
LOG="$HOME/Library/Logs/omnigent-slim-launcher.log"
mkdir -p "$(dirname "$LOG")"

alert() {
    /usr/bin/osascript - "$1" >/dev/null 2>&1 <<'APPLESCRIPT'
on run argv
    display alert "omnigent-slim didn't start" message (item 1 of argv) as critical
end run
APPLESCRIPT
}

if [ ! -x "$ROOT/start.sh" ]; then
    alert "Can't find $ROOT/start.sh. If you moved the repo, run scripts/make_dock_app.sh again from its new place."
    exit 1
fi

# start.sh starts the server only if it isn't running, then prints the URL.
if ! "$ROOT/start.sh" --no-open >"$LOG" 2>&1 </dev/null; then
    alert "$(tail -n 6 "$LOG")

Full log: $LOG"
    exit 1
fi
URL=$(sed -n 's/^omnigent-slim is running: //p' "$LOG" | tail -1)
URL=${URL:-http://127.0.0.1:6767/library}

if [ "$BROWSER" != default ] && /usr/bin/open -Ra "Google Chrome" 2>/dev/null; then
    /usr/bin/open -na "Google Chrome" --args --app="$URL"
else
    /usr/bin/open "$URL"
fi
EOF
} > "$tmp/app/Contents/MacOS/launch"
chmod 755 "$tmp/app/Contents/MacOS/launch"

mkdir -p "$DEST"
rm -rf "$APP"
mv "$tmp/app" "$APP"
# Tell Finder and the Dock about the new icon.
touch "$APP"
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$APP" 2>/dev/null || true
echo "Built $APP"

if [ "$ADD_TO_DOCK" = 1 ]; then
    url="file://$(printf %s "$APP" | sed 's/ /%20/g')/"
    if defaults read com.apple.dock persistent-apps 2>/dev/null | grep -Fq "$url"; then
        echo "Already in the Dock."
    else
        defaults write com.apple.dock persistent-apps -array-add \
            "<dict><key>tile-data</key><dict><key>file-data</key><dict><key>_CFURLString</key><string>$url</string><key>_CFURLStringType</key><integer>15</integer></dict></dict></dict>"
        killall Dock
        echo "Added to the Dock."
    fi
else
    echo "Drag it to the Dock, or run again with --add-to-dock."
fi
