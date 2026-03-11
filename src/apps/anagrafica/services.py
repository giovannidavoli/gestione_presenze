import pandas as pd
from django.db import transaction
from django.db.models import Q
from .models import (
    Dipendente, Azienda, Studio, CCNL, 
    CausaleAssenza, PresenzaGiornaliera, EventoAssenza
)
import logging
import zipfile
import csv
import io
import os
from decimal import Decimal
from datetime import date, datetime, timedelta
from statistics import mode
from calendar import monthrange

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. FUNZIONI DI UTILITÀ E PULIZIA DATI
# ==============================================================================

def pulisci_importo(valore):
    """Converte stringhe o numeri in Decimal sicuro per i calcoli monetari."""
    if pd.isna(valore) or valore == '' or valore is None:
        return Decimal("0.00")
    if isinstance(valore, (int, float)):
        return Decimal(str(valore))
    if isinstance(valore, str):
        valore = valore.strip().replace('€', '').replace('%', '').strip()
        if ',' in valore:
            valore = valore.replace('.', '').replace(',', '.')
        try:
            return Decimal(valore)
        except:
            return Decimal("0.00")
    return Decimal("0.00")

def pulisci_codice(valore):
    """Rimuove zeri iniziali e residui decimali (es. '00022.0' -> '22')."""
    if pd.isna(valore) or valore is None: return ""
    # Forza la conversione in stringa prima dello strip per evitare errore 'int' object has no attribute 'strip'
    s = str(valore).strip().split('.')[0]
    s = s.lstrip('0')
    return s if s else "0"

def pulisci_data(valore):
    """Gestisce date Excel (numeriche) o stringhe in formato italiano."""
    if pd.isna(valore) or valore == '': return None
    try:
        if isinstance(valore, (datetime, date)): return valore
        return pd.to_datetime(valore, dayfirst=True).date()
    except:
        return None

# ==============================================================================
# 2. LOGICA CALENDARIO E FESTIVITÀ ITALIANE
# ==============================================================================

def calcola_pasquetta(anno):
    """Calcola il Lunedì dell'Angelo per un dato anno."""
    a = anno % 19
    b = anno // 100
    c = anno % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mese = (h + l - 7 * m + 114) // 31
    giorno = ((h + l - 7 * m + 114) % 31) + 1
    return date(anno, mese, giorno) + timedelta(days=1)

def is_giorno_festivo(data_rif, azienda=None):
    """Verifica se una data è festiva (Nazionali + Santo Patrono)."""
    feste_fisse = [
        (1, 1), (6, 1), (25, 4), (1, 5), (2, 6), 
        (15, 8), (1, 11), (8, 12), (25, 12), (26, 12)
    ]
    if (data_rif.day, data_rif.month) in feste_fisse: return True
    if data_rif == calcola_pasquetta(data_rif.year): return True
    if azienda and azienda.giorno_patrono == data_rif.day and azienda.mese_patrono == data_rif.month:
        return True
    return False

# ==============================================================================
# 3. RICERCA INTELLIGENTE DIPENDENTE (ROBUSTA E PROTETTA)
# ==============================================================================

def cerca_dipendente(matricola_csv, codice_azienda_csv):
    """Ricerca dipendente con protezione contro attributi mancanti su oggetti int."""
    matr_clean = pulisci_codice(matricola_csv)
    az_clean = pulisci_codice(codice_azienda_csv)
    if not matr_clean or not az_clean: return None
    
    # CORREZIONE: str(codice_azienda_csv).strip() evita l'errore 'int' object has no attribute 'strip'
    dip = Dipendente.objects.filter(
        Q(azienda__codice=az_clean) | Q(azienda__codice=str(codice_azienda_csv).strip()),
        codice=matr_clean
    ).first()
    return dip

# ==============================================================================
# 4. IMPORTAZIONE CAUSALI GIS (IBRIDA)
# ==============================================================================

def importa_causali_gis(file_path, log_msgs):
    """Popola le causali rilevando automaticamente Excel o CSV."""
    try:
        if file_path.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file_path, header=0, usecols=[0, 1], names=['Codice', 'Descrizione'])
        else:
            df = pd.read_csv(file_path, sep=None, engine='python', encoding='latin1', quoting=3, usecols=[0, 1], names=['Codice', 'Descrizione'], header=0)

        count = 0
        for _, row in df.iterrows():
            cod = str(row['Codice']).strip().replace('"', '')
            desc = str(row['Descrizione']).strip().replace('"', '')
            if cod and cod.lower() != 'nan' and cod != 'Codice':
                CausaleAssenza.objects.update_or_create(codice=cod, defaults={'descrizione': desc})
                count += 1
        log_msgs.append(f"✅ Importate {count} causali Ranocchi con successo.")
    except Exception as e: log_msgs.append(f"❌ Errore causali: {e}")

# ==============================================================================
# 5. ELABORAZIONE REGISTRO E ARTICOLAZIONE ORARIO (PROTETTA)
# ==============================================================================

def elabora_csv_presenze(csv_bytes, filename, log_msgs, mappa):
    """Estrae l'articolazione oraria con protezione totale dai tipi dato."""
    try:
        content_str = csv_bytes.decode('latin1')
        lines = content_str.splitlines()
        if len(lines) <= mappa.pre_riga_inizio + 1: return

        cod_az_csv, meta_anno, meta_mese = "0", datetime.now().year, datetime.now().month
        for line in lines[:5]:
            parts = line.split(';')
            # str(...).strip() protegge dall'errore oggetto int
            if len(parts) > 1 and 'Azienda' in parts[0]: cod_az_csv = str(parts[1]).strip()
            if len(parts) > 1 and 'Anno' in parts[0]: meta_anno = int(parts[1])
            if len(parts) > 3 and 'Mese' in parts[2]: meta_mese = int(parts[3])

        df = pd.read_csv(
            io.BytesIO(csv_bytes), sep=';', encoding='latin1', 
            header=None, skiprows=mappa.pre_riga_inizio + 1,
            names=range(50), engine='python'
        )
        
        current_dip = None
        count_articolazione = 0

        for idx, row in df.iterrows():
            # Identificazione matricola con pulizia sicura
            raw_matr = str(row.iloc[mappa.pre_col_matricola]).strip().split('.')[0]
            if raw_matr != "" and raw_matr.lower() != 'nan':
                # Determinazione azienda di riferimento (intestazione o colonna)
                az_rif = cod_az_csv
                if mappa.pre_col_azienda_cod >= 0:
                    az_rif = str(row.iloc[mappa.pre_col_azienda_cod]).strip()
                
                current_dip = cerca_dipendente(raw_matr, az_rif)
            
            if not current_dip: continue
            
            tipo_riga = str(row.iloc[mappa.pre_col_tipo]).strip()
            
            if tipo_riga == "Ore lavorate":
                start_col = mappa.pre_col_tipo + 1
                
                # 1. Popolamento ARTICOLAZIONE SETTIMANALE (7 Giorni)
                for g in range(1, 8):
                    col_idx = start_col + (g - 1)
                    val_ore = pulisci_importo(row.iloc[col_idx])
                    
                    try:
                        data_g = date(meta_anno, meta_mese, g)
                        weekday = data_g.weekday()
                        
                        if weekday == 0: current_dip.ore_lun = val_ore
                        elif weekday == 1: current_dip.ore_mar = val_ore
                        elif weekday == 2: current_dip.ore_mer = val_ore
                        elif weekday == 3: current_dip.ore_gio = val_ore
                        elif weekday == 4: current_dip.ore_ven = val_ore
                        elif weekday == 5: current_dip.ore_sab = val_ore
                        elif weekday == 6: current_dip.ore_dom = val_ore
                    except ValueError: continue
                
                current_dip.save()
                count_articolazione += 1

                # 2. Popolamento REGISTRO PRESENZE (Intero Mese)
                for g in range(1, 32):
                    col_idx = start_col + (g - 1)
                    if col_idx >= len(row) or pd.isna(row.iloc[col_idx]): continue
                    try:
                        data_g = date(meta_anno, meta_mese, g)
                        presenza, _ = PresenzaGiornaliera.objects.get_or_create(dipendente=current_dip, data=data_g)
                        presenza.ore_lavorate = pulisci_importo(row.iloc[col_idx])
                        presenza.is_festivo = is_giorno_festivo(data_g, current_dip.azienda)
                        presenza.save()
                    except ValueError: continue

        log_msgs.append(f"✅ {filename}: Aggiornata Articolazione e Registro per {count_articolazione} dipendenti.")
    except Exception as e: log_msgs.append(f"❌ Errore Registro {filename}: {e}")

# ==============================================================================
# 6. ORCHESTRATORE SINCRONIZZAZIONE (INTEGRALE - 18 ELEMENTI E 16 RATEI)
# ==============================================================================

def importa_dati_excel_gestionale(caricamento):
    mappa = caricamento.mappatura
    log_msgs = []
    
    with transaction.atomic():
        if caricamento.file_causali_gis:
            importa_causali_gis(caricamento.file_causali_gis.path, log_msgs)

        # ANAGRAFICA E TURNOVER
        if caricamento.file_anagrafica:
            df = pd.read_excel(caricamento.file_anagrafica.path, header=None, skiprows=mappa.ana_riga_inizio-1)
            for _, r in df.iterrows():
                cod_az = pulisci_codice(r[mappa.ana_col_azienda_cod])
                matr = pulisci_codice(r[mappa.ana_col_matricola])
                if not cod_az or not matr: continue
                studio = Studio.objects.first() or Studio.objects.create(nome="Studio Principale")
                azienda, _ = Azienda.objects.update_or_create(codice=cod_az, defaults={'ragione_sociale': str(r[mappa.ana_col_azienda_ragione]).strip(), 'studio': studio})
                Dipendente.objects.update_or_create(azienda=azienda, codice=matr, defaults={
                    'cognome_nome': str(r[mappa.ana_col_nominativo]).strip(),
                    'sede_lavoro': str(r[mappa.ana_col_sede_lavoro]).strip() if pd.notna(r[mappa.ana_col_sede_lavoro]) else '',
                    'indirizzo': str(r[mappa.ana_col_indirizzo]).strip() if pd.notna(r[mappa.ana_col_indirizzo]) else '',
                    'comune': str(r[mappa.ana_col_comune]).strip() if pd.notna(r[mappa.ana_col_comune]) else '',
                    'qualifica': str(r[mappa.ana_col_qualifica]).strip() if pd.notna(r[mappa.ana_col_qualifica]) else '',
                    'tipo_contratto': str(r[mappa.ana_col_tipo_contratto]).strip() if pd.notna(r[mappa.ana_col_tipo_contratto]) else '',
                    'livello': str(r[mappa.ana_col_livello]).strip() if pd.notna(r[mappa.ana_col_livello]) else '',
                    'perc_part_time': pulisci_importo(r[mappa.ana_col_perc_part_time]),
                    'data_assunzione': pulisci_data(r[mappa.ana_col_assunzione]),
                    'data_cessazione': pulisci_data(r[mappa.ana_col_cessazione]),
                    'data_termine': pulisci_data(r[mappa.ana_col_termine]),
                })
            log_msgs.append("✅ Anagrafica e Turnover sincronizzati.")

        # RETRIBUZIONI (18 ELEMENTI PAGA)
        if caricamento.file_retribuzioni:
            df = pd.read_excel(caricamento.file_retribuzioni.path, header=None, skiprows=mappa.ret_riga_inizio-1)
            for _, r in df.iterrows():
                d = cerca_dipendente(r[mappa.ret_col_matricola], r[mappa.ret_col_azienda_cod])
                if d:
                    d.tipo_paga = str(r[mappa.ret_col_tipo_paga]).strip()
                    d.lordo_mensile_calcolato = pulisci_importo(r[mappa.ret_col_lordo_fatto])
                    d.elemento_1 = pulisci_importo(r[mappa.ret_col_elementi_start + 0]); d.elemento_2 = pulisci_importo(r[mappa.ret_col_elementi_start + 1]); d.elemento_3 = pulisci_importo(r[mappa.ret_col_elementi_start + 2])
                    d.elemento_4 = pulisci_importo(r[mappa.ret_col_elementi_start + 3]); d.elemento_5 = pulisci_importo(r[mappa.ret_col_elementi_start + 4]); d.elemento_6 = pulisci_importo(r[mappa.ret_col_elementi_start + 5])
                    d.elemento_7 = pulisci_importo(r[mappa.ret_col_elementi_start + 6]); d.elemento_8 = pulisci_importo(r[mappa.ret_col_elementi_start + 7]); d.elemento_9 = pulisci_importo(r[mappa.ret_col_elementi_start + 8])
                    d.elemento_10 = pulisci_importo(r[mappa.ret_col_elementi_start + 9]); d.elemento_11 = pulisci_importo(r[mappa.ret_col_elementi_start + 10]); d.elemento_12 = pulisci_importo(r[mappa.ret_col_elementi_start + 11])
                    d.elemento_13 = pulisci_importo(r[mappa.ret_col_elementi_start + 12]); d.elemento_14 = pulisci_importo(r[mappa.ret_col_elementi_start + 13]); d.elemento_15 = pulisci_importo(r[mappa.ret_col_elementi_start + 14])
                    d.elemento_16 = pulisci_importo(r[mappa.ret_col_elementi_start + 15]); d.elemento_17 = pulisci_importo(r[mappa.ret_col_elementi_start + 16]); d.elemento_18 = pulisci_importo(r[mappa.ret_col_elementi_start + 17])
                    d.save()
            log_msgs.append("✅ Retribuzioni e 18 elementi paga aggiornati.")

        # COSTI STACOS
        if caricamento.file_stacos:
            df = pd.read_excel(caricamento.file_stacos.path, header=None, skiprows=1)
            for _, r in df.iterrows():
                d = cerca_dipendente(r[mappa.sta_col_matricola], r[mappa.sta_col_azienda_cod])
                if d:
                    d.costo_inps_ditta = pulisci_importo(r[mappa.sta_col_inps]); d.costo_inail_ditta = pulisci_importo(r[mappa.sta_col_inail]); d.rateo_tfr = pulisci_importo(r[mappa.sta_col_tfr]); d.save()

        # RATEI (16 STATI)
        if caricamento.file_ratei:
            df = pd.read_excel(caricamento.file_ratei.path, header=None, skiprows=1)
            for _, r in df.iterrows():
                d = cerca_dipendente(r[mappa.rat_col_matricola], r[mappa.rat_col_azienda_cod])
                if d:
                    d.ferie_residuo_ap = pulisci_importo(r[mappa.rat_col_ferie_ap]); d.ferie_maturate = pulisci_importo(r[mappa.rat_col_ferie_mat]); d.ferie_godute = pulisci_importo(r[mappa.rat_col_ferie_god]); d.ferie_residuo_attuale = pulisci_importo(r[mappa.rat_col_ferie_res])
                    d.permessi_residuo_ap = pulisci_importo(r[mappa.rat_col_perm_ap]); d.permessi_maturati = pulisci_importo(r[mappa.rat_col_perm_mat]); d.permessi_goduti = pulisci_importo(r[mappa.rat_col_perm_god]); d.permessi_residuo_attuale = pulisci_importo(r[mappa.rat_col_perm_res])
                    d.rol_residuo_ap = pulisci_importo(r[mappa.rat_col_rol_ap]); d.rol_maturati = pulisci_importo(r[mappa.rat_col_rol_mat]); d.rol_goduti = pulisci_importo(r[mappa.rat_col_rol_god]); d.rol_residuo_attuale = pulisci_importo(r[mappa.rat_col_rol_res])
                    d.ex_fest_residuo_ap = pulisci_importo(r[mappa.rat_col_exfest_ap]); d.ex_fest_maturati = pulisci_importo(r[mappa.rat_col_exfest_mat]); d.ex_fest_goduti = pulisci_importo(r[mappa.rat_col_exfest_god]); d.ex_fest_residuo_attuale = pulisci_importo(r[mappa.rat_col_exfest_res]); d.save()

        # PRESENZE ZIP
        if caricamento.file_presenze:
            with zipfile.ZipFile(caricamento.file_presenze.path, 'r') as z:
                for f in [x for x in z.namelist() if x.lower().endswith('.csv')]:
                    with z.open(f) as csv_file:
                        elabora_csv_presenze(csv_file.read(), f, log_msgs, mappa)

    return log_msgs

# ==============================================================================
# 7. LOGICA PIANIFICATO, ESPORTAZIONE E ANTEPRIMA (COERENTE)
# ==============================================================================

def applica_pianificato_mensile(dipendente, anno, mese):
    _, num_giorni = monthrange(anno, mese)
    orario_sett = {0: dipendente.ore_lun, 1: dipendente.ore_mar, 2: dipendente.ore_mer, 3: dipendente.ore_gio, 4: dipendente.ore_ven, 5: dipendente.ore_sab, 6: dipendente.ore_dom}
    count = 0
    with transaction.atomic():
        for g in range(1, num_giorni + 1):
            data_g = date(anno, mese, g)
            ore_prev = orario_sett[data_g.weekday()]
            if ore_prev > 0 and not is_giorno_festivo(data_g, dipendente.azienda):
                pres, _ = PresenzaGiornaliera.objects.get_or_create(dipendente=dipendente, data=data_g)
                if pres.ore_lavorate == 0:
                    pres.ore_lavorate = ore_prev; pres.di_cui_notturne = dipendente.notturno_standard; pres.save(); count += 1
    return f"✅ Pianificato applicato per {count} giorni."

def esporta_presenze_ranocchi(azienda, anno, mese):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_NONE)
    writer.writerow(['Azienda', azienda.codice, 'Sede', '0000', '', ''])
    writer.writerow(['Anno', anno, 'Mese', str(mese).zfill(2), '', ''])
    writer.writerow([]); writer.writerow(['', '', ''] + [str(g).zfill(2) for g in range(1, 32)])
    writer.writerow(['Matricola', 'Cognome e nome', 'Tipo'] + ['Ore' for _ in range(1, 32)])
    for dip in azienda.dipendenti.all():
        presenze = {p.data.day: p for p in dip.presenze.filter(data__year=anno, data__month=mese)}
        row_lav = [dip.codice, dip.cognome_nome, 'Ore lavorate']; row_not = ['', '', 'di cui notturne']
        for g in range(1, 32):
            p = presenze.get(g)
            row_lav.append(str(p.ore_lavorate).replace('.', ',') if p and p.ore_lavorate else '')
            row_not.append(str(p.di_cui_notturne).replace('.', ',') if p and p.di_cui_notturne else '')
        writer.writerow(row_lav); writer.writerow(row_not)
    return output.getvalue()

def genera_dati_anteprima(mappatura_id, file_obj=None):
    preview_data = {'headers': [], 'rows': []}
    if not file_obj: return preview_data
    try:
        path = file_obj.path if hasattr(file_obj, 'path') else file_obj
        if str(path).lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(path, header=None, nrows=10)
            preview_data['headers'] = [f"Col {i}" for i in range(len(df.columns))]; preview_data['rows'] = df.fillna('').values.tolist()
    except Exception as e: preview_data['error'] = str(e)
    return preview_data