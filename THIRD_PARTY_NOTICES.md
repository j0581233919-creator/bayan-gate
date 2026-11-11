# Dependency & Attribution Notices

The implementation, automated test suites, and documentation of `bayan-gate` were written specifically for this project with AI assistance. They are distributed under the [MIT License](LICENSE) using the collective attribution "BayanGate Contributors".

## Zero External Dependencies

- **Runtime & Tests**: The package and its automated test suites run exclusively on the standard library of Python 3.10+.
- **No Third-Party Packages**: Zero external PyPI dependencies (`dependencies = []` declared in `pyproject.toml`).
- **No Bundled Binaries or Vendor Trees**: No proprietary binaries, pre-compiled wheels, or web fonts are distributed with this software.

## Python Runtime Notice

Users supply their own Python interpreter. Python and its standard library modules (`re`, `unicodedata`, `hashlib`, `hmac`, `dataclasses`, `enum`, `typing`, `argparse`, `json`, `calendar`, `datetime`, `unittest`) are licensed under the [Python Software Foundation License](https://docs.python.org/3/license.html). The MIT License of `bayan-gate` applies strictly to this project's source code and does not relicense Python or its standard library.
