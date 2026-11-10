#!/usr/bin/env python3
"""Make only the public Nemotron snapshot and referenced blobs readable by UID 10001."""
from pathlib import Path
import sys


def prepare(cache):
    cache=Path(cache).resolve()
    repo=cache/'models--nvidia--NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4'
    shared=cache/'blobs'
    if repo.is_symlink() or not repo.is_dir():
        raise ValueError('Expected a real downloaded public model repository.')
    paths={repo}
    for path in repo.rglob('*'):
        if not path.is_symlink():
            paths.add(path)
            continue
        target=path.resolve(strict=True)
        boundary=repo if target.is_relative_to(repo) else shared
        if not target.is_relative_to(boundary) or not target.is_file():
            raise ValueError('Model symlink escapes the public artifact cache.')
        paths.add(target)
        for parent in target.parents:
            paths.add(parent)
            if parent==boundary:
                break
    # Validate every reference before changing any permissions.
    for path in paths:
        path.chmod(path.stat().st_mode | (0o555 if path.is_dir() else 0o444))


if __name__=='__main__':prepare(sys.argv[1])
