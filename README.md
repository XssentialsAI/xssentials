# xssentials

Internal Python client library for Xssentials' line-of-business APIs. It is the shared dependency
behind the two MCP servers:

- [`connectwise-mcp`](https://github.com/XssentialsAI/connectwise-mcp) — ConnectWise Manage tools
- [`dtools-cloud-mcp`](https://github.com/XssentialsAI/dtools-cloud-mcp) — D-Tools Cloud tools

You don't install this on its own — the MCP servers depend on it. The instructions below exist so
their `pip install` can resolve `xssentials`.

## Requirements

- macOS, Python 3.9+
- `pydantic >= 2.0` (installed automatically)

## Install

Clone it as a sibling of the MCP servers and install it editable. The MCP server READMEs walk you
through this; the short version:

```bash
git clone https://github.com/XssentialsAI/xssentials.git
pip install -e ./xssentials
```

Each MCP server's `pyproject.toml` declares `xssentials @ git+https://github.com/XssentialsAI/xssentials.git`.
Installing it editable first (as above) satisfies that dependency with no network fetch — which is
why the documented setup clones all three repos before running `pip install`.

## Layout

```
xssentials/
├── connectwise/client.py        ConnectWise Manage REST client (urllib, GET-only)
├── dtools/cloud/
│   ├── client.py                D-Tools Cloud RPC client (GET + 8 write endpoints)
│   ├── auth.py                  X-API-Key resolver (reads env var set by `op run`)
│   └── models.py                Pydantic models
└── shared/
    ├── formatters.py            Markdown table / card / pagination helpers
    ├── validators.py            check_payload_size, enforce_get_only
    └── auth_helpers.py          required_env / MissingEnvError
```

## Credentials

This library reads credentials from **environment variables only** — it never reads secrets from
disk. The MCP servers inject those variables at launch via `op run --env-file=...` (1Password CLI),
so plaintext keys never land in a file. See each server's README for the exact variables and the
1Password setup.

## Note on the D-Tools `BASIC_AUTH` constant

`dtools/cloud/client.py` contains a hardcoded `BASIC_AUTH` literal. Per D-Tools' own auth
documentation this is a **shared public constant** that every D-Tools tenant sends — it is not a
secret and is not tenant-specific. The per-tenant secret is the `X-API-Key`, which is supplied from
1Password at runtime, never committed. Even so, **keep this repository private.**

## License

Internal Xssentials tooling. ConnectWise and D-Tools are trademarks of their respective owners.
