from autowheel.autowheel import process
import sys

duckdb_version, python_version = sys.argv[1:]

process(
    package_name='duckdb',
    platform_tag='linux64',
    before_build='pip install oldest-supported-numpy',
    test_command='python3 -c "import duckdb"',
    test_requires=[],
    output_dir='wheels',
    python_versions={duckdb_version: [python_version]}
)
