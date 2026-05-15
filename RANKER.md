# Ranker — setup

The ranker is two static pages served from GitHub Pages:

- `index.html` — public homepage. Reads `feed.xml` + `ratings.json` + `blocklist.json` from the same origin. Polls every 5 minutes.
- `rank.html` — private feeder. Password-gated. Commits ratings back to the repo via the GitHub API.

`ratings.json` (`{url: 0–5}`) and `blocklist.json` (`[url, …]`) live at the repo root. The daily pipeline ignores `ratings.json` and respects `blocklist.json` (drops any blocked URL from the feed).

## One-time setup

### 1. Enable GitHub Pages

Repo Settings → Pages → "Build and deployment" → Source: **Deploy from a branch** → Branch: `main` / `/ (root)` → Save.

Site URL will be `https://emteev.github.io/yaain/`.

### 2. Set the ranker password

Pick a password and hash it:

```sh
echo -n "yourpassword" | shasum -a 256
```

Open `rank.html`, find `PASSWORD_SHA256`, replace the hex string. Commit.

### 3. Generate a GitHub personal access token

GitHub → Settings → Developer settings → Personal access tokens → **Fine-grained tokens** → Generate new.

- Resource owner: your account
- Repository access: **Only select repositories** → `emteev/yaain`
- Repository permissions → **Contents: Read and write**
- Expiration: your call (90 days is fine)

Copy the token. Open `rank.html` in your browser, enter password + paste the token once. Both are stored in `localStorage` and only sent to `api.github.com`.

## Rating scale

| Rank | Where it appears |
|---|---|
| 0 | Hidden (default for unrated) |
| 1 | Hero — full-width headline, summary + why, byline |
| 2 | Featured — 2 columns, headline + one paragraph |
| 3 | Brief — 4 columns, short summary |
| 4 | Bullet — headline · publication · date |
| 5 | Deleted — added to `blocklist.json`; dropped from `feed.xml` on next run |

Move 5 → anything else to un-block.

## Failure modes

**Save fails with 409/422** — someone else (or another tab) wrote to the file first. The feeder re-fetches the SHA and retries once. If it still fails, reload the page.

**Pages serves stale ratings** — cache-busted query strings are appended on every fetch, but GitHub's raw CDN can lag ~1 minute behind a commit. Just wait.

**Password forgotten** — you set the hash; re-hash a new password and replace the constant in `rank.html`.
