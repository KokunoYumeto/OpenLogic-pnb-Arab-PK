"""Build the complete translated Sets chapter, retaining exact source identities.

This is an extensible reader-construction component, not a claim of full edition
coverage. Every conditional omission and reference/asset mapping is inventoried.
The tool generates TeX only. Use the separate guarded PowerShell launcher.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path

REPO=Path(__file__).resolve().parents[1]
STATE=Path(r'C:\interlanguage-task-state\openlogic-pnb-Arab-PK')
CHAPTER='content/sets-functions-relations/sets'

def digest(raw): return hashlib.sha256(raw).hexdigest()

def argument(text, pos):
    while pos<len(text) and text[pos].isspace(): pos+=1
    if text[pos]!='{': raise ValueError('Expected balanced TeX argument')
    start=pos+1
    depth=1
    pos+=1
    while pos<len(text) and depth:
        if text[pos]=='{' and text[pos-1]!='\\': depth+=1
        elif text[pos]=='}' and text[pos-1]!='\\': depth-=1
        pos+=1
    if depth: raise ValueError('Unbalanced argument')
    return text[start:pos-1],pos

def rtl_set_conditions(body, unit, records):
    """One RTL clause per mixed set-builder predicate, with LTR math islands.

    Independent text boxes were reversing the phrase around embedded variables.
    Preserve the exact text chunks and formal-fragment order; change direction
    boundaries only. Purely symbolic set builders are left untouched.
    """
    result=[]; pos=0
    while True:
        start=body.find(r'\Setabs',pos)
        if start<0: result.append(body[pos:]); break
        result.append(body[pos:start])
        representative,p=argument(body,start+len(r'\Setabs'))
        condition,end=argument(body,p)
        if not re.search('[\u0600-\u06ff]',condition):
            result.append(body[start:end]); pos=end; continue
        chunks=[]; formal=[]; cursor=0
        def add_math(fragment):
            fragment=fragment.strip()
            if fragment:
                formal.append(fragment)
                chunks.append(r'\textenglish{\('+fragment+r'\)}')
        for match in re.finditer(r'\\text\{([^{}]*)\}',condition):
            add_math(condition[cursor:match.start()])
            chunks.append(match.group(1))
            cursor=match.end()
        add_math(condition[cursor:])
        rendered=r'\text{\textarabic{'+''.join(chunks)+'}}'
        recovered=re.findall(r'\\textenglish\{\\\((.*?)\\\)\}',rendered,flags=re.S)
        if recovered!=formal: raise ValueError('Math-island order changed')
        records.append({'unit':unit,'representative':representative,'original_condition':condition,'condition_sha256':digest(condition.encode()),'formal_fragments_in_original_order':formal,'rendering':'one RTL text clause with explicitly LTR formal islands'})
        result.append(r'\Setabs{'+representative+'}{'+rendered+'}')
        pos=end
    return ''.join(result)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--font-dir',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,default=REPO/'provenance'/'SOURCE_MANIFEST.jsonl')
    args=parser.parse_args()
    out=args.output_dir.resolve()
    if not (out.is_relative_to(REPO) or out.is_relative_to(STATE)): raise ValueError('Output boundary')
    out.mkdir(parents=True,exist_ok=True)
    manifest={row['source_path']:row for row in map(json.loads,args.manifest.read_text('utf-8-sig').splitlines())}
    driver=(REPO/'translation'/CHAPTER/'sets.tex').read_text('utf-8')
    names=re.findall(r'\\olimport\{([^}]+)\}',driver)
    if len(names)!=6 or len(set(names))!=6: raise ValueError('Unexpected chapter graph')
    records=[]
    units=[]
    label_kinds={}
    for name in ['sets']+names:
        rel=f'{CHAPTER}/{name}.tex'
        source=(REPO/'upstream'/rel).read_bytes()
        target=(REPO/'translation'/rel).read_bytes()
        if digest(source)!=manifest[rel]['source_sha256']: raise ValueError('Source hash mismatch')
        records.append({'unit_id':manifest[rel]['unit_id'],'source_path':rel,'source_sha256':digest(source),'translation_sha256':digest(target)})
        if name=='sets': continue
        text=target.decode('utf-8')
        prefix=':'.join(re.search(r'\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}',text).groups())
        label_kinds[prefix+':sec']='حصہ'
        for match in re.finditer(r'\\ollabel\{([^}]+)\}',text):
            key=match.group(1)
            label_kinds[prefix+':'+key]='شکل' if key in ['fig:union','fig:intersection','difference'] else 'تعریف' if key=='wienerkuratowski' else 'مسئلہ' if key.startswith('thm:') else 'قضیہ'
        units.append((name,prefix,text))
    refs=[]
    assets=[]
    conditionals=[]
    layout_overrides=[]
    rtl_conditions=[]
    bodies=[]
    for name,prefix,text in units:
        body=text.split(r'\begin{document}',1)[1].rsplit(r'\end{document}',1)[0]
        while r'\oliflabeldef' in body:
            start=body.index(r'\oliflabeldef')
            label,pos=argument(body,start+len(r'\oliflabeldef'))
            yes,pos=argument(body,pos)
            no,end=argument(body,pos)
            choose=label in label_kinds
            conditionals.append({'unit':name,'label':label,'included_branch':'yes' if choose else 'no','omitted_sha256':digest((no if choose else yes).encode()),'reason':'Exact source conditional evaluated against this complete chapter reader, not the whole edition.'})
            body=body[:start]+(yes if choose else no)+body[end:]
        body=re.sub(r'\\olfileid\{[^}]*\}\{[^}]*\}\{[^}]*\}', '',body)
        body=re.sub(r'\\olsection\{([^}]+)\}',lambda m:r'\section{'+m.group(1)+r'}\label{'+prefix+':sec}',body)
        body=re.sub(r'\\ollabel\{([^}]+)\}',lambda m:r'\label{'+prefix+':'+m.group(1)+'}',body)
        def ref(match):
            opts=re.findall(r'\[([^]]*)\]',match.group(1))
            p=prefix.split(':')
            if len(opts)==1: p[2]=opts[0]
            elif len(opts)==2: p[1:]=opts
            elif len(opts)==3: p=opts
            target=':'.join(p)+':'+match.group(2)
            if target not in label_kinds: raise ValueError('Unresolved local reference '+target)
            refs.append({'unit':name,'target':target,'kind':label_kinds[target]})
            return r'\pnbref{'+label_kinds[target]+'}{'+target+'}'
        body=re.sub(r'\\[Oo]lref((?:\[[^]]*\]){0,3})\{([^}]+)\}',ref,body)
        def asset(match):
            relative=match.group(1)
            path=(REPO/'upstream'/relative).resolve()
            if not path.is_relative_to(REPO/'upstream'/'assets'): raise ValueError('Asset boundary')
            data=path.read_bytes()
            if not any(x['source_path']==relative for x in assets): assets.append({'source_path':relative,'bytes':len(data),'sha256':digest(data)})
            return r'\begin{LTR}\centering\input{'+Path(os.path.relpath(path,out)).as_posix()+r'}\end{LTR}'
        body=re.sub(r'\\olasset\{([^}]+)\}',asset,body)
        body=re.sub(r'\\pnboblique\{!!\{element\}s\}', 'عنصراں',body)
        body=re.sub(r'!!\^?a?\{element\}s?', 'عنصر',body)
        if '!!' in body: raise ValueError('Unexpanded lexical token')
        body=rtl_set_conditions(body,name,rtl_conditions)
        body=re.sub(r'\\text\{([^{}]*[\u0600-\u06ff][^{}]*)\}',lambda m:r'\text{\textarabic{'+m.group(1)+'}}',body)
        body=body.replace(r'\textrm{Ruth}',r'\text{\textenglish{Ruth}}').replace('``','«').replace("''",'»')
        if name=='unions-and-intersections':
            # This complete atomic equality overflowed the RTL inline paragraph.
            # Promote to display without changing any mathematical symbol/order.
            formula=r'\{a, b, c \} \cap \{a, b, d \} = \{a, b\}'
            needle='$'+formula+'$۔'
            if body.count(needle)!=1: raise ValueError('Layout override no longer matches exact source formula')
            body=body.replace(needle,'\\[\n'+formula+r'\text{\textarabic{۔}}'+'\n\\]')
            layout_overrides.append({'unit':name,'formula':formula,'change':'inline to display; terminal punctuation retained','reason':'Naskh first complete build overfull hbox 37.1751pt; source translation bytes unchanged'})
        bodies.append(body)
    preamble=(REPO/'reader'/'sets-preamble.tex').read_text('utf-8')
    title=re.search(r'\\olchapter\{sfr\}\{set\}\{([^}]+)\}',driver).group(1)
    static=args.font_dir.resolve()/'NotoNastaliqUrdu-Regular.ttf'
    if not static.is_file(): raise ValueError('Required static Nastaliq font absent')
    fontpath=Path(os.path.relpath(static.parent,out)).as_posix()+'/'
    font_names=['NotoNaskhArabic-Regular.ttf','NotoNaskhArabic-Bold.ttf','NotoSerif-Regular.ttf','NotoSerif-Bold.ttf','NotoSerif-Italic.ttf','NotoSerif-BoldItalic.ttf',static.name]
    font_records=[]
    for filename in font_names:
        raw=(static.parent/filename).read_bytes()
        font_records.append({'file':filename,'bytes':len(raw),'sha256':digest(raw)})
    basefont=r'\setmainfont[Path='+fontpath+r',BoldFont=NotoSerif-Bold.ttf,ItalicFont=NotoSerif-Italic.ttf,BoldItalicFont=NotoSerif-BoldItalic.ttf]{NotoSerif-Regular.ttf}'
    supportfont='\n'.join(r'\newfontfamily\arabicfont'+suffix+r'[Script=Arabic,Path='+fontpath+r',BoldFont=NotoNaskhArabic-Bold.ttf]{NotoNaskhArabic-Regular.ttf}' for suffix in ['sf','tt'])
    for profile,font,leading in [
        ('naskh',r'\newfontfamily\arabicfont[Script=Arabic,Path='+fontpath+r',BoldFont=NotoNaskhArabic-Bold.ttf]{NotoNaskhArabic-Regular.ttf}','1.15'),
        ('nastaliq',r'\newfontfamily\arabicfont[Script=Arabic,Path='+Path(os.path.relpath(static.parent,out)).as_posix()+'/,BoldFont='+static.name+',BoldFeatures={FakeBold=1.8}]{'+static.name+'}','1.7')]:
        tex=preamble.replace('@@BASEFONT@@',basefont).replace('@@SUPPORTFONT@@',supportfont).replace('@@FONT@@',font).replace('@@LEADING@@',leading).replace('@@PROFILE@@',profile).replace('@@CHAPTER@@',title).replace('@@BODY@@','\n\n'.join(bodies))
        (out/f'sets-{profile}.tex').write_text(tex,encoding='utf-8')
    receipt={'schema':'pnb-sets-reader-inputs/1','source_units':records,'body_sections':len(bodies),'chapter_driver_count':1,'reader_coverage_unit_ids':[x['unit_id'] for x in records],'references':refs,'label_kinds':label_kinds,'assets':assets,'conditionals':conditionals,'layout_overrides':layout_overrides,'rtl_set_conditions':rtl_conditions,'number_direction':'Section and figure presentation numbers isolated LTR; stored label numbers unchanged.','emphasis_rendering':'Bold upright for native Arabic-script emphasis; no unavailable italic fallback. Nastaliq bold is explicitly synthetic weight.','nastaliq_font_sha256':digest(static.read_bytes()),'builder_sha256':digest(Path(__file__).read_bytes()),'preamble_sha256':digest((REPO/'reader'/'sets-preamble.tex').read_bytes()),'status':'tex_generated_no_pdf_acceptance'}
    receipt['fonts']=font_records
    (out/'INPUTS.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'units':len(records),'sections':len(bodies),'references':len(refs),'assets':len(assets),'conditional_branches':len(conditionals),'inputs_sha256':digest((out/'INPUTS.json').read_bytes())}))

if __name__=='__main__': main()
