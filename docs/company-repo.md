# Keeping Flight Deck in your company's GitHub

The work Mac can't clone `dudgeon/flight-deck-demo`, but it can push to a
repository in the company's own GitHub. This page covers moving a downloaded
copy into such a repository, using it from there, and bringing in later
versions without losing anything (D-171).

It assumes `git` works on the Mac. Type `git --version` in Terminal to check.
If macOS offers to install the command line developer tools, let it, or ask
IT. Nothing here needs npm, pip or the open internet: the only network traffic
is `git push` and `git clone` to your company's GitHub.

## How it fits together

- **The download is the source of each new version.** You still download the
  ZIP of `dudgeon/flight-deck-demo` in the browser, as in the README.
- **The company repository is your team's copy.** It holds the app plus
  everything you build: skills, workflows, people, scenarios.
- **A clone of it is its own app folder.** Running `sh setup.sh` in the clone
  runs the app right there; it doesn't copy it to `~/flight-deck`.
- **`.install-manifest.json` is committed.** It records what the last
  downloaded version shipped. That record is how an update tells your team's
  changes apart from ours, so it has to travel with the repository.

## 1. Put your copy into the company repository (once)

Do this after setup has installed the app (README, steps 1 and 2), so
`~/flight-deck` has its install record.

1. Create an empty repository in your company's GitHub, for example
   `flight-deck`, with no README or license, so it starts empty.
2. In Terminal, paste these lines one at a time. Replace the address on the
   third line with your new repository's address (the green **Code** button).

   ```bash
   cd ~/flight-deck && sh stop.sh
   git init -b main && git add -A && git commit -m "Flight Deck from dudgeon/flight-deck-demo"
   git remote add origin https://github.com/YOUR-COMPANY/flight-deck.git
   git push -u origin main
   ```

What goes in: the app, the workspace, and the install record. What stays out
(`.gitignore`): the Python runtime in `.runtime/`, Hangar drafts in
`workspace/.hangar/`, flown demos, the usage log in `logs/`, setup's
`updates/` folder and its report. Sessions are in `~/.omnigent-slim`, outside
the folder, and never go in.

## 2. Use it from a clone

On any work Mac, yours or a teammate's:

```bash
git clone https://github.com/YOUR-COMPANY/flight-deck.git ~/flight-deck
sh ~/flight-deck/setup.sh
```

Setup sees a git checkout and runs it in place. The first run unpacks the
bundled Python (about a minute), adds the Dock icon and starts the app.

If you made the repository in step 1 from `~/flight-deck`, the clone can go
straight back into `~/flight-deck`: move or delete the old folder first.

## 3. Bring in a newer version

1. Download the ZIP of `dudgeon/flight-deck-demo` again in the browser. You
   don't need to unzip it.
2. In Terminal: `sh ~/flight-deck/setup.sh`

Setup finds the newest download in Downloads, updates the clone in place and
restarts the app, with the same rules as any update:

- files your team added are left alone;
- files your team changed keep your version, and our new version is saved in
  `updates/<date>/new-versions/` for you to compare;
- files your team deleted stay deleted;
- the app's own code (outside `workspace/`) takes the new version, and any
  change you made to it is saved in `updates/<date>/replaced/`.

Then commit and push, so your teammates get it with `git pull`:

```bash
cd ~/flight-deck && git add -A && git commit -m "Update Flight Deck" && git push
```

`git status` before you commit shows exactly what the update changed.
Teammates run `git pull`, then `sh ~/flight-deck/setup.sh` to restart on the
new version. Only one person needs to bring in each download.

## Things to know

- **A clone with no install record isn't updated automatically.** If the
  company repository was made from an unzipped download rather than from
  `~/flight-deck`, it has no `.install-manifest.json`. Setup then won't pick up
  downloads by itself: run `sh setup.sh --from ~/Downloads/<the ZIP>` once. On
  that first update every shipped file that differs counts as your team's
  change and is kept (with the new version saved), so nothing is lost; after
  it, the record exists and updates work normally.
- **A ZIP downloaded from your company's repository works too.** Setup
  recognizes any download that holds this app, whatever the file is called.
- **The Hangar's "Send to repo"** (D-113) pushes published configuration to a
  branch of whichever repository the clone came from, so on a company clone
  it goes to the company repository.
- **One app folder per Mac.** The Workspace and Hangar projects point at
  one folder. If you keep both `~/flight-deck` and a clone elsewhere, they
  follow whichever one you started last. Clone into `~/flight-deck` (step 2)
  and keep just that one.
- **Developers' own checkouts** of `dudgeon/flight-deck-demo` have no install
  record, so `sh setup.sh` in one just runs it in place and never pulls in a
  download unless you pass `--from`.
