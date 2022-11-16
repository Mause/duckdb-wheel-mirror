import os
import sys
import tarfile
import tempfile
from fnmatch import fnmatch

import requests
from autowheel.config import PYTHON_TAGS
from cibuildwheel.__main__ import main as cibuildwheel


def process(platform_tag: str, before_build: str, package_name: str,
            release_version: str,
            python_versions,
            output_dir,
            test_command,
            test_requires,
            build_existing=False,
            ) -> None:
    print('Processing {package_name}'.format(package_name=package_name))

    # Prepare PyPI URL
    pypi_data = requests.get('https://pypi.org/pypi/{package_name}/json'.format(package_name=package_name)).json()

    # Remember where we started - if anything goes wrong we'll go back there
    # at the end.
    start_dir = os.path.abspath('.')

    print('Release: {release_version}... '.format(release_version=release_version), end='')

    # Figure out which Python versions are requested in the config
    required_pythons = python_versions

    # Now determine which Python versions have already been built for the
    # target OS and are on PyPI. Note that for a given platform there are
    # multiple possible tags. If *any* of the platform tags match, we
    # consider the wheel already built.

    files = pypi_data['releases'][release_version]

    wheels_pythons = []
    sdist = None
    for fileinfo in files:
        if fileinfo['packagetype'] == 'bdist_wheel':
            filename = fileinfo['filename']
            if fnmatch(filename, '*{0}*'.format(platform_tag)):
                for python_tag in PYTHON_TAGS:
                    if python_tag in filename:
                        wheels_pythons.append(python_tag)
        elif fileinfo['packagetype'] == 'sdist':
            sdist = fileinfo

    if build_existing:
        missing = sorted(set(required_pythons))
    else:
        missing = sorted(set(required_pythons) - set(wheels_pythons))
        if not missing:
            print('all wheels present')
            return

    print('missing wheels:', missing)

    # We now build the missing wheels
    try:
        call_cibuildwheel(before_build, missing, output_dir, platform_tag, sdist, test_command, test_requires)
    finally:

        os.chdir(start_dir)


def call_cibuildwheel(before_build: str, missing, output_dir, platform_tag, sdist, test_command, test_requires) -> None:
    tmpdir = tempfile.mkdtemp()
    print('Changing to {0}'.format(tmpdir))
    os.chdir(tmpdir)

    print('  Fetching {url}'.format(**sdist))
    req = requests.get(sdist['url'])
    with open(sdist['filename'], 'wb') as f:
        f.write(req.content)

    print('  Expanding {filename}'.format(**sdist))
    tar = tarfile.open(sdist['filename'], 'r:gz')
    tar.extractall(path='.')
    # Find directory name
    paths = os.listdir('.')
    paths.remove(sdist['filename'])
    if len(paths) > 1:
        raise ValueError('Unexpected files/directories:', paths)

    print('  Go into directory {0}'.format(paths[0]))
    os.chdir(paths[0])
    # We now configure cibuildwheel via environment variables

    print('  Running cibuildwheel')
    sys.argv = ['cibuildwheel', '.']
    if 'mac' in platform_tag:
        os.environ['CIBW_PLATFORM'] = 'macos'
    elif 'linux' in platform_tag:
        os.environ['CIBW_PLATFORM'] = 'linux'
    else:
        os.environ['CIBW_PLATFORM'] = 'windows'
    os.environ['CIBW_OUTPUT_DIR'] = str(output_dir)
    if test_command:
        os.environ['CIBW_TEST_COMMAND'] = str(test_command)
    if test_requires:
        os.environ['CIBW_TEST_REQUIRES'] = str(test_requires)
    os.environ['CIBW_BUILD_VERBOSITY'] = '3'

    for python_tag in missing:
        os.environ['CIBW_BUILD'] = "{0}-{1}".format(python_tag, platform_tag)

        if before_build:
            os.environ['CIBW_BEFORE_BUILD'] = str(before_build)

        for key, value in os.environ.items():
            if key.startswith('CIBW'):
                print('{0}: {1}'.format(key, value))

        try:
            cibuildwheel()
        except SystemExit as exc:
            if exc.code != 0:
                raise


def main():
    os.environ['CIBW_ARCHS'] = 'native'

    duckdb_version, python_version = sys.argv[1:]

    process(
        package_name='duckdb',
        release_version=duckdb_version,
        platform_tag='*manylinux*',
        before_build='pip install oldest-supported-numpy',
        test_command='python3 -c "import duckdb"',
        test_requires='numpy',
        output_dir='wheels',
        python_versions=[python_version]
    )


if __name__ == '__main__':
    main()
