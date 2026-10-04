#!/usr/bin/env python3
"""One-off number-multiset parity for PT lines 596-851 vs EN chunk (sprint A-06)."""
import re, subprocess, sys
from collections import Counter
pt = subprocess.check_output(['sed','-n','596,851p','MANUSCRIPT.md'],text=True)
en = open('_sprint-2026-10-04/translation/A-06-s4.3.md').read()
def strip(t):
    t = re.sub(r'§[\d.]+','',t)
    t = re.sub(r'\d{4}-\d{2}-\d{2}','',t)
    t = re.sub(r'\bv\d+(\.\d+)*','',t)
    return t
def nums(t, en):
    t = strip(t)
    if not en:
        t = re.sub(r'\b\d{1,2}(?:[–, ]+(?:e )?\d{1,2})*/\d{2}\b','',t)  # dd/mm dates
    out=[]
    pat = r'\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\d+' if en else r'\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+,\d+|\d+'
    for m in re.findall(pat,t):
        out.append(m.replace(',','').replace('.','.') if en else m.replace('.','').replace(',','.'))
    return Counter(out)
a,b = nums(pt,False), nums(en,True)
print('PT total',sum(a.values()),'EN total',sum(b.values()))
print('PT-EN',dict(a-b)); print('EN-PT',dict(b-a))
