#!/usr/bin/env python3
"""Record sampled TCP peers and byte counters; absence is not proof of zero egress."""
import argparse
import ipaddress
import json
import subprocess
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def docker(*args):
    result=subprocess.run(['sg','docker','-c', ' '.join(args)],capture_output=True,text=True)
    return result.stdout.strip()

def ipv4(raw):
    address,port=raw.split(':')
    return str(ipaddress.ip_address(bytes.fromhex(address)[::-1]))+':'+str(int(port,16))

def sample():
    value={'timestamp':time.time(),'containers':{}}
    for name in ['hp-nemotron-serve','cyber-siege-challenger']:
        raw=docker('docker','exec',name,'cat','/proc/net/tcp')
        sockets=[]
        for line in raw.splitlines()[1:]:
            parts=line.split()
            if len(parts)>3:
                sockets.append({'local':ipv4(parts[1]),'remote':ipv4(parts[2]),'state_hex':parts[3]})
        stats=docker('docker','stats','--no-stream','--format',"'{{json .}}'",name)
        processes=docker('docker','top',name,'-eo','pid,comm')
        value['containers'][name]={'sockets':sockets,'docker_stats_raw':stats,'processes':processes}
    return value

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seconds',type=int,default=120);p.add_argument('--output',default='docs/container-load-observations.jsonl');args=p.parse_args()
    end=time.monotonic()+args.seconds
    with (ROOT/args.output).open('a') as stream:
        while time.monotonic()<end:
            stream.write(json.dumps(sample())+'\n');stream.flush();time.sleep(2)
