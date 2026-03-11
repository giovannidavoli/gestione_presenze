import pandas as pd
import os
import io
import zipfile
import statistics
from datetime import date, datetime
import xml.etree.ElementTree as ET
from decimal import Decimal, ROUND_HALF_UP
from django.apps import apps # Per evitare import circolari
from .models import SessioneImportazione, RecordStoricoDipendente

# ==================================================================================
# SEZIONE 1: FUNZIONI UTILITY ORIGINALI (PRESERVATE)
# ==================================================================================

def clean_id(val):
    """
    Sincronizza gli ID (es. 1047, 1047.0, '08') in stringhe pulite.
    Rende l'accoppiamento tra file GIS infallibile.
    """
    if pd.isna(val) or val == "": return ""
    s = str(val).strip().split('.')[0]
    cleaned = "".join(filter(str.isdigit, s))
    return cleaned.lstrip('0') if cleaned else ""

def clean_dec_importer(v):
    """
    Pulisce i valori economici e gestisce correttamente anche i numeri negativi 
    (fondamentale per i ratei in rosso).
    """
    if pd.isna(v) or v == "" or str(v).strip().lower() in ["nan", "none"]: 
        return Decimal("0.00")
    try:
        if isinstance(v, (int, float, Decimal)):
            return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
        s = str(v).strip().replace('€', '').replace(' ', '')
        if ',' in s and '.' in s: 
            s = s.replace('.', '').replace(',', '.')
        elif ',' in s: 
            s = s.replace(',', '.')
            
        return Decimal(s).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except: 
        return Decimal("0.00")

def clean_hours(v):
    """
    Pulisce le ore giornaliere scartando valori > 31.00.
    Indispensabile per ignorare anni (2026) o date nella riga 0 GIS.
    """
    val = clean_dec_importer(v)
    if val > Decimal("31.00"): 
        return Decimal("0.00")
    return val

def smart_read(file_path):
    """Legge l'intero file GIS (Excel o CSV) senza limiti di righe."""
    try:
        return pd.read_excel(file_path, header=None).fillna('')
    except:
        return pd.read_csv(file_path, header=None, sep=None, engine='python', encoding='latin-1').fillna('')

def calcola_stime_finanziarie(lordo_effettivo):
    """
    Formula Studio ETL: 
    Netto = (Lordo - 9,19% contributi) * 0,85 tasse stimate.
    """
    l = lordo_effettivo
    inps_ditta = (l * Decimal("0.30")).quantize(Decimal("0.01"))
    inail_ditta = (l * Decimal("0.02")).quantize(Decimal("0.01"))
    tfr_mese = (l * Decimal("0.0741")).quantize(Decimal("0.01"))
    costo_totale = l + inps_ditta + inail_ditta + tfr_mese
    
    # Calcolo Netto Prudenziale
    contributi_dip = (l * Decimal("0.0919")).quantize(Decimal("0.01"))
    imponibile_fiscale = l - contributi_dip
    netto_stimato = (imponibile_fiscale * Decimal("0.85")).quantize(Decimal("0.01"))
    
    return {
        'costo': costo_totale, 
        'netto': netto_stimato,
        'inps_ditta': inps_ditta, 
        'inail_ditta': inail_ditta, 
        'tfr': tfr_mese 
    }

def get_idx(mappa, campo, nome_file):
    """Recupera l'indice colonna con gestione errori per mappatura mancante."""
    val = mappa.get(campo)
    if val is None or str(val).strip() == "":
        raise ValueError(f"Mancata mappatura per '{campo}' nel file {nome_file.upper()}.")
    return int(val)

# ==================================================================================
# SEZIONE 2: NUOVA LOGICA PRESENZE ZIP (AGGIUNTA)
# ==================================================================================

def determina_orario_da_mensile(row, anno, mese):
    """
    Analizza i giorni dal 01 al 31.
    Ricostruisce l'orario settimanale (Lun-Dom) basandosi sulla moda (valore frequente).
    """
    ore_per_giorno = {0: [], 1: [], 2: [], 3: [], 4: [], 5: [], 6: []}
    
    for giorno in range(1, 32):
        col_name = str(giorno).zfill(2)
        if col_name in row.index and pd.notna(row[col_name]):
            try:
                # Usa la funzione di pulizia esistente
                valore = clean_dec_importer(row[col_name])
                if valore > 0:
                    try:
                        data_corrente = date(anno, mese, giorno)
                        weekday = data_corrente.weekday() # 0=Lun
                        ore_per_giorno[weekday].append(valore)
                    except ValueError:
                        pass
            except:
                continue

    orario_settimanale = {}
    mapping_campi = ['ore_lun', 'ore_mar', 'ore_mer', 'ore_gio', 'ore_ven', 'ore_sab', 'ore_dom']
    mapping_output = {'Lun': 0, 'Mar': 0, 'Mer': 0, 'Gio': 0, 'Ven': 0, 'Sab': 0, 'Dom': 0} # Per compatibilità output
    mapping_keys = list(mapping_output.keys())

    for i in range(7):
        lista_ore = ore_per_giorno[i]
        key_out = mapping_keys[i]
        
        if lista_ore:
            try:
                valore_standard = statistics.mode(lista_ore)
            except:
                valore_standard = max(lista_ore)
        else:
            valore_standard = Decimal(0)
            
        mapping_output[key_out] = valore_standard
        
    return mapping_output

def elabora_file_presenze_csv(csv_content, filename, log_msgs):
    """
    Processa un singolo CSV estratto dallo ZIP Ranocchi.
    """
    try:
        Dipendente = apps.get_model('anagrafica', 'Dipendente')
        
        # Estrazione Anno/Mese dal nome file (es. ...202601.csv)
        base_name = os.path.basename(filename)
        name_part = os.path.splitext(base_name)[0]
        anno = datetime.now().year
        mese = datetime.now().month
        
        if len(name_part) >= 6 and name_part[-6:].isdigit():
            anno = int(name_part[-6:-2])
            mese = int(name_part[-2:])
        
        # Lettura CSV (skiprows=3 standard)
        df = pd.read_csv(io.BytesIO(csv_content), sep=';', encoding='latin1', skiprows=3)
        
        if len(df.columns) < 3:
            return

        col_matricola = df.columns[0]
        col_tipo = df.columns[2]
        
        # Filtro righe "Ore lavorate"
        df_ore = df[df[col_tipo].astype(str).str.contains("Ore lavorate", case=False, na=False)]
        
        count = 0
        for _, row in df_ore.iterrows():
            try:
                raw_matr = str(row[col_matricola]).strip()
                if not raw_matr or raw_matr.lower() == 'nan': continue
                
                # Usa clean_id esistente per coerenza
                matricola_clean = clean_id(raw_matr).zfill(6)
                
                dipendente = Dipendente.objects.filter(codice=matricola_clean).first()
                if dipendente:
                    orari = determina_orario_da_mensile(row, anno, mese)
                    
                    # Aggiornamento diretto DB
                    dipendente.ore_lun = orari['Lun']
                    dipendente.ore_mar = orari['Mar']
                    dipendente.ore_mer = orari['Mer']
                    dipendente.ore_gio = orari['Gio']
                    dipendente.ore_ven = orari['Ven']
                    dipendente.ore_sab = orari['Sab']
                    dipendente.ore_dom = orari['Dom']
                    dipendente.save()
                    count += 1
            except:
                continue
                
        log_msgs.append(f"File {filename}: Aggiornati {count} dipendenti.")

    except Exception as e:
        log_msgs.append(f"Errore file {filename}: {str(e)}")

def importa_presenze_zip(zip_path_or_file):
    """
    Entry point per l'importazione ZIP.
    """
    log_msgs = []
    try:
        # Gestione sia path stringa che file object
        if isinstance(zip_path_or_file, str):
            if not zipfile.is_zipfile(zip_path_or_file):
                return ["ERRORE: File non valido."]
            z = zipfile.ZipFile(zip_path_or_file, 'r')
        else:
            if not zipfile.is_zipfile(zip_path_or_file):
                return ["ERRORE: File non valido."]
            z = zipfile.ZipFile(zip_path_or_file, 'r')

        with z:
            file_list = [f for f in z.namelist() if f.lower().endswith('.csv') and not f.startswith('__MACOSX')]
            
            if not file_list:
                return ["Nessun CSV trovato nello ZIP."]
            
            for filename in file_list:
                with z.open(filename) as csv_file:
                    content = csv_file.read()
                    elabora_file_presenze_csv(content, filename, log_msgs)
                    
    except Exception as e:
        return [f"Errore critico ZIP: {str(e)}"]
        
    return log_msgs

# ==================================================================================
# SEZIONE 3: MOTORE ETL E GENERAZIONE XML (ORIGINALI - PRESERVATI)
# ==================================================================================

def consolidamento_totale(mappa, percorsi, ore_standard=173):
    """
    MOTORE ETL INTEGRALE CON LOGICA CONTRATTUALE:
    - PT=0 -> 100%
    - Autopilota Full-Time (8x5) ignorando file presenze
    - Riparametrazione mese su ore standard inserite
    - Anti-Duplicazione Morbida per recupero dati reali
    """
    db_consolidato = {}
    ore_std_dec = Decimal(str(ore_standard))
    
    # 1. ANAGRAFICA E LOGICA CONTRATTUALE
    if percorsi.get('anagrafica'):
        df = smart_read(percorsi['anagrafica'])
        m = mappa['anagrafica']
        for _, row in df.iterrows():
            c_az = clean_id(row.iloc[get_idx(m, 'Azienda_Cod', 'anagrafica')])
            mat = clean_id(row.iloc[get_idx(m, 'Matricola', 'anagrafica')])
            
            if c_az and mat:
                chiave = f"{c_az}_{mat}"
                if chiave not in db_consolidato:
                    pt_raw = clean_dec_importer(row.iloc[get_idx(m, 'Perc_PT', 'anagrafica')])
                    pt = Decimal("100.00") if pt_raw == Decimal("0.00") else pt_raw
                    pt_ratio = pt / Decimal("100")
                    ore_mese_riparametrate = (ore_std_dec * pt_ratio).quantize(Decimal("0.01"))
                    
                    presenze_base = {g: Decimal("0.00") for g in ['Lun','Mar','Mer','Gio','Ven','Sab','Dom']}
                    if pt == Decimal("100.00"):
                        presenze_base = {'Lun': Decimal("8.00"), 'Mar': Decimal("8.00"), 'Mer': Decimal("8.00"), 'Gio': Decimal("8.00"), 'Ven': Decimal("8.00"), 'Sab': Decimal("0.00"), 'Dom': Decimal("0.00")}
                    
                    db_consolidato[chiave] = {
                        'Azienda_Cod': c_az, 
                        'Matricola': mat,
                        'Azienda_Rag': str(row.iloc[get_idx(m, 'Azienda_Rag', 'anagrafica')]),
                        'Nominativo': str(row.iloc[get_idx(m, 'Nominativo', 'anagrafica')]),
                        'Qualifica': str(row.iloc[get_idx(m, 'Qualifica', 'anagrafica')]),
                        'Tipo_Contratto': str(row.iloc[get_idx(m, 'Tipo_Contratto', 'anagrafica')]),
                        'Livello': str(row.iloc[get_idx(m, 'Livello', 'anagrafica')]),
                        'Perc_PT': pt,
                        'ore_mese_standard': ore_mese_riparametrate,
                        'Assunzione': str(row.iloc[get_idx(m, 'Assunzione', 'anagrafica')]),
                        'presenze_settimanali': presenze_base,
                        'h_ord': Decimal("0.00"), 'h_extra': Decimal("0.00"),
                        'lordo': Decimal("0.00"), 'fatto': Decimal("0.00"),
                        'Tipo_Retribuzione': '' 
                    }

    # 2. PRESENZE: Solo per Part-Time (Logica Excel Vecchia - Mantenuta per compatibilità)
    if percorsi.get('presenze') and 'presenze' in mappa:
        # Se il file presenze è un ZIP, viene ignorato qui e gestito dal nuovo flusso in views.py
        if not str(percorsi['presenze']).lower().endswith('.zip'):
            df_pre = smart_read(percorsi['presenze'])
            m_pre = mappa['presenze']
            idx_mat_pre = get_idx(m_pre, 'Matricola', 'presenze')
            visti_presenze = set()
            
            for i in range(len(df_pre)):
                mat_f = clean_id(df_pre.iloc[i].iloc[idx_mat_pre])
                if mat_f and mat_f not in visti_presenze:
                    for chiave, dati_dip in db_consolidato.items():
                        if chiave.endswith(f"_{mat_f}"):
                            visti_presenze.add(mat_f)
                            if dati_dip['Perc_PT'] < Decimal("100.00"):
                                for offset in [2, 4]:
                                    t_idx = i + offset
                                    if t_idx < len(df_pre):
                                        t_row = df_pre.iloc[t_idx]
                                        for g in ['Lun','Mar','Mer','Gio','Ven','Sab','Dom']:
                                            if m_pre.get(g) and str(m_pre[g]).strip() != "":
                                                dati_dip['presenze_settimanali'][g] += clean_hours(t_row.iloc[int(m_pre[g])])

    # 3. RETRIBUZIONI
    if percorsi.get('retribuzioni') and 'retribuzioni' in mappa:
        df_ret = smart_read(percorsi['retribuzioni'])
        m_ret = mappa['retribuzioni']
        
        for _, row in df_ret.iterrows():
            mat_r = clean_id(row.iloc[get_idx(m_ret, 'Matricola', 'retribuzioni')])
            for chiave, dati_dip in db_consolidato.items():
                if chiave.endswith(f"_{mat_r}"):
                    tipo_raw = str(row.iloc[get_idx(m_ret, 'Tipo_Retribuzione', 'retribuzioni')]).strip()
                    fatto_raw = clean_dec_importer(row.iloc[get_idx(m_ret, 'Retribuzione_Fatto', 'retribuzioni')])
                    
                    if tipo_raw and not dati_dip['Tipo_Retribuzione']:
                        dati_dip['Tipo_Retribuzione'] = tipo_raw
                    
                    if fatto_raw > 0 and dati_dip['fatto'] == Decimal("0.00"):
                        fatto = fatto_raw
                        tipo = dati_dip['Tipo_Retribuzione'].lower()
                        pt_ratio = dati_dip['Perc_PT'] / Decimal("100")
                        
                        h_tot = sum(dati_dip['presenze_settimanali'].values())
                        soglia = Decimal("40.00") * pt_ratio
                        h_ord = min(h_tot, soglia)
                        h_extra = max(Decimal("0.00"), h_tot - soglia)
                        
                        if 'orar' in tipo:
                            molt_base = dati_dip['ore_mese_standard']
                            lordo = (molt_base * fatto) + (h_extra * fatto * Decimal("1.25"))
                        else:
                            lordo = fatto * pt_ratio
                        
                        dati_dip.update({
                            'fatto': fatto, 'lordo': lordo.quantize(Decimal("0.01")),
                            'h_ord': h_ord.quantize(Decimal("0.01")), 
                            'h_extra': h_extra.quantize(Decimal("0.01"))
                        })
                        dati_dip.update(calcola_stime_finanziarie(lordo))
                    
                    for x in range(1, 19):
                        e_field = f'Elemento_{x}'
                        if e_field in m_ret and str(m_ret[e_field]).strip() != "":
                            val_el = clean_dec_importer(row.iloc[int(m_ret[e_field])])
                            if val_el > 0:
                                dati_dip[e_field.lower()] = val_el

    # 4. RATEI
    if percorsi.get('ratei') and 'ratei' in mappa:
        df_rat = smart_read(percorsi['ratei'])
        m_rat = mappa['ratei']
        campi_ratei = {
            'Ferie_Res': 'ferie_res', 'Ferie_Mat': 'ferie_mat',
            'Perm_Res': 'perm_res', 'Perm_Mat': 'perm_mat',
            'Rol_Res': 'rol_res', 'Rol_Mat': 'rol_mat',
            'ExFes_Res': 'exfes_res', 'ExFes_Mat': 'exfes_mat'
        }
        for _, row in df_rat.iterrows():
            mat_rat = clean_id(row.iloc[get_idx(m_rat, 'Matricola', 'ratei')])
            for chiave, dati_dip in db_consolidato.items():
                if chiave.endswith(f"_{mat_rat}"):
                    for map_f, db_f in campi_ratei.items():
                        if m_rat.get(map_f):
                            val_rat = clean_dec_importer(row.iloc[int(m_rat[map_f])])
                            if val_rat != Decimal("0.00") and dati_dip.get(db_f, Decimal("0.00")) == Decimal("0.00"):
                                dati_dip[db_f] = val_rat

    # 5. STACOS
    if percorsi.get('stacos') and 'stacos' in mappa:
        df_sta = smart_read(percorsi['stacos'])
        m_sta = mappa['stacos']
        for _, row in df_sta.iterrows():
            mat_sta = clean_id(row.iloc[get_idx(m_sta, 'Matricola', 'stacos')])
            for chiave, dati_dip in db_consolidato.items():
                if chiave.endswith(f"_{mat_sta}"):
                    for map_f, db_f in {'Inps_Ditta': 'inps_ditta', 'Inail_Ditta': 'inail_ditta', 'TFR': 'tfr'}.items():
                        if m_sta.get(map_f):
                            val_sta = clean_dec_importer(row.iloc[int(m_sta[map_f])])
                            if val_sta != Decimal("0.00") and dati_dip.get(db_f, Decimal("0.00")) == Decimal("0.00"):
                                dati_dip[db_f] = val_sta

    return db_consolidato

def archivia_e_genera_xml(dati_consolidati, nome_file, ore_standard="173"):
    """Generazione XML e salvataggio DB storico integrale."""
    sessione = SessioneImportazione.objects.create(
        nome_file_principale=nome_file,
        totale_dipendenti=len(dati_consolidati),
        costo_totale_periodo=sum(d.get('costo', 0) for d in dati_consolidati.values())
    )
    root = ET.Element("StudioETL_Export", sessione_id=str(sessione.id))
    
    for chiave, d in dati_consolidati.items():
        RecordStoricoDipendente.objects.create(
            sessione=sessione, codice_azienda=d['Azienda_Cod'], ragione_sociale=d.get('Azienda_Rag', ''),
            matricola=d['Matricola'], nominativo=d['Nominativo'], qualifica=d.get('Qualifica', ''),
            tipo_contratto=d.get('Tipo_Contratto', ''), livello=d.get('Livello', ''),
            perc_part_time=d['Perc_PT'], lordo=d['lordo'], retribuzione_di_fatto=d['fatto'],
            tipo_retribuzione=d.get('Tipo_Retribuzione', ''), inps_ditta=d.get('inps_ditta', 0),
            inail_ditta=d.get('inail_ditta', 0), tfr_quota_mese=d.get('tfr', 0),
            costo_aziendale=d.get('costo', 0), netto_stimato=d.get('netto', 0),
            ore_ordinarie=d.get('h_ord', 0), ore_straordinarie=d.get('h_extra', 0),
            elemento_1=d.get('elemento_1', 0), elemento_2=d.get('elemento_2', 0), elemento_3=d.get('elemento_3', 0),
            elemento_4=d.get('elemento_4', 0), elemento_5=d.get('elemento_5', 0), elemento_6=d.get('elemento_6', 0),
            elemento_7=d.get('elemento_7', 0), elemento_8=d.get('elemento_8', 0), elemento_9=d.get('elemento_9', 0),
            elemento_10=d.get('elemento_10', 0), elemento_11=d.get('elemento_11', 0), elemento_12=d.get('elemento_12', 0),
            elemento_13=d.get('elemento_13', 0), elemento_14=d.get('elemento_14', 0), elemento_15=d.get('elemento_15', 0),
            elemento_16=d.get('elemento_16', 0), elemento_17=d.get('elemento_17', 0), elemento_18=d.get('elemento_18', 0),
            ferie_residue=d.get('ferie_res', 0), ferie_maturate=d.get('ferie_mat', 0),
            permessi_residui=d.get('perm_res', 0), permessi_maturati=d.get('perm_mat', 0),
            rol_residuo=d.get('rol_res', 0), rol_maturato=d.get('rol_mat', 0),
            ex_fest_residuo=d.get('exfes_res', 0), ex_fest_maturato=d.get('exfes_mat', 0),
            dati_completi_json={k: str(v) for k, v in d.items()}
        )
        dip = ET.SubElement(root, "Dipendente")
        
        # INIEZIONE CAMPO FISSO ORE
        ET.SubElement(dip, "Ore_Standard_Mese").text = str(ore_standard)
        
        for k, v in d.items():
            if k != 'presenze_settimanali': 
                ET.SubElement(dip, k).text = str(v)
    
    return ET.tostring(root, encoding='utf-8'), sessione.id