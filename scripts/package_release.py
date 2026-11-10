#!/usr/bin/env python3
"""Create a source snapshot from the explicit distribution policy, never a worktree tar."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def selected_files(root=ROOT):
    policy=json.loads((root/'config/distribution-files.json').read_text())
    selected=set(policy['files'] + policy['config_files'] + ['docs/'+p for p in policy['docs']])
    for folder in policy['trees'] + policy['screenshot_trees']:
        selected.update(p.relative_to(root).as_posix() for p in (root/folder).rglob('*') if p.is_file())
    result=[]
    for name in sorted(selected):
        p=Path(name)
        if name in policy['excluded_files'] or any(part in policy['excluded_parts'] for part in p.parts) or p.suffix in policy['excluded_suffixes']:
            continue
        if p.is_absolute() or '..' in p.parts or (root/p).is_symlink():
            raise ValueError('Unsafe distribution entry: '+name)
        if not (root/p).is_file():
            raise ValueError('Missing distribution entry: '+name)
        result.append(name)
    return result


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();files=selected_files()
    dest=args.output.resolve()
    if dest==ROOT or ROOT in dest.parents:
        raise SystemExit('Release output must be outside the working repository.')
    dest.mkdir(parents=True,exist_ok=True)
    version=json.loads((ROOT/'config/distribution-files.json').read_text())['version']
    tree=dest/('cyber-siege-v'+version)
    if tree.exists():
        raise SystemExit('Use a new output directory; existing snapshots are preserved.')
    tree.mkdir()
    sums=[]
    for name in files:
        target=tree/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/name,target)
        sums.append(hashlib.sha256(target.read_bytes()).hexdigest()+'  '+name)
    (tree/'SOURCE_SHA256SUMS').write_text('\n'.join(sums)+'\n')
    with zipfile.ZipFile(dest/(tree.name+'.zip'),'w',zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(tree.rglob('*')):
            if p.is_file():archive.write(p,p.relative_to(dest))
    with tarfile.open(dest/(tree.name+'.tar.gz'),'w:gz') as archive:
        archive.add(tree,arcname=tree.name)
    print(json.dumps({'source_files':len(files),'snapshot':str(tree),'archives':[tree.name+'.zip',tree.name+'.tar.gz']},indent=2))


if __name__=='__main__':main()
