import pathlib
from packaging.version import Version

organization_name = "de.bendalab"
application_name = "AmpullaryUi"
application_version = Version("0.0.1")

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS_ROOT_FILE = pathlib.PosixPath.joinpath(PACKAGE_ROOT, "docs", "index.md")