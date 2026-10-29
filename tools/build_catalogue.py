#!/usr/bin/env python3
"""Synchronisation Gestion -> boutique.

Usage (depuis la racine du dépôt) :
  python3 tools/build_catalogue.py <dossier_produits> [<dossier_photos>]

<dossier_produits> : un fichier JSON par article, tels qu'exportés de la base Gestion
                     (ArtifactData list collection "products" avec out_dir) — ou un seul fichier .json (liste).
<dossier_photos>   : photos téléchargées depuis le stockage de la page Gestion, nommées <assetId>.<ext>.

Effets :
  - chaque photo {a: assetId} sans nom de fichier site est convertie en img/w/<id>-u<k>-360.webp et -720.webp ;
  - le catalogue est réécrit dans artifact.html entre /*CATALOGUE-DEBUT*/ et /*CATALOGUE-FIN*/ ;
  - index.html est régénéré ;
  - un compte rendu JSON est écrit dans .sync/result.json :
      {"photos": {"<productId>": [{"a": assetId, "w": nom}, ...]}, "new_files": [...], "warnings": [...], "count": n}
    -> réécrire ensuite dans la base le champ photos des articles listés (pour qu'ils gardent le nom w).
"""
import json,os,sys,glob,re,subprocess
from PIL import Image,ImageOps
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W=os.path.join(ROOT,'img','w')

def load(path):
    if os.path.isdir(path):
        L=[]
        for f in sorted(glob.glob(os.path.join(path,'**','*.json'),recursive=True)):
            d=json.load(open(f,encoding='utf-8'))
            if isinstance(d,dict) and 'data' in d and isinstance(d['data'],dict): d={**d['data'],'id':d.get('id') or d.get('doc_id') or d['data'].get('id')}
            L.append(d)
        return L
    d=json.load(open(path,encoding='utf-8'))
    return d if isinstance(d,list) else list(d.values())

def square(im,size):
    im=ImageOps.exif_transpose(im).convert('RGB')
    w,h=im.size;r=w/h
    if 0.8<=r<=1.25:
        im=ImageOps.fit(im,(size,size),Image.LANCZOS)
    else:
        im.thumbnail((size,size),Image.LANCZOS)
        bg=Image.new('RGB',(size,size),(255,255,255));bg.paste(im,((size-im.width)//2,(size-im.height)//2));im=bg
    return im

def main():
    prods=load(sys.argv[1]); phdir=sys.argv[2] if len(sys.argv)>2 else None
    res={'photos':{},'new_files':[],'warnings':[]}
    cat=[]
    for p in sorted(prods,key=lambda x:int(x.get('n') or 0)):
        pid=p['id']; base=[]; changed=False; photos=[]
        for ph in p.get('photos') or []:
            ph=dict(ph)
            if not ph.get('w'):
                a=ph.get('a'); src=None
                if phdir and a:
                    c=[f for f in glob.glob(os.path.join(phdir,a+'*')) if os.path.isfile(f)]
                    src=c[0] if c else None
                if not src:
                    res['warnings'].append(f'{pid} : photo {a} introuvable, ignorée'); continue
                k=1
                while os.path.exists(os.path.join(W,f'{pid}-u{k}-720.webp')): k+=1
                name=f'{pid}-u{k}'
                im=Image.open(src)
                for s in (360,720):
                    out=os.path.join(W,f'{name}-{s}.webp'); square(im,s).save(out,'WEBP',quality=82,method=6)
                    res['new_files'].append(os.path.relpath(out,ROOT))
                ph['w']=name; changed=True
            photos.append(ph); base.append(ph['w'])
        if changed: res['photos'][pid]=photos
        if not base: res['warnings'].append(f'{pid} : aucune photo, article non publié'); continue
        if not str(p.get('desc','')).strip(): res['warnings'].append(f'{pid} : description vide')
        e={'id':pid,'n':int(p['n']),'cat':p['cat'],'name':p['name'],'price':round(float(p['price']),2),'d':p.get('d',''),
           'desc':p.get('desc',''),'specs':p.get('specs') or [],'base':base,'oos':bool(p.get('oos'))}
        if p.get('variants'):
            e['variants']=[{'name':v['name'],'img':min(int(v.get('img',0)),len(base)-1)} for v in p['variants']]
        if p.get('hidden'): e['hidden']=True
        cat.append(e)
    art=os.path.join(ROOT,'artifact.html'); s=open(art,encoding='utf-8').read()
    a=s.index('/*CATALOGUE-DEBUT*/'); b=s.index('/*CATALOGUE-FIN*/')
    s=s[:a]+'/*CATALOGUE-DEBUT*/window.TZ_CATALOGUE='+json.dumps(cat,ensure_ascii=False,separators=(',',':'))+';'+s[b:]
    open(art,'w',encoding='utf-8').write(s)
    subprocess.run([sys.executable,os.path.join(ROOT,'tools','build_site.py')],check=True)
    res['count']=len(cat); res['visible']=sum(1 for c in cat if not c.get('hidden'))
    os.makedirs(os.path.join(ROOT,'.sync'),exist_ok=True)
    json.dump(res,open(os.path.join(ROOT,'.sync','result.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=1)
    print(json.dumps(res,ensure_ascii=False,indent=1))
main()
