import sys, os
from PIL import Image, ImageDraw
root, out = sys.argv[1], sys.argv[2]
import yaml; names = yaml.safe_load(open(os.path.join(root,'data.yaml')))['names']
cols = {}
tiles = []
for rel in sys.argv[3:]:
    p = os.path.join(root, rel)
    im = Image.open(p).convert('RGB')
    d = ImageDraw.Draw(im)
    lp = p.replace('/images/','/labels/').rsplit('.',1)[0]+'.txt'
    for line in open(lp):
        c,x,y,w,h = line.split(); c=int(c); x,y,w,h = map(float,(x,y,w,h))
        W,H = im.size
        d.rectangle([(x-w/2)*W,(y-h/2)*H,(x+w/2)*W,(y+h/2)*H], outline='red', width=6)
        d.text(((x-w/2)*W+4,(y-h/2)*H+4), names[c], fill='red')
    tiles.append(im.resize((512,512)))
g = Image.new('RGB',(512*len(tiles),512))
for i,t in enumerate(tiles): g.paste(t,(512*i,0))
g.save(out)
