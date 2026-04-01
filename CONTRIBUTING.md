# Contributing to Open Memory Capsule

First off — thank you. This project exists to be useful, and contributions make it better for everyone.

## How to Contribute

### Report a Bug
Open an issue with:
- What you did
- What you expected
- What actually happened
- Your OS, Python version, GPU (if relevant)

### Request a Feature
Open an issue describing:
- The problem you're trying to solve
- Why existing behavior doesn't cover it

### Submit Code

1. Fork the repo
2. Create a branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Add tests for new behavior
5. Run tests: `pytest tests/`
6. Open a PR

## Pull Request Rules

- `main` is protected and accepts changes via PR only
- Keep PRs focused and reasonably small
- Link an issue when possible (`Fixes #123`)
- Prefer squash merge to keep history clean

## Commit Messages

Use clear, imperative commit messages, for example:

- `feat: add telegram watcher retry logic`
- `fix: handle empty OCR result in image ingest`
- `docs: clarify Docker quick-start steps`

## Where to Contribute

### High-value areas (most impact):

| Area | What's needed | Difficulty |
|------|--------------|------------|
| **New integration** | Add a new platform watcher | Medium |
| **Web UI** | Simple search interface (React/plain HTML) | Medium |
| **Mobile app** | React Native app with share extension | Hard |
| **Browser extension** | Chrome/Firefox extension | Medium |
| **Improve search** | Better ranking, query understanding | Medium |
| **Tests** | More unit + integration tests | Easy |
| **Docs** | Setup guides, video tutorials | Easy |
| **Translations** | Translate README | Easy |

### Adding a New Integration

Each integration lives in `integrations/<platform>/`:

```python
# integrations/myplatform/watcher.py

class MyPlatformWatcher:
    def __init__(self, cfg, enqueue_fn):
        self.cfg = cfg
        self._enqueue = enqueue_fn

    async def start(self):
        # Watch for new content
        # Call self._enqueue("ingest_file", {...}) or
        #      self._enqueue("ingest_text", {...})
        pass
```

Then register it in `daemon/__main__.py` in `_start_integrations()`.

Add config fields in `config.py` and `config.yaml`.

That's it — the pipeline handles everything else.

### Adding a New AI Provider

Implement the two interfaces in `providers/base.py`:

```python
class MyProviderLLM(LLMProvider):
    async def extract_capsule_info(self, raw_content, source_app, ...) -> ExtractionResult:
        ...

    async def health_check(self) -> bool:
        ...
```

Register it in `providers/__init__.py`.

## Code Style

- Python 3.10+
- No formatter enforced — just be consistent with surrounding code
- Type hints where they add clarity
- Keep it simple — this project values readability over cleverness

## Questions?

Open an issue or start a Discussion. We're friendly.
