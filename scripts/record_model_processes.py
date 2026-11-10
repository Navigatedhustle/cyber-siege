#!/usr/bin/env python3
"""Map known model container IDs to NVML host PIDs without guessing by memory size."""
import json
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
result={}
for key,name in [('hero','hp-nemotron-serve'),('challenger','cyber-siege-challenger')]:
    p=subprocess.run(['sg','docker','-c',f"docker inspect --format '{{{{.Id}}}}' {name}"],capture_output=True,text=True,timeout=5)
    if p.returncode==0:result[p.stdout.strip()]=key
(ROOT/'runtime/model-containers.json').write_text(json.dumps(result,indent=2))
print('Recorded model container identities for GPU process attribution.')
