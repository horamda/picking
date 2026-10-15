"""Extractor conservador para PDFs de carga de ChessERP v6 vistos en el piloto.
Si detecta líneas de artículos dudosas, no autoriza importar silenciosamente.
"""
import re
from collections import OrderedDict
import fitz

DATE = re.compile(r'\b\d{2}/\d{2}/\d{2,4}\b')
HEAD = re.compile(r'Reparto Nro:\s*(\d+)\s*\|\s*Fecha:\s*(\d{2}/\d{2}/\d{4})')
TRUCK = re.compile(r'Transporte:\s*(\d+)\s*-\s*\(([^)]+)\)\s*(.*?)\s*\|\s*Chofer:\s*(.*?)\s*\|\s*Depósito:\s*(.*)')
COURT = re.compile(r'^\s*(\d{3})\s*-\s*CANCHA\s+(\d+)', re.I)
STORE = re.compile(r'^\s*Almacen:\s*(\d+)\s*-\s*(.*?)\s{2,}A CARGAR', re.I)
ITEM = re.compile(r'^\s*(\d{3,6})\s+(.+?)\s{2,}(\d{2}/\d{2}/\d{2,4})?\s*(\d+)?\s*(\d+)?\s*$')
EMPTY = re.compile(r'^\s*(\d{3,6})\s+(.+?)\s{2,}(\d+)\s*(\d+)?\s*$')

def parse_pdf(data:bytes):
    doc=fitz.open(stream=data,filetype='pdf')
    result={'reparto':None,'fecha':None,'camion':None,'chofer':None,'deposito':None,'canchas':[],'activos_referencia':[],'advertencias':[]}
    courts=OrderedDict()
    header=None
    for page_num,page in enumerate(doc,1):
        text=page.get_text(sort=True)
        # preserve spatial columns with pdftotext -layout when installed; fitz blocks if not
        import subprocess
        proc=subprocess.run(['pdftotext','-f',str(page_num),'-l',str(page_num),'-layout','-','-'],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if proc.returncode==0: text=proc.stdout.decode('utf-8','replace')
        lines=text.splitlines()
        h=HEAD.search(text)
        if h and header is None:
            header=(h.group(1),h.group(2))
            result['reparto'],result['fecha']=header
        elif h and header!=(h.group(1),h.group(2)):
            raise ValueError('El PDF contiene repartos o fechas diferentes; importalos por separado')
        t=TRUCK.search(text)
        if t:
            truck=(t.group(2).strip(),t.group(4).strip(),t.group(5).strip())
            if result['camion'] and result['camion']!=truck[0]:raise ValueError('PDF con camiones diferentes')
            result['camion'],result['chofer'],result['deposito']=truck
        court=None;store='';in_empty=False; units_start=None
        for line in lines:
            if 'SKU Descripción' in line and 'Unids' in line:
                units_start=line.find('Unids')
            c=COURT.match(line)
            if c:
                court=int(c.group(2)); courts.setdefault(court,OrderedDict());store='';in_empty=False;continue
            if 'VACIOS CORRESPONDIENTES A LOS ARTICULOS A CARGAR' in line:
                in_empty=True;court=None;continue
            if in_empty:
                if 'ChessERP' in line or 'Pagina:' in line:in_empty=False
                e=EMPTY.match(line)
                if e and 'SKU' not in line:
                    result['activos_referencia'].append({'sku':e.group(1),'nombre':e.group(2).strip(),'bultos':int(e.group(3)),'unidades':int(e.group(4) or 0)})
                continue
            s=STORE.match(line)
            if s and court is not None:store=s.group(2).strip();continue
            if court is None or not store:continue
            if 'TOTAL ALMACEN' in line:store='';continue
            if not re.match(r'^\s*\d{3,6}\s+\S',line):continue
            # Ignore layout footer / totals; parse right-hand columns reliably using 2+ spaces.
            segments=[x.strip() for x in re.split(r'\s{2,}',line.strip()) if x.strip()]
            if not segments or not re.match(r'^\d{3,6}\s+\S',segments[0]):continue
            sku,desc=segments[0].split(' ',1)
            tail=segments[1:]
            if tail and DATE.fullmatch(tail[0]):tail=tail[1:]
            if not tail or not tail[0].isdigit() or len(tail)>2 or (len(tail)==2 and not tail[1].isdigit()):
                result['advertencias'].append(f'Página {page_num}, cancha {court}: línea sin interpretar: {line.strip()}')
                continue
            # Layout may have a quantity only in Unids, with Bultos blank.
            # Use the PDF column headers to distinguish those cases.
            if len(tail)==1 and units_start is not None:
                pos=line.rfind(tail[0])
                if pos>=units_start-4:b,u=0,int(tail[0])
                else:b,u=int(tail[0]),0
            else:
                b=int(tail[0]);u=int(tail[1]) if len(tail)>1 else 0
            key=sku
            if key not in courts[court]:
                courts[court][key]={'sku':sku,'descripcion':desc,'almacen':store,'bultos':0,'unidades':0,'lineas_originales':[]}
            obj=courts[court][key]
            obj['bultos']+=b;obj['unidades']+=u
            obj['lineas_originales'].append({'bultos':b,'unidades':u,'texto':line.strip()})
    if not result['reparto'] or not result['camion'] or not courts:raise ValueError('No se pudo reconocer el encabezado y las canchas del PDF de Chess')
    result['canchas']=[{'numero':n,'productos':list(p.values())} for n,p in courts.items()]
    return result
