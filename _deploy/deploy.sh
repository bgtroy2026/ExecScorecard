#!/bin/bash
#############################################################
#  Deploy ExecScorecard — commit everything in this folder and push it to
#  github.com/bgtroy2026/ExecScorecard. GitHub Actions then publishes site/ to Pages.
#
#  Double-click "Deploy ExecScorecard.command" (runs in Terminal) or run:
#     bash _deploy/deploy.sh "commit message"
#
#  First run only: creates the GitHub repo (public, so Pages works on the free plan),
#  turns on GitHub Pages, and sets this folder up as a git repository.
#
#  Uses the same GitHub token the Sales Portal / StorePortal deploys keep in your
#  Keychain (service BigGrovePortalDeploy). If none is found it asks once and saves it.
#############################################################
set -u
PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_NAME="ExecScorecard"
GH_USER="bgtroy2026"
REPO="$GH_USER/$REPO_NAME"
KC_SERVICE="BigGrovePortalDeploy"
API="https://api.github.com"
ACTIONS_URL="https://github.com/$REPO/actions"
SITE_URL="https://$GH_USER.github.io/$REPO_NAME/"
LOG="$PROJECT/_deploy/deploy_last.log"
mkdir -p "$PROJECT/_deploy"
exec > >(tee "$LOG") 2>&1
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

say()  { printf '\n\033[1;32m%s\033[0m\n' "$*"; }
die()  { printf '\n\033[1;31mERROR: %s\033[0m\n' "$*"; read -n1 -s -r -p "Press any key to close..."; echo; exit 1; }

echo "==================================================="
echo "Deploy ExecScorecard  $(date '+%Y-%m-%d %H:%M:%S')"
echo "==================================================="
cd "$PROJECT" || die "Cannot open $PROJECT"

# ---------------------------------------------------------- token (Keychain)
TOKEN=$(security find-generic-password -s "$KC_SERVICE" -a "$GH_USER" -w 2>/dev/null || true)
if [ -z "$TOKEN" ]; then
  echo
  echo "No GitHub token found in your Keychain for $GH_USER."
  echo "Create a classic personal access token with the 'repo' and 'workflow' scopes at https://github.com/settings/tokens"
  read -r -s -p "Paste the token (it will be saved to your Keychain): " TOKEN; echo
  [ -z "$TOKEN" ] && die "No token entered."
  security add-generic-password -U -s "$KC_SERVICE" -a "$GH_USER" -w "$TOKEN" 2>/dev/null || echo "(could not save to Keychain — continuing)"
fi
AUTH_URL="https://${GH_USER}:${TOKEN}@github.com/${REPO}.git"
gh_api() { curl -sS -o /tmp/execsc_api.json -w '%{http_code}' -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" "$@"; }

# ---------------------------------------------------------- first run: create the repo
CODE=$(gh_api "$API/repos/$REPO")
if [ "$CODE" = "404" ]; then
  say "Creating github.com/$REPO ..."
  CODE=$(gh_api -X POST "$API/user/repos" -d "{\"name\":\"$REPO_NAME\",\"description\":\"Big Grove Brewery Executive Scorecard\",\"private\":false,\"auto_init\":false,\"has_wiki\":false}")
  [ "$CODE" = "201" ] || { cat /tmp/execsc_api.json; die "Could not create the repo (HTTP $CODE). Create it by hand at https://github.com/new named $REPO_NAME, then run this again."; }
elif [ "$CODE" = "401" ]; then
  security delete-generic-password -s "$KC_SERVICE" -a "$GH_USER" >/dev/null 2>&1
  die "GitHub rejected the token (it was removed from the Keychain — run this again and paste a new one)."
elif [ "$CODE" != "200" ]; then
  cat /tmp/execsc_api.json; die "Could not check the repo (HTTP $CODE)."
fi

# ---------------------------------------------------------- git setup
if [ ! -d .git ]; then
  git init -q -b main || die "git init failed."
  say "Initialized git in $PROJECT"
fi
git remote get-url origin >/dev/null 2>&1 || git remote add origin "https://github.com/$REPO.git"

# ---------------------------------------------------------- safety: never publish real data or secrets
for bad in raw state _site .env bundle_keys.json .execscorecard-token; do
  if git ls-files --error-unmatch "$bad" >/dev/null 2>&1; then die "'$bad' is tracked by git — it must stay ignored. Nothing was pushed."; fi
done
if git ls-files site/config.local.json | grep -q .; then
  die "site/config.local.json is tracked — it carries real goals and must stay on this Mac. Nothing was pushed."
fi
if git ls-files site/data | grep -v '^site/data/sample/' | grep -q .; then
  die "Real data files under site/data/ are tracked — only site/data/sample/ may be published. Nothing was pushed."
fi

# ---------------------------------------------------------- commit
MSG="${1:-Update ExecScorecard $(date '+%Y-%m-%d %H:%M')}"
git add -A
# second guard, after staging: nothing private may be about to go up, whatever .gitignore says
if git diff --cached --name-only | grep -E '^site/config\.local\.json$|^site/data/' | grep -v '^site/data/sample/' | grep -q .; then
  git reset -q
  die "Private files were staged (site/config.local.json or site/data/ outside sample/). Unstaged them; nothing was pushed."
fi
if git diff --cached --quiet; then
  echo "Nothing new to commit."
else
  git -c user.name="Troy Myler" -c user.email="troy@biggrovebrewery.com" commit -q -m "$MSG" || die "Commit failed."
  say "Committed: $MSG"
fi

# ---------------------------------------------------------- reconcile with GitHub
GIT_TERMINAL_PROMPT=0 git fetch -q "$AUTH_URL" main 2>/dev/null && HAVE_REMOTE=1 || HAVE_REMOTE=0
if [ "$HAVE_REMOTE" = "1" ]; then
  if ! git merge-base HEAD FETCH_HEAD >/dev/null 2>&1; then
    echo "GitHub has unrelated history — merging it in, keeping our files."
    git -c user.name="Troy Myler" -c user.email="troy@biggrovebrewery.com" merge -q --allow-unrelated-histories -X ours FETCH_HEAD -m "Merge GitHub initial commit" || die "Merge failed — resolve in the folder and rerun."
  elif ! git merge-base --is-ancestor FETCH_HEAD HEAD; then
    echo "GitHub has newer commits — rebasing ours on top."
    git -c user.name="Troy Myler" -c user.email="troy@biggrovebrewery.com" rebase -q FETCH_HEAD || die "Rebase failed — resolve in the folder and rerun."
  fi
fi

# ---------------------------------------------------------- push
say "Pushing to GitHub..."
OUT=$(GIT_TERMINAL_PROMPT=0 git push "$AUTH_URL" HEAD:main 2>&1); RC=$?
echo "${OUT//$TOKEN/********}"
if [ $RC -ne 0 ]; then
  if echo "$OUT" | grep -qi 'workflow'; then
    die "GitHub refused the workflow file — the Keychain token needs the 'workflow' scope. Edit the token at https://github.com/settings/tokens, tick 'workflow', and run this again."
  fi
  if echo "$OUT" | grep -qiE 'denied|authentication|403|401'; then
    security delete-generic-password -s "$KC_SERVICE" -a "$GH_USER" >/dev/null 2>&1
    die "GitHub rejected the token (it was removed from the Keychain — run this again and paste a token with 'repo' and 'workflow' scopes)."
  fi
  die "Push failed — see above."
fi
git fetch -q origin 2>/dev/null; git branch -q --set-upstream-to=origin/main main 2>/dev/null || true

# ---------------------------------------------------------- make sure Pages is on (publishes from the Actions workflow)
CODE=$(gh_api "$API/repos/$REPO/pages")
if [ "$CODE" = "404" ]; then
  CODE=$(gh_api -X POST "$API/repos/$REPO/pages" -d '{"build_type":"workflow"}')
  if [ "$CODE" = "201" ]; then
    say "GitHub Pages turned on. Starting the first publish..."
    gh_api -X POST "$API/repos/$REPO/actions/workflows/pages.yml/dispatches" -d '{"ref":"main"}' >/dev/null
  else
    cat /tmp/execsc_api.json
    echo "Could not turn on Pages automatically (HTTP $CODE). In the repo: Settings → Pages → Source: GitHub Actions, then run this again."
  fi
fi
rm -f /tmp/execsc_api.json

say "Done. Publishing takes about a minute: $ACTIONS_URL"
say "Scorecard: $SITE_URL"
[ "${2:-}" = "--quiet" ] || { read -n1 -s -r -p "Press any key to close..."; echo; }
