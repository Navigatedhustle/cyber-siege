#!/usr/bin/env python3
"""Render the standalone, selectable-text installation manual without network access."""
from html import escape
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageBreak,
                              PageTemplate, Paragraph, Preformatted, Spacer)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT=Path(__file__).resolve().parents[1]
WIDTH,HEIGHT=A4
MARGIN=44
AVAILABLE=WIDTH-2*MARGIN
NAVY=colors.HexColor('#071321')
BLUE=colors.HexColor('#004BDF')


def inline(text):
    text=escape(text)
    text=re.sub(r'`([^`]+)`',r'<font name="Courier">\1</font>',text)
    text=re.sub(r'\*\*([^*]+)\*\*',r'<b>\1</b>',text)
    text=re.sub(r'(https?://[^\s<]+)',r'<link color="#004BDF" href="\1">\1</link>',text)
    return text


class Manual(BaseDocTemplate):
    def afterFlowable(self, flowable):
        if (isinstance(flowable,Paragraph) and flowable.style.name=='ManualSection'
                and re.match(r'^\d+\.',flowable.getPlainText())):
            text=flowable.getPlainText();key='section-'+text.split('.')[0]
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text,key,0,False)
            self.notify('TOCEntry',(0,text,self.page,key))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setTitle('Cyber Siege - Fresh Fury Installation and Launch Guide v1.0.0')
    canvas.setAuthor('Carlos Sanchez')
    canvas.setFont('Helvetica',8)
    canvas.setFillColor(colors.HexColor('#526174'))
    canvas.drawString(MARGIN,25,'CYBER SIEGE  |  v1.0.0  |  Fresh Fury guide')
    canvas.drawRightString(WIDTH-MARGIN,25,str(doc.page))
    canvas.setStrokeColor(colors.HexColor('#CFD9E5'))
    canvas.line(MARGIN,38,WIDTH-MARGIN,38)
    canvas.restoreState()


def main():
    styles=getSampleStyleSheet()
    body=ParagraphStyle('ManualBody',parent=styles['BodyText'],fontName='Helvetica',
                        fontSize=10,leading=14,spaceAfter=7,textColor=NAVY,
                        splitLongWords=True)
    heading=ParagraphStyle('ManualSection',parent=styles['Heading1'],fontName='Helvetica-Bold',
                           fontSize=15,leading=19,spaceBefore=17,spaceAfter=10,textColor=BLUE,
                           keepWithNext=True)
    code=ParagraphStyle('ManualCode',fontName='Courier',fontSize=8,leading=11,
                        backColor=colors.HexColor('#EFF4FA'),borderPadding=8,
                        spaceBefore=7,spaceAfter=12)
    title=ParagraphStyle('ManualTitle',fontName='Helvetica-Bold',fontSize=30,leading=35,
                         textColor=NAVY,spaceAfter=20)
    subtitle=ParagraphStyle('ManualSubtitle',parent=body,fontSize=14,leading=20,spaceAfter=22)
    story=[Spacer(1,70),Paragraph('CYBER SIEGE',title),
           Paragraph('Fresh Fury installation<br/>and launch guide',subtitle),
           Paragraph('Release 1.0.0 | 10 November 2026',body),
           Paragraph('Install from GitHub, launch the local AI experience, connect private '
                     'devices, resolve proxy routing, run the story and switch demos safely.',body),
           Spacer(1,25),Paragraph('Copy. Paste. Launch.',heading),
           Preformatted('git clone --branch v1.0.0 \\\n  https://github.com/Navigatedhustle/cyber-siege.git\ncd cyber-siege\n./launch.sh',code),
           Paragraph('On the Fury: <link href="http://127.0.0.1:8090/" color="#004BDF">'
                     'http://127.0.0.1:8090/</link><br/>Then click <b>Start the story</b>.',body),
           Paragraph('Read prerequisites first. The host needs Ubuntu 24.04 ARM64, GB300, '
                     'Python 3.12, working Docker/GPU access and PDF libraries. '
                     'Cold model installation requires internet access and time.',body),PageBreak()]
    toc=TableOfContents();toc.levelStyles=[ParagraphStyle('Contents',parent=body,leftIndent=0,
                                                        firstLineIndent=0,spaceBefore=5)]
    story.extend([Paragraph('Contents',heading),toc,PageBreak()])
    text=(ROOT/'docs/FRESH_FURY_GUIDE.md').read_text()
    paragraph=[];code_lines=[];in_code=False
    def flush():
        if paragraph:
            story.append(Paragraph(inline(' '.join(paragraph)),body));paragraph.clear()
    for line in text.splitlines():
        if line.startswith('```'):
            flush()
            if in_code:
                for command in code_lines:
                    if stringWidth(command,'Courier',8)>AVAILABLE-16:
                        raise ValueError('Command exceeds printable width: '+command)
                story.append(KeepTogether([Preformatted('\n'.join(code_lines),code)]))
                code_lines=[]
            in_code=not in_code;continue
        if in_code:
            code_lines.append(line);continue
        if line.startswith('# '):continue
        if line.startswith('## '):
            flush();story.append(Paragraph(inline(line[3:]),heading))
        elif not line.strip():flush()
        elif line.startswith('- '):
            flush();story.append(Paragraph(inline(line[2:]),body,bulletText='-'))
        else:paragraph.append(line)
    flush()
    dest=ROOT/'docs/FRESH_FURY_GUIDE.pdf'
    doc=Manual(str(dest),pagesize=A4,leftMargin=MARGIN,rightMargin=MARGIN,
               topMargin=45,bottomMargin=53,pageCompression=1)
    doc.addPageTemplates(PageTemplate(id='manual',frames=Frame(MARGIN,53,AVAILABLE,HEIGHT-98,
                           leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0),onPage=footer))
    doc.multiBuild(story)
    print(dest)


if __name__=='__main__':main()
