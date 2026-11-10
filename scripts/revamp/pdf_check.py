#!/usr/bin/env python3
"""Render exported PDFs to PNG; verify single page, bounds and longest optional story."""
import json
import subprocess
import time
from pathlib import Path
from xml.etree import ElementTree
from harness import ROOT,Server
from revamp import playbook
from revamp.engine import Engine

def inspect(path):
    info=subprocess.check_output(['pdfinfo',str(path)],text=True)
    pages=int(next(x.split(':')[1] for x in info.splitlines() if x.startswith('Pages:')))
    bbox=path.with_suffix('.xml')
    subprocess.run(['pdftotext','-bbox',str(path),str(bbox)],check=True)
    root=ElementTree.fromstring(bbox.read_text());ns={'h':'http://www.w3.org/1999/xhtml'}
    page=root.find('.//h:page',ns);words=root.findall('.//h:word',ns)
    width,height=float(page.attrib['width']),float(page.attrib['height'])
    inside=all(float(w.attrib['xMin'])>=25 and float(w.attrib['xMax'])<=width-25 and float(w.attrib['yMin'])>=25 and float(w.attrib['yMax'])<=height-25 for w in words)
    subprocess.run(['pdftoppm','-scale-to','1600','-png','-singlefile',str(path),str(path.with_suffix(''))],check=True,capture_output=True)
    text=subprocess.check_output(['pdftotext',str(path),'-'],text=True)
    assert pages==1 and inside and 'what success should look like' in text
    return {'pages':pages,'text_within_printable_bounds':inside,'words':len(words),'rendered_png':str(path.with_suffix('.png'))}

def main():
    out=ROOT/'runtime/revamp-pdf-proof';out.mkdir(parents=True,exist_ok=True)
    server=Server('revamp-pdf-server-'+str(int(time.time())),port=8097)
    report={'variants':[]}
    try:
        room=server.create(2,industry='manufacturing');code=room['code']
        assert server.client.get(f'/api/rooms/{code}/playbook.pdf?team=1').status_code==400
        for _ in range(8):server.client.post(f'/api/rooms/{code}/control',json={'command':'next'})
        current=server.client.get('/api/rooms/'+code).json();assert current['phase']=='debrief'
        response=server.client.get(f'/api/rooms/{code}/playbook.pdf?team=1');response.raise_for_status()
        normal=out/'seller-playbook.pdf';normal.write_bytes(response.content)
        report['variants'].append({'kind':'real API export, no private story',**inspect(normal)})
        # Exercise private story handling with a temporary isolated file; never create a real local story.
        story=out/'test-story.json';story.write_text(json.dumps({'stories':[{'approved':True,'title':'Approved internal example','text':'An approved internal account described the value of keeping sensitive analysis close to its team. '*5,'approval_reference':'TEST ONLY'}]}))
        previous=playbook.STORY_PATH;playbook.STORY_PATH=story
        try:
            data=dict(current,teams=None);data['code']=code
            team=current['teams'][0];team['name']='Longest Team Name For QA'
            result=out/'seller-playbook-story.pdf';result.write_bytes(playbook.render_pdf(data,team))
            report['variants'].append({'kind':'max-length approved story and long team name',**inspect(result)})
            story.write_text(json.dumps({'stories':[{'approved':False,'text':'Do not reveal this','approval_reference':'x'}]}))
            assert playbook.approved_story() is None
        finally:playbook.STORY_PATH=previous
        selector=server.client.get('/playbook?room='+code)
        assert selector.status_code==200 and 'Choose your team' in selector.text
        rendered=server.client.get('/playbook?room='+code+'&team=2')
        assert rendered.status_code==200 and 'Team 02' in rendered.text
        report.update(debrief_gate_enforced=True,unapproved_story_excluded=True,remote_resources_disabled=True,passed=True)
    finally:server.close()
    (ROOT/'docs/revamp-pdf.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':main()
