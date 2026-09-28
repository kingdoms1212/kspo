from pathlib import Path
import re
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont

base = Path(__file__).parent
for name in ('program-design-flow', 'ai-integration', 'csv-pipeline'):
    root = ET.parse(base / (name + '.svg')).getroot()
    img = Image.new('RGB', (1800, 1000), '#F5F8FC')
    draw = ImageDraw.Draw(img)
    for el in root:
        if not el.tag.endswith('g'):
            continue
        for node in el:
            a = node.attrib
            tag = node.tag.split('}')[-1]
            if tag == 'rect':
                x,y,w,h = [float(a[k]) for k in ('x','y','width','height')]
                draw.rounded_rectangle((x,y,x+w,y+h), radius=float(a.get('rx',0)), fill=a.get('fill'), outline=a.get('stroke'), width=int(a.get('stroke-width',1)))
            elif tag == 'text':
                font = ImageFont.truetype('C:/Windows/Fonts/' + ('malgunbd.ttf' if a.get('font-weight')=='700' else 'malgun.ttf'), int(a['font-size']))
                draw.text((float(a['x']),float(a['y'])), node.text or '', font=font, fill=a['fill'], anchor='ls')
            elif tag == 'path':
                coords = re.findall(r'[MHV]|-?\d+(?:\.\d+)?', a['d'])
                pts=[];i=0;x=y=0
                while i<len(coords):
                    op=coords[i];i+=1
                    if op=='M': x=float(coords[i]);y=float(coords[i+1]);i+=2
                    elif op=='H': x=float(coords[i]);i+=1
                    elif op=='V': y=float(coords[i]);i+=1
                    pts.append((x,y))
                color=a['stroke'];draw.line(pts,fill=color,width=3)
                x,y=pts[-1];px,py=pts[-2]
                if x==px: tri=[(x,y),(x-8,y-14 if y>py else y+14),(x+8,y-14 if y>py else y+14)]
                else: tri=[(x,y),(x-14 if x>px else x+14,y-8),(x-14 if x>px else x+14,y+8)]
                draw.polygon(tri,fill=color)
    img.save(base/(name+'.png'))
