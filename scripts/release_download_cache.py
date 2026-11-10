"""Release only this repo's clean download page cache on unified memory Grace.

This is advisory, does not delete files, and never uses global drop_caches.
"""
from pathlib import Path
import os
root=Path(__file__).resolve().parents[1]/'runtime/huggingface'
count=0
for path in root.rglob('*'):
    if path.is_file() and not path.is_symlink() and path.stat().st_size>1024*1024:
        with path.open('rb') as stream:
            os.posix_fadvise(stream.fileno(),0,0,os.POSIX_FADV_DONTNEED)
        count+=1
print(f'Advised release of clean pages from {count} repository download files; no files deleted.')
