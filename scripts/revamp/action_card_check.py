#!/usr/bin/env python3
"""Local PDF output/link/bounds verification and inspectable preview artifacts."""
import json,re,subprocess,time
from pathlib import Path
from xml.etree import ElementTree
from harness import ROOT
from revamp.engine import Engine
from revamp import action_card,playbook

out=ROOT/'runtime/account-card-proof';out.mkdir(parents=True,exist_ok=True)
engine=Engine(out/'database');room,token=engine.experience('card-proof-'+str(int(time.time())))
for _ in range(8):engine.advance(room)
room['teams']['1'].update(score=1500,trust=98,risk=25500,fast=0,robot_uses={role:3 for role in ['SCOUT','SHERLOCK','SHIELD','PATCH','SCRIBE']})
room['card']={'account':'Northwind opportunity planning','next_step':'Invite the customer’s technical champion to a local AI discovery session and agree one workflow to evaluate.'}
report=[]
try:
    for kind in ['standard','long-fields-and-approved-story']:
        if kind!='standard':
            room['card']={'account':('Long account name '+ 'Enterprise Customer Opportunity Planning '*2)[:80],'next_step':('Discuss a local AI pilot with the business owner, IT, the AI team and the security lead. '*3)[:200]}
            story=out/'story.json';story.write_text(json.dumps({'stories':[{'approved':True,'title':'Approved internal story','text':('Approved internal copy for layout validation only. '*10)[:420],'approval_reference':'Layout test only'}]}))
            playbook.STORY_PATH=story
        pdf=out/(kind+'.pdf');pdf.write_bytes(action_card.render_action_card(room))
        info=subprocess.check_output(['pdfinfo',str(pdf)],text=True);pages=int(re.search(r'Pages:\s+(\d+)',info)[1])
        bbox=pdf.with_suffix('.xml');subprocess.run(['pdftotext','-bbox',str(pdf),str(bbox)],check=True)
        tree=ElementTree.fromstring(bbox.read_text());ns={'h':'http://www.w3.org/1999/xhtml'}
        page=tree.find('.//h:page',ns);words=tree.findall('.//h:word',ns);width=float(page.attrib['width']);height=float(page.attrib['height'])
        inside=all(float(w.attrib['xMin'])>=24 and float(w.attrib['xMax'])<=width-24 and float(w.attrib['yMin'])>=24 and float(w.attrib['yMax'])<=height-24 for w in words)
        subprocess.run(['pdftoppm','-scale-to','1600','-png','-singlefile',str(pdf),str(pdf.with_suffix(''))],check=True,capture_output=True)
        text=subprocess.check_output(['pdftotext',str(pdf),'-'],text=True)
        links=[r['url'] for r in action_card.RESOURCES]
        links+= [action_card.SOURCE_BY_ID[k]['url'] for k in ['rhel','redhat_hp']]
        annotations=subprocess.check_output(['pdfinfo','-url',str(pdf)],text=True)
        links_present=all(url in annotations for url in links)
        normalized=' '.join(text.split())
        capabilities=all(item['title'] in normalized for item in action_card.DIFFERENTIATORS['items'])
        qualifications=all(phrase in normalized for phrase in ['listed hardware/OS configurations','200–240V','integration as planned','not measured outcomes'])
        assert pages==1 and inside and links_present and capabilities and qualifications and 'Product availability' in text
        report.append({'variant':kind,'pages':pages,'all_text_inside_printable_bounds':inside,'official_source_links':links,'all_links_in_pdf_annotations':links_present,'differentiators':len(action_card.DIFFERENTIATORS['items']),'all_differentiators_present':capabilities,'scope_qualifications_present':qualifications,'pdf':str(pdf),'preview':str(pdf.with_suffix('.png'))})
finally:engine.db.close()
(ROOT/'docs/single-experience-card.json').write_text(json.dumps({'passed':True,'variants':report},indent=2));print(json.dumps(report,indent=2))
