# Contributing

Thanks for your interest in contributing to TongSIM.

## Development setup (Python SDK)

- Python: 3.12+
- Recommended: [`uv`](https://docs.astral.sh/uv/)

```powershell
uv venv
uv sync --all-groups
```

## Lint / format

```powershell
uv run ruff check
uv run ruff format
```

## Protobuf (gRPC) code generation

```powershell
uv run python scripts/generate_pb2.py
```

## Docs

```powershell
uv run mkdocs serve
```

## Pull requests

- Keep changes focused and include a clear description.
- If you add or change APIs, please update `docs/` accordingly.

By submitting a pull request, you agree that your contribution will be licensed under the terms in `LICENSE`.
