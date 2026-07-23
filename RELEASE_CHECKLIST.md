# Release checklist

## Code

- [ ] Version updated in `pyproject.toml`
- [ ] Version updated in `src/limitforge/__init__.py`
- [ ] `CHANGELOG.md` release date and changes updated
- [ ] `CITATION.cff` version and date updated
- [ ] Unit tests pass
- [ ] Redis integration tests pass
- [ ] Django demo starts and returns HTTP 429 correctly
- [ ] Coverage remains at or above configured threshold
- [ ] Lint and type checks pass

## Package

- [ ] Distribution name confirmed immediately before publication
- [ ] Wheel and source distribution built
- [ ] `twine check dist/*` passes
- [ ] Lua scripts and `py.typed` present in wheel
- [ ] Wheel installs in a clean environment
- [ ] TestPyPI install verified

## Documentation

- [ ] README numbers reproduce on documented machine
- [ ] Redis benchmark added; no placeholders remain in resume
- [ ] Installation commands tested
- [ ] Repository links and author information correct
- [ ] Security reporting method enabled

## GitHub and PyPI

- [ ] Main branch protected
- [ ] CI green on release commit
- [ ] GitHub `pypi` environment created
- [ ] PyPI trusted publisher configured for `publish.yml`
- [ ] Annotated version tag pushed
- [ ] GitHub release notes reviewed
- [ ] Published package smoke-tested from PyPI
