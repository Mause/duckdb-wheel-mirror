from pathlib import Path
from shutil import copy

for filename in Path(__file__).parent.rglob('mirror/**/*'):
    if filename.is_symlink():
        source = str(filename.resolve())
        filename.unlink()
        copy(source, str(filename))
