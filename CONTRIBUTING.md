# Contributing

Contributions are welcome, and they are greatly appreciated! Every little bit
helps, and credit will always be given.

## Types of contributions

### Report bugs

Report bugs at https://github.com/obulat/zeyrek/issues.

If you are reporting a bug, please include:

- Your Python, NLTK and Zeyrek versions, and your operating system.
- The words or text you analyzed, what Zeyrek returned, and what you expected.

### Fix bugs and implement features

Look through the GitHub issues. Anything tagged with "bug" or "enhancement" and
"help wanted" is open to whoever wants to implement it.

### Write documentation

Zeyrek could always use more documentation, whether in the official docs, in
docstrings, or on the web in blog posts and articles.

### Submit feedback

The best way to send feedback is to file an issue at
https://github.com/obulat/zeyrek/issues.

If you are proposing a feature:

- Explain in detail how it would work.
- Keep the scope as narrow as possible, to make it easier to implement.
- Remember that this is a volunteer-driven project, and that contributions are
  welcome :)

## Get started

1. Fork the `zeyrek` repo on GitHub, and clone your fork:

   ```shell
   git clone git@github.com:your_name_here/zeyrek.git
   ```

2. Install [uv](https://docs.astral.sh/uv/), then create the virtualenv with the
   package and its dev and docs dependencies:

   ```shell
   cd zeyrek/
   uv sync
   uvx pre-commit install
   ```

   The pre-commit hooks format and lint the code with Ruff on every commit.

3. Create a branch for your change:

   ```shell
   git switch -c name-of-your-bugfix-or-feature
   ```

4. When you're done, run the tests, including on the oldest supported Python
   version, and format and lint the code:

   ```shell
   uv run pytest
   uv run --python 3.10 pytest
   uv run ruff format
   uv run ruff check --fix
   ```

   To run a subset of tests:

   ```shell
   uv run pytest tests/test_analysis.py -k stem_transition
   ```

   Build the docs once, or serve them with live reload:

   ```shell
   uv run make -C docs html
   uv run sphinx-autobuild docs/ docs/_build/ --watch zeyrek/
   ```

5. Commit your changes, push your branch to GitHub, and open a pull request.

## Pull request guidelines

1. The pull request should include tests.
2. If the pull request adds functionality, update the docs in `docs/` and, for
   user-facing changes, the README.
3. CI must pass on every Python version in `.github/workflows/ci.yml`.

## Releasing

The version lives only in `pyproject.toml`; the package and the docs read it
from there. Bump it with `uv version --bump` (`patch`, `minor`, `major`,
`alpha`, `beta`, `rc` or `stable`), then commit, tag and push:

```shell
uv version --bump patch
git commit -am "Release $(uv version --short)"
git tag "v$(uv version --short)"
git push --follow-tags
```

Then create a GitHub release from the tag, with "Generate release notes". Publishing
the release uploads the package to PyPI.
