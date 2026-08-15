# Cloudflare Deployment

This repo is configured for a Cloudflare Worker at:

```text
https://lumen.ompatnaik.com
```

The deployed Worker hosts the public Lumen website from `public/`. The site is the install/run hub: it provides copyable commands, serves `/install.sh`, checks for a local Lumen console at `http://127.0.0.1:8765`, and links into that local console when available.

The macOS desktop agent in `lumen/` still runs locally; Cloudflare Workers cannot run macOS automation, local Ollama, MLX Whisper, or desktop app controls.

## One-Time Local Setup

Wrangler is the Cloudflare CLI:

```sh
npm install -g wrangler
wrangler login
wrangler whoami
```

This machine currently has Wrangler installed globally. Authentication is stored by Wrangler outside the repo.

## Local Development

```sh
npm install
npm run dev
```

Wrangler will serve the Worker and static assets locally.

## Deploy From This Machine

```sh
npm run deploy
```

The `wrangler.toml` file maps the Worker to `lumen.ompatnaik.com` with:

```toml
[[routes]]
pattern = "lumen.ompatnaik.com"
custom_domain = true
```

Cloudflare requires `ompatnaik.com` to be an active Cloudflare zone. If an existing DNS record already uses `lumen.ompatnaik.com`, remove or replace it before deploying the custom domain.

## GitHub Pull Deployment

In Cloudflare:

1. Go to Workers & Pages.
2. Create or open the `lumen` Worker.
3. Connect the GitHub repo `OmTheLast/Lumen`.
4. Use `main` as the production branch.
5. Use this build/deploy command:

```sh
npm install && npm run deploy
```

6. Keep the Worker config file as `wrangler.toml`.

For repository-driven deploys, prefer a scoped Cloudflare API token in Cloudflare/GitHub settings instead of personal interactive login. Required scopes are typically account read plus Workers scripts/routes write and zone read for the target zone.

## Useful Checks

```sh
wrangler whoami
npm run check
npm run deploy -- --dry-run
curl https://lumen.ompatnaik.com/api/health
```
