"""NVML observations only. Missing telemetry stays absent, never zero filled."""
import json
import re
from pathlib import Path
from app.config import ROOT, settings
import pynvml

class GPU:
    def __init__(self):
        self.handle=None
        if not settings.gpu_telemetry_enabled:return
        try:
            pynvml.nvmlInit()
            self.handle=pynvml.nvmlDeviceGetHandleByIndex(0)
        except pynvml.NVMLError:
            self.handle=None

    def sample(self):
        if self.handle is None: return None
        try:
            h=self.handle
            memory=pynvml.nvmlDeviceGetMemoryInfo(h)
            processes=[]
            try: known=json.loads((ROOT/'runtime/model-containers.json').read_text())
            except (OSError,ValueError):known={} 
            try:
                for p in pynvml.nvmlDeviceGetComputeRunningProcesses(h):
                    used=p.usedGpuMemory
                    model=None
                    try:
                        group=Path(f'/proc/{p.pid}/cgroup').read_text()
                        for container_id,key in known.items():
                            if container_id in group:model=key
                    except OSError:pass
                    processes.append({'pid':p.pid,'model':model,'memory_bytes':used if used and used<2**60 else None})
            except pynvml.NVMLError: pass
            return dict(name=pynvml.nvmlDeviceGetName(h),utilization=pynvml.nvmlDeviceGetUtilizationRates(h).gpu,
                        power_watts=pynvml.nvmlDeviceGetPowerUsage(h)/1000,memory_used_bytes=memory.used,
                        memory_total_bytes=memory.total,processes=processes)
        except pynvml.NVMLError: return None
