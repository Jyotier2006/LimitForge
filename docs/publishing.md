# Publishing to PyPI

## 0. Confirm the name

Immediately before first publication, open the PyPI project URL and confirm the
distribution name is still available. A previously observed 404 does not reserve
the name.

## 1. Replace pre-release details

- verify author and repository URLs in `pyproject.toml`;
- update version in `pyproject.toml` and `src/limitforge/__init__.py`;
- update `CHANGELOG.md` and `CITATION.cff`;
- confirm README installation commands;
- run all quality checks.

## 2. Build and validate

```bash
python -m pip install -U build twine
rm -rf dist build
python -m build
python -m twine check dist/*
```

Inspect both the source archive and wheel:

```bash
tar -tf dist/*.tar.gz
python -m zipfile -l dist/*.whl
```

Confirm that Lua files, `py.typed`, README, and license are included.

## 3. Test in a clean environment

```bash
python -m venv /tmp/limitforge-release-test
source /tmp/limitforge-release-test/bin/activate
pip install dist/*.whl
python -c "from limitforge import RateLimiter; print(RateLimiter())"
```

## 4. TestPyPI

Create a TestPyPI account and upload:

```bash
python -m twine upload --repository testpypi dist/*
```

Install from TestPyPI while allowing dependencies from normal PyPI:

```bash
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  limitforge
```

## 5. Configure trusted publishing

In PyPI, create a pending trusted publisher with:

- owner: `Jyotier2006`;
- repository: `limitforge`;
- workflow: `publish.yml`;
- environment: `pypi`.

Create a protected GitHub environment named `pypi`. The included workflow uses
GitHub OIDC and requests `id-token: write`; it does not require a long-lived PyPI
API token.

## 6. Release

1. Merge a release pull request.
2. Create and push tag `v0.1.0`.
3. Create a GitHub release from the tag.
4. The workflow builds, validates, uploads artifacts, and publishes.
5. Install the published wheel in a fresh environment and run a smoke test.

Package releases are immutable. If metadata or code is wrong, publish a new
version rather than attempting to replace files.
