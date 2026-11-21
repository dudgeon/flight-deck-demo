#!/bin/sh
# One-step setup for Flight Deck (omnigent-slim) on a Mac, from a downloaded ZIP.
#
# Run it from Terminal, in the unzipped folder:
#
#   sh setup.sh            check this Mac, fix the download, set up, start the app
#   sh setup.sh --yes      same, without pausing to ask before clearing the flag
#   sh setup.sh --no-open  same, without opening the browser at the end
#
# It never downloads or installs anything: Python, its packages and tmux are in
# this folder. It checks what this Mac needs, says plainly what is missing,
# fixes what unzipping a browser download breaks (the macOS quarantine flag and
# missing execute permissions), then runs ./start.sh, which serves the app on
# http://127.0.0.1:6767.
#
# Every run writes setup-report.txt in this folder, and a copy on the Desktop.
# If something fails, that file is what to send back.
#
# Written for /bin/sh on macOS. Keep it POSIX: no bash-only syntax.

# No `set -e`: every step checks its own result so a failure can be explained.
set -u

ROOT=$(cd "$(dirname "$0")" && pwd)
REPORT="$ROOT/setup-report.txt"
DESKTOP_REPORT="$HOME/Desktop/flight-deck-setup-report.txt"
PORT=6767
ASSUME_YES=0
OPEN_BROWSER=1
for arg in "$@"; do
    case $arg in
        -y|--yes) ASSUME_YES=1 ;;
        --no-open) OPEN_BROWSER=0 ;;
        -h|--help) sed -n '2,19p' "$0"; exit 0 ;;
        *) echo "Unknown option: $arg (try: sh setup.sh --help)" >&2; exit 2 ;;
    esac
done

# ---------------------------------------------------------------- output ----

if [ -t 1 ]; then
    B=$(printf '\033[1m'); G=$(printf '\033[32m'); Y=$(printf '\033[33m')
    R=$(printf '\033[31m'); N=$(printf '\033[0m')
else
    B=; G=; Y=; R=; N=
fi

: > "$REPORT" 2>/dev/null || {
    REPORT="${TMPDIR:-/tmp}/flight-deck-setup-report.txt"
    : > "$REPORT"
}

rep() { printf '%s\n' "$*" >> "$REPORT"; }
step() { printf '\n%s%s%s\n' "$B" "$*" "$N"; rep ""; rep "== $*"; }
ok() { printf '  %s✓%s %s\n' "$G" "$N" "$*"; rep "  OK    $*"; }
note() { printf '  %s!%s %s\n' "$Y" "$N" "$*"; rep "  NOTE  $*"; }
info() { printf '    %s\n' "$*"; rep "        $*"; }
# Paste a command's output (from a file) into the report, indented.
rep_file() { [ -f "$1" ] && sed 's/^/        | /' "$1" >> "$REPORT"; }

save_report() {
    if [ -d "$HOME/Desktop" ] && cp "$REPORT" "$DESKTOP_REPORT" 2>/dev/null; then
        SAVED="$DESKTOP_REPORT"
    else
        SAVED="$REPORT"
    fi
}

# fail <what went wrong> <what to do>...  Stops setup with a clear message.
fail() {
    what=$1; shift
    printf '\n  %s✗ %s%s\n' "$R" "$what" "$N"
    rep "  FAIL  $what"
    for line in "$@"; do printf '    %s\n' "$line"; rep "        $line"; done
    rep ""
    rep "Setup stopped here."
    save_report
    printf '\n%sSetup stopped.%s A report of every check is in:\n' "$B" "$N"
    printf '    %s\n' "$SAVED"
    printf 'If the steps above don'"'"'t fix it, send that file back (it has no passwords\n'
    printf 'or keys in it). You can run %ssh setup.sh%s again at any time.\n\n' "$B" "$N"
    exit 1
}

# -------------------------------------------------------------- the report --

rep "Flight Deck setup report"
rep "Date:    $(date '+%Y-%m-%d %H:%M:%S %Z')"
rep "Folder:  $ROOT"
rep "Setup:   $(shasum "$0" 2>/dev/null | cut -c1-12) (setup.sh)  $(shasum "$ROOT/start.sh" 2>/dev/null | cut -c1-12) (start.sh)"
rep "Upstream: $(head -1 "$ROOT/UPSTREAM" 2>/dev/null)"

printf '%sFlight Deck setup%s\n' "$B" "$N"
printf 'This checks your Mac, prepares this folder and starts the app. Nothing is\n'
printf 'downloaded or installed. It takes about a minute the first time.\n'

# ----------------------------------------------------------- 1. this Mac ----

step "1. Checking this Mac"

os=$(uname -s)
[ "$os" = Darwin ] || fail "This isn't a Mac (the system says '$os')." \
    "Flight Deck's setup only runs on macOS."

macos=$(sw_vers -productVersion 2>/dev/null || echo unknown)
major=${macos%%.*}
case $major in ''|*[!0-9]*) major=0 ;; esac
if [ "$major" -ge 13 ]; then
    ok "macOS $macos"
else
    fail "macOS $macos is too old." "Flight Deck needs macOS 13 (Ventura) or newer."
fi

arch=$(uname -m)
translated=$(sysctl -n sysctl.proc_translated 2>/dev/null || echo 0)
if [ "$arch" = arm64 ]; then
    ok "Apple silicon (arm64)"
elif [ "$translated" = 1 ]; then
    fail "Terminal is running in Intel mode (Rosetta)." \
        "Quit Terminal. In Finder, open Applications > Utilities, select Terminal," \
        "choose File > Get Info, and untick 'Open using Rosetta'. Then try again."
else
    fail "This Mac has an Intel processor ($arch)." \
        "Flight Deck's bundled Python and tmux are built for Apple silicon only."
fi

# Free disk space, in KB, where this folder lives. Setup needs about 600 MB.
free_kb=$(df -Pk "$ROOT" 2>/dev/null | awk 'NR==2 {print $4}')
case $free_kb in ''|*[!0-9]*) free_kb=0 ;; esac
if [ "$free_kb" -ge 1048576 ]; then
    ok "Free disk space: $((free_kb / 1048576)) GB"
elif [ "$free_kb" -ge 614400 ]; then
    note "Free disk space is low: $((free_kb / 1024)) MB. Setup needs about 600 MB."
else
    fail "Not enough free disk space ($((free_kb / 1024)) MB)." \
        "Setup needs about 600 MB. Free some space and run it again."
fi

# ----------------------------------------------------- 2. the download ----

step "2. Checking the downloaded folder"

missing=
for f in start.sh stop.sh pyproject.toml uv.lock vendor/bin/tmux \
         omnigent/server/static/web-ui/index.html sdks/python-client sdks/ui workspace; do
    [ -e "$ROOT/$f" ] || missing="$missing $f"
done
tarball=$(ls "$ROOT"/vendor/python/cpython-*-aarch64.tar.gz 2>/dev/null | head -1)
[ -n "$tarball" ] || missing="$missing vendor/python/cpython-*.tar.gz"
wheels=$(ls "$ROOT"/vendor/wheels/*.whl 2>/dev/null | wc -l | tr -d ' ')
[ "$wheels" -gt 0 ] || missing="$missing vendor/wheels/*.whl"
if [ -n "$missing" ]; then
    fail "The folder is incomplete. Missing:$missing" \
        "The download or the unzip was probably cut short. Delete this folder and" \
        "the ZIP, download the ZIP again and unzip it once more."
fi
ok "All parts are here ($wheels bundled Python packages)"
case $ROOT in
    *" "*) note "The folder path has a space in it. That's fine; mentioned in case it matters." ;;
esac

# The quarantine flag. A browser adds it to every file it downloads, and
# unzipping passes it on to every file inside. macOS then refuses to run the
# bundled tmux and Python. Clearing it on files you chose to download is the
# Terminal version of macOS's own "Open Anyway" button. Only this folder is
# touched.
quarantined=0
for f in "$ROOT/start.sh" "$ROOT/vendor/bin/tmux" "$tarball"; do
    if xattr -p com.apple.quarantine "$f" >/dev/null 2>&1; then quarantined=1; fi
done
if [ "$quarantined" = 0 ]; then
    ok "No download flag (quarantine) on this folder"
else
    note "macOS has flagged this folder as downloaded from the internet."
    rep "        quarantine value: $(xattr -p com.apple.quarantine "$ROOT/vendor/bin/tmux" 2>/dev/null)"
    info "Every file from a browser download carries this flag, and macOS won't"
    info "run the bundled tmux and Python while it's there. Setup will remove the"
    info "flag from this folder only (it is what macOS's 'Open Anyway' does)."
    info "If your company's rules say not to, press Ctrl-C now and use the curl"
    info "download in the README instead; it never adds the flag."
    if [ "$ASSUME_YES" = 0 ] && [ -t 0 ]; then
        printf '    Press Return to continue, or Ctrl-C to stop: '
        read -r _answer
        rep "        (person pressed Return to clear the flag)"
    else
        rep "        (cleared without asking: --yes or no keyboard input)"
    fi
    xattr -dr com.apple.quarantine "$ROOT" > "$ROOT/.setup-xattr.log" 2>&1
    still=0
    for f in "$ROOT/start.sh" "$ROOT/vendor/bin/tmux" "$tarball"; do
        if xattr -p com.apple.quarantine "$f" >/dev/null 2>&1; then still=1; fi
    done
    if [ "$still" = 1 ]; then
        rep_file "$ROOT/.setup-xattr.log"
        rm -f "$ROOT/.setup-xattr.log"
        fail "macOS wouldn't let setup remove the download flag." \
            "Your Mac's settings may lock it. Download the ZIP again with the curl" \
            "line in the README (it never adds the flag), or ask IT."
    fi
    rm -f "$ROOT/.setup-xattr.log"
    ok "Download flag removed from this folder"
fi

# Execute permissions. Some unzip tools drop them; put them back.
fixed=0
for f in "$ROOT"/start.sh "$ROOT"/stop.sh "$ROOT"/setup.sh "$ROOT"/vendor/bin/* \
         "$ROOT"/scripts/*.sh "$ROOT"/vendor/scripts/*.sh "$ROOT"/scripts/dock/*; do
    [ -f "$f" ] || continue
    if [ ! -x "$f" ]; then
        chmod +x "$f" 2>/dev/null && fixed=$((fixed + 1))
    fi
done
[ -x "$ROOT/start.sh" ] && [ -x "$ROOT/vendor/bin/tmux" ] || \
    fail "Setup couldn't make start.sh and tmux runnable." \
        "This folder may be read-only. Move it into your home folder and try again."
if [ "$fixed" -gt 0 ]; then
    ok "Execute permission restored on $fixed files"
else
    ok "Execute permissions are fine"
fi

# The bundled tmux must start. A kill here (exit 137) means macOS blocked it.
"$ROOT/vendor/bin/tmux" -V > "$ROOT/.setup-tmux.log" 2>&1
rc=$?
tmux_v=$(head -1 "$ROOT/.setup-tmux.log")
if [ "$rc" = 0 ]; then
    ok "Bundled tmux runs ($tmux_v)"
    rm -f "$ROOT/.setup-tmux.log"
else
    rep "        tmux exit code: $rc"
    rep_file "$ROOT/.setup-tmux.log"
    rm -f "$ROOT/.setup-tmux.log"
    if [ "$rc" = 137 ] || [ "$rc" = 9 ]; then
        fail "macOS stopped the bundled tmux from running (exit $rc)." \
            "Your Mac's security settings block programs from this download. Download" \
            "the ZIP again with the curl line in the README, or ask IT."
    fi
    fail "The bundled tmux won't run (exit $rc: $tmux_v)." \
        "Send the report back; it has the error."
fi

# ------------------------------------------------- 3. what it relies on ----

step "3. Checking the programs Flight Deck relies on"

# Claude Code. Terminal may not have it on PATH even when it is installed.
claude_bin=$(command -v claude 2>/dev/null)
if [ -z "$claude_bin" ]; then
    for c in "$HOME/.local/bin/claude" "$HOME/.claude/local/claude" \
             /opt/homebrew/bin/claude /usr/local/bin/claude "$HOME/.npm-global/bin/claude"; do
        if [ -x "$c" ]; then claude_bin=$c; break; fi
    done
    if [ -n "$claude_bin" ]; then
        claude_dir=$(dirname "$claude_bin")
        PATH="$claude_dir:$PATH"; export PATH
        note "Claude Code is installed at $claude_bin but Terminal can't find it."
        info "Setup will use it for now. So ./start.sh finds it next time, run:"
        info "  echo 'export PATH=\"$claude_dir:\$PATH\"' >> ~/.zprofile"
    fi
fi
[ -n "$claude_bin" ] || fail "Claude Code ('claude') isn't installed, or Terminal can't find it." \
    "Install Claude Code the way your company provides it. Then open a new" \
    "Terminal window, type 'claude', sign in, type /exit, and run setup again."

claude_v=$(claude --version 2>"$ROOT/.setup-claude.log" </dev/null | head -1)
if [ -n "$claude_v" ]; then
    ok "Claude Code $claude_v ($claude_bin)"
    rm -f "$ROOT/.setup-claude.log"
else
    rep_file "$ROOT/.setup-claude.log"
    rm -f "$ROOT/.setup-claude.log"
    fail "Claude Code is installed but didn't start ('claude --version' failed)." \
        "Open a new Terminal window and type 'claude'. Fix what it reports, sign in," \
        "type /exit, then run setup again."
fi
if [ -e "$HOME/.claude.json" ] || [ -d "$HOME/.claude" ]; then
    ok "Claude Code has been run on this Mac before"
else
    note "Claude Code looks like it has never been run here."
    info "Before your first session, type 'claude' in Terminal, sign in, then /exit."
fi

# Node isn't needed by Flight Deck. Some Claude Code installs (npm) need it.
node_v=$(node --version 2>/dev/null)
if [ -n "$node_v" ]; then
    ok "Node $node_v (not needed by Flight Deck; noted for the report)"
elif head -c 64 "$claude_bin" 2>/dev/null | grep -q node; then
    fail "Claude Code needs Node, and Node isn't installed." \
        "Your Claude Code was installed with npm. Install Node the way your company" \
        "provides it, or ask IT for the native Claude Code installer."
else
    ok "Node isn't installed (not needed)"
fi

# Python is bundled. Unpack-and-run is checked by start.sh; note any system one.
py_v=$(/usr/bin/python3 --version 2>/dev/null </dev/null)
ok "Python 3.12 is bundled in this folder${py_v:+ (the Mac also has $py_v; not used)}"

# The port. start.sh picks the next free port if 6767 is taken.
holder=$(lsof -nP -iTCP:$PORT -sTCP:LISTEN 2>/dev/null | awk 'NR==2 {print $1" (pid "$2")"}')
if [ -z "$holder" ]; then
    ok "Port $PORT is free"
else
    note "Something is already using port $PORT: $holder."
    info "If that is Flight Deck from an earlier run, that's fine. Otherwise the app"
    info "will use the next free port, and setup will tell you which."
fi

# -------------------------------------------------- 4. set up and start ----

step "4. Setting up and starting Flight Deck"
info "The first time, this unpacks the bundled Python and installs its packages"
info "from this folder, with no network. It takes about a minute."
printf '\n'

START_LOG="$ROOT/.setup-start.log"
rc_file="$ROOT/.setup-start.rc"
rm -f "$START_LOG" "$rc_file"
( "$ROOT/start.sh" --no-open 2>&1; echo $? > "$rc_file" ) | tee "$START_LOG" | sed 's/^/    /'
start_rc=$(cat "$rc_file" 2>/dev/null || echo 1)
rm -f "$rc_file"
rep "        start.sh exit code: $start_rc"
rep_file "$START_LOG"

server_logs() {
    logs="${OMNIGENT_DATA_DIR:-$HOME/.omnigent-slim}/logs"
    [ -d "$logs" ] || return 0
    rep ""
    rep "== Recent server logs ($logs)"
    for f in $(ls -t "$logs"/*.log 2>/dev/null | head -3); do
        rep "  -- $(basename "$f") (last 60 lines)"
        tail -n 60 "$f" | sed 's/^/        | /' >> "$REPORT"
    done
}

if [ "$start_rc" != 0 ]; then
    killed=0
    grep -q -i "killed" "$START_LOG" && killed=1
    rm -f "$START_LOG"
    server_logs
    if [ "$killed" = 1 ]; then
        fail "macOS stopped the bundled Python from running." \
            "Your Mac's security settings block programs from this download. Download" \
            "the ZIP again with the curl line in the README, or ask IT."
    fi
    fail "Flight Deck didn't start (start.sh stopped with exit code $start_rc)." \
        "The lines just above say what went wrong. Run 'sh setup.sh' once more; if it" \
        "fails the same way, send the report back."
fi

url=$(sed -n 's/.*omnigent-slim is running: \(http[^ ]*\).*/\1/p' "$START_LOG" | tail -1)
rm -f "$START_LOG"
url=${url:-http://127.0.0.1:$PORT/library}
base=${url%/library}

# Confirm the app answers (this machine only; nothing leaves the Mac).
up=0
i=0
while [ $i -lt 20 ]; do
    if curl -fsS --noproxy '*' -o /dev/null --max-time 3 "$base/" 2>/dev/null; then up=1; break; fi
    i=$((i + 1)); sleep 1
done
if [ "$up" = 1 ]; then
    ok "Flight Deck answers at $url"
else
    server_logs
    fail "Flight Deck started but doesn't answer at $base." \
        "Run './stop.sh', then 'sh setup.sh' again. If it fails again, send the report."
fi
case $base in
    *:$PORT) ;;
    *) note "Port $PORT was busy, so it is on ${base##*:} instead." ;;
esac

rep ""
rep "Setup finished: Flight Deck is running at $url"
save_report

printf '\n%s%sFlight Deck is running.%s Open %s%s%s\n' "$B" "$G" "$N" "$B" "$url" "$N"
printf '  Next time, start it with ./start.sh and stop it with ./stop.sh (in this folder).\n'
printf '  Optional Dock icon: scripts/make_dock_app.sh --add-to-dock\n'
printf '  A report of this setup is in %s\n\n' "$SAVED"
[ "$OPEN_BROWSER" = 1 ] && open "$url" 2>/dev/null

exit 0
