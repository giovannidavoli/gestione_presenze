import pandas as pd
import io
import os
import re
from decimal import Decimal
from django.db import transaction
from .models import Dipendente, Azienda, Studio

# --- UTILITY DI PULIZIA (Mantenute e Corazzate) ---

def clean_decimal(v):
    """Pulisce i dati numerici gestendo i formati Ranocchi (es: 1.250,50)."""
    if pd.isna(v) or v == "" or str(v).strip().lower() in ["nan", "none"]: 
        return Decimal("0.00")
    try:
        s = str(v).strip().replace('€', '').replace(' ', '')
        if ',' in s and '.' in s: s = s.replace('.', '').replace(',', '.')
        elif ',' in s: s = s.replace(',', '.')
        return Decimal(s).quantize(Decimal("0.00001"))
    except: 
        return Decimal("0.00")

def get_clean_id(val, is_azienda=False):
    """Estrae ID numerici puliti (es: 001047 -> 1047)."""
    if pd.isna(val): return None
    try:
        s_val = str(val).strip().split('.')[0]
        nums = re.findall(r'\d+', s_val)
        if nums:
            res = str(int(nums[0]))
            if is_azienda and int(res) < 10: return None
            return res
        return None
    except: return None

def extract_ditta_info(val):
    """Estrae Codice e Ragione Sociale da stringhe tipo 'Ditta: 001047 CENTER CITY SRL'."""
    if pd.isna(val): return None, None
    s = str(val).strip()
    if "Ditta:" in s:
        match = re.search(r'Ditta:\s*(\d+)\s*(.*)', s)
        if match:
            return str(int(match.group(1))), match.group(2).strip()
    return None, None

def smart_read_csv(path):
    """Legge CSV provando diversi separatori e forzando 100 colonne."""
    for sep in [';', ',']:
        try:
            df = pd.read_csv(path, header=None, sep=sep, engine='python', names=range(100))
            if df.shape[1] > 1:
                return df.dropna(axis=1, how='all')
        except: continue
    return pd.read_csv(path, header=None, sep=None, engine='python', names=range(100)).dropna(axis=1, how='all')

# --- CUORE DEL TOOL: GENERATORE ANTEPRIMA ---

def genera_dati_anteprima(car_obj):
    """
    Unifica tutti i file in un'unica struttura dati per la Dashboard HTML.
    Questa funzione non salva nulla, serve solo per la visualizzazione.
    """
    m = car_obj.mappatura
    df_ana = smart_read_csv(car_obj.file_anagrafica.path)
    
    mappa_dipendenti = {} # Chiave: "CodAz_Matr"
    curr_az_cod, curr_az_rag = None, None

    # 1. Base Anagrafica
    for _, row in df_ana.iterrows():
        val0 = str(row.iloc[0])
        if "Ditta:" in val0:
            curr_az_cod, curr_az_rag = extract_ditta_info(val0)
            continue
        
        matr = get_clean_id(row.iloc[m.ana_col_matricola])
        if matr and curr_az_cod:
            pt = clean_decimal(row.iloc[m.ana_col_perc_part_time])
            pt_f = pt if pt > 0 else Decimal("100.00")
            chiave = f"{curr_az_cod}_{matr}"
            
            mappa_dipendenti[chiave] = {
                'cod_az': curr_az_cod, 'ditta': curr_az_rag, 'matr': matr,
                'nome': str(row.iloc[m.ana_col_nominativo]).strip(),
                'qualifica': str(row.iloc[m.ana_col_qualifica]).strip(),
                'contratto': str(row.iloc[m.ana_col_tipo_contratto]).strip(),
                'pt': pt_f, 'lordo': Decimal("0.00"),
                'ore': [8.0, 8.0, 8.0, 8.0, 8.0, 0.0, 0.0] if pt_f == 100 else [0.0]*7,
                'inps': Decimal("0.00"), 'inail': Decimal("0.00"), 'tfr': Decimal("0.00"),
                'ferie_ap': Decimal("0.00")
            }

    # 2. Aggancio Retribuzioni (Lordo)
    if car_obj.file_retribuzioni:
        df_ret = smart_read_csv(car_obj.file_retribuzioni.path)
        curr_az_ret = None
        for _, row in df_ret.iterrows():
            if "Ditta:" in str(row.iloc[0]): curr_az_ret, _ = extract_ditta_info(row.iloc[0])
            matr = get_clean_id(row.iloc[m.ret_col_matricola])
            chiave = f"{curr_az_ret}_{matr}"
            if chiave in mappa_dipendenti:
                v = [clean_decimal(row.iloc[m.ret_col_elementi_start + j]) for j in range(8)]
                lordo_base = sum(v)
                mappa_dipendenti[chiave]['lordo'] = (lordo_base * (mappa_dipendenti[chiave]['pt'] / Decimal("100"))).quantize(Decimal("0.01"))

    # 3. Aggancio Stacos
    if car_obj.file_stacos:
        df_sta = smart_read_csv(car_obj.file_stacos.path)
        curr_az_sta = None
        for _, row in df_sta.iterrows():
            if "Ditta:" in str(row.iloc[0]): curr_az_sta, _ = extract_ditta_info(row.iloc[0])
            matr = get_clean_id(row.iloc[m.sta_col_matricola])
            chiave = f"{curr_az_sta}_{matr}"
            if chiave in mappa_dipendenti:
                mappa_dipendenti[chiave]['inps'] = clean_decimal(row.iloc[m.sta_col_inps])
                mappa_dipendenti[chiave]['inail'] = clean_decimal(row.iloc[m.sta_col_inail])
                mappa_dipendenti[chiave]['tfr'] = clean_decimal(row.iloc[m.sta_col_tfr])

    # 4. Aggancio Presenze (Sovrascrive Default)
    if car_obj.file_presenze:
        df_pre = pd.read_csv(car_obj.file_presenze.path, header=None, sep=';', engine='python', names=range(100))
        az_pre = get_clean_id(df_pre.iloc[0, 1])
        for _, row in df_pre.iterrows():
            matr = get_clean_id(row.iloc[0])
            if matr and "ore lavorate" in str(row.iloc[2]).lower():
                chiave = f"{az_pre}_{matr}"
                if chiave in mappa_dipendenti:
                    st = m.pre_col_lunedi
                    mappa_dipendenti[chiave]['ore'] = [float(clean_decimal(row.iloc[st+j])) for j in range(7)]

    return list(mappa_dipendenti.values())

# --- FUNZIONE DI SALVATAGGIO DEFINITIVA ---

def importa_dati_excel_gestionale(car_obj):
    """Usa il generatore di anteprima per salvare i dati reali nel DB."""
    dati = genera_dati_anteprima(car_obj)
    
    with transaction.atomic():
        studio_obj, _ = Studio.objects.get_or_create(nome="STUDIO PROFESSIONALE DI RIFERIMENTO")
        
        for d in dati:
            # Assicuriamoci che l'azienda esista
            az_obj, _ = Azienda.objects.get_or_create(codice=d['cod_az'], defaults={'ragione_sociale': d['ditta'], 'studio': studio_obj})
            
            Dipendente.objects.update_or_create(
                azienda=az_obj, codice=d['matr'],
                defaults={
                    'cognome_nome': d['nome'], 'qualifica': d['qualifica'], 'tipo_contratto': d['contratto'],
                    'perc_part_time': d['pt'], 'lordo_mensile_calcolato': d['lordo'],
                    'costo_inps_ditta': d['inps'], 'costo_inail_ditta': d['inail'], 'rateo_tfr': d['tfr'],
                    'ore_lun': d['ore'][0], 'ore_mar': d['ore'][1], 'ore_mer': d['ore'][2],
                    'ore_gio': d['ore'][3], 'ore_ven': d['ore'][4], 'ore_sab': d['ore'][5], 'ore_dom': d['ore'][6]
                }
            )
    
    car_obj.elaborato = True
    car_obj.save()
    print(f">>> SINCRONIZZAZIONE COMPLETATA: {len(dati)} record.")