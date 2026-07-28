# Contributing

Thank you for your interest in Peripatos! This guide will help you get started.

## Development Setup

```bash
git clone https://github.com/yu-zou/Peripatos.git
cd Peripatos
pip install -e .
```

## Running Tests

All tests run inside Docker:

```bash
# Unit tests (mocked providers)
docker compose run --rm test pytest -v

# Integration tests (requires real API keys in config)
RUN_INTEGRATION=1 docker compose run --rm test pytest -v -m integration

# Real-LLM end-to-end test
# Requires Peripatos/config.test.json with API key
RUN_INTEGRATION=1 docker compose run --rm test pytest -v tests/test_e2e.py

# Python 3.14 wheel-install smoke test (optional)
docker compose run --rm install-test
```

The `install-test` service builds a wheel from source, installs it into a fresh
Python 3.14 environment, and verifies `peripatos --help`, `list-archetypes`,
and provider imports all work correctly.

## Code Quality

- **Line length**: 100 characters max
- **Python version**: 3.10+
- **Formatting**: Follow the existing style in the codebase
- **Tests**: Add tests for new features. Run the full test suite before submitting.

## Pull Request Process

1. Ensure your fork is up to date with `main`
2. Create a feature branch
3. Make your changes and add tests
4. Run the test suite and confirm it passes
5. Open a PR against the `main` branch
6. Describe what your change does and why

## Project Structure

```
peripatos_core/
    cli.py              # CLI entry point (typer)
    config.py           # Configuration loading & resolution
    dialogue.py         # Dialogue generation pipeline
    rag.py              # ReAct RAG agent
    parser.py           # PDF/HTML/MD parsing
    audio.py            # Audio synthesis & MP3 assembly
    registry.py         # TTS provider registry & voice selection
    cache.py            # Audio & dialogue caching
    prompts/
        archetypes/     # YAML archetype prompts (peer, skeptic, tutor, enthusiast)
        system.txt      # System prompt template
        react.txt       # ReAct agent prompt template
tests/
    test_*.py           # Unit tests
    test_e2e.py         # End-to-end integration test
    fixtures/           # Test fixtures
```

## License

By contributing, you agree that your contributions will be licensed under the
[MIT License](LICENSE).