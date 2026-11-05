#!/usr/bin/env bash
# Install the skills used for the hackathon video (brag + HyperFrames + an optional comedy-writing skill)
# into .claude/skills/ at project level, pinned to tested commits. Third-party code: the installed folders are
# in .gitignore, like vendor/. Re-run it any time: it overwrites the installed copies.
#
#   ./scripts/install-video-skills.sh            # install
#   ./scripts/install-video-skills.sh --doctor   # install, then check the HyperFrames environment
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/.claude/skills"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# repo | commit | path inside the repo | installed name
SKILLS=(
  "latent-spaces/brag|669ab9286aa28b6c3ee30e75f181ee74319d012a|skills/brag|brag"
  "latent-spaces/brag|669ab9286aa28b6c3ee30e75f181ee74319d012a|skills/brag-slim|brag-slim"
  "heygen-com/hyperframes|a6e6717f2ae9bc547505d9c5d916e4dcb341d630|skills/hyperframes|hyperframes"
  "heygen-com/hyperframes|a6e6717f2ae9bc547505d9c5d916e4dcb341d630|skills/hyperframes-cli|hyperframes-cli"
  "heygen-com/hyperframes|a6e6717f2ae9bc547505d9c5d916e4dcb341d630|skills/hyperframes-registry|hyperframes-registry"
  "heygen-com/hyperframes|a6e6717f2ae9bc547505d9c5d916e4dcb341d630|skills/media-use|media-use"
  "pantheon-org/tekhne|fa20b1d7dfe109789cb0f7773dad708f7962d835|skills/comedy/cunk-esque-mockumentary|cunk-esque-mockumentary"
)

fetch() {  # fetch <owner/repo> <commit> -> prints the checkout dir
  local repo="$1" commit="$2" dir="$TMP/${1//\//__}"
  if [ ! -d "$dir" ]; then
    git init -q "$dir"
    git -C "$dir" remote add origin "https://github.com/$repo.git"
    git -C "$dir" sparse-checkout set --no-cone /skills/
    GIT_LFS_SKIP_SMUDGE=1 git -C "$dir" fetch -q --depth 1 --filter=blob:none origin "$commit"
    GIT_LFS_SKIP_SMUDGE=1 git -C "$dir" -c advice.detachedHead=false checkout -q FETCH_HEAD
  fi
  echo "$dir"
}

mkdir -p "$DEST"
for entry in "${SKILLS[@]}"; do
  IFS='|' read -r repo commit path name <<<"$entry"
  src="$(fetch "$repo" "$commit")/$path"
  [ -f "$src/SKILL.md" ] || { echo "missing $repo/$path/SKILL.md" >&2; exit 1; }
  rm -rf "${DEST:?}/$name"
  cp -R "$src" "$DEST/$name"
  rm -rf "$DEST/$name/.audits" "$DEST/$name/evals"
  echo "installed $name  ($repo@${commit:0:7})"
done

if [ "${1:-}" = "--doctor" ]; then
  node --version; ffmpeg -version | head -1
  npx --yes hyperframes doctor
fi
