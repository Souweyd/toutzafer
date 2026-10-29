#!/usr/bin/env python3
"""Régénère index.html (site GitHub Pages) à partir de artifact.html (source de la page Claude).
Usage : python3 tools/build_site.py   (depuis la racine du dépôt)"""
import os
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src=open(os.path.join(ROOT,'artifact.html'),encoding='utf-8').read()
cur=open(os.path.join(ROOT,'index.html'),encoding='utf-8').read()
i=src.index('<style>'); head=cur[:cur.index('<title>')]; se=src.index('</style>')+len('</style>')
out=head+src[:i]+'<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}</style>\n'+src[i:se]+'\n</head>\n<body>\n'+src[se:]+'\n</body>\n</html>\n'
open(os.path.join(ROOT,'index.html'),'w',encoding='utf-8').write(out)
print('index.html régénéré')
