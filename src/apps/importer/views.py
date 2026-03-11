from django.shortcuts import render
from django.http import HttpResponse
from django.core.files.storage import FileSystemStorage
from django.contrib import messages
from django.apps import apps
# Aggiunto 'importa_presenze_zip' agli import esistenti per non rompere il vecchio codice
from .services import smart_read, consolidamento_totale, archivia_e_genera_xml, importa_presenze_zip
from .models import ConfigurazioneMapper, SessioneImportazione, RecordStoricoDipendente
import os
import pandas as pd # Aggiunto per sicurezza nella gestione anteprime
from datetime import datetime

def sync_verso_presenze(dati_finali):
    """
    PONTE DIRETTO: Popola le tabelle del gestionale.
    Puntiamo all'app 'anagrafica' come indicato.
    """
    # Identificazione dinamica dell'app corretta
    target_label = None
    for label in ['anagrafica', 'apps.anagrafica', 'apps_anagrafica']:
        try:
            # Proviamo a vedere se questa label contiene il modello Studio
            apps.get_model(label, 'Studio')
            target_label = label
            break
        except (LookupError, ValueError):
            continue

    if not target_label:
        raise Exception("Impossibile trovare i modelli nell'app 'anagrafica'. Verifica che sia presente in INSTALLED_APPS.")

    # Recupero modelli
    Studio = apps.get_model(target_label, 'Studio')
    Azienda = apps.get_model(target_label, 'Azienda')
    Dipendente = apps.get_model(target_label, 'Dipendente')

    # 1. Studio di default
    studio_base = Studio.objects.first()
    if not studio_base:
        studio_base = Studio.objects.create(nome="Studio Professionale", sede="Sede Centrale")

    for chiave, d in dati_finali.items():
        # 2. Azienda
        azienda, _ = Azienda.objects.get_or_create(
            codice=d['Azienda_Cod'],
            defaults={
                'ragione_sociale': d.get('Azienda_Rag', f"Azienda {d['Azienda_Cod']}"), 
                'studio': studio_base
            }
        )

        # 3. Data Assunzione
        data_ass = None
        if d.get('Assunzione'):
            try:
                val_ass = str(d['Assunzione']).strip()
                data_ass = datetime.strptime(val_ass, '%d/%m/%Y').date()
            except:
                pass

        # 4. Aggiornamento Dipendente
        Dipendente.objects.update_or_create(
            azienda=azienda,
            codice=d['Matricola'],
            defaults={
                'cognome_nome': d['Nominativo'],
                'qualifica': d.get('Qualifica', ''),
                'tipo_paga': d.get('Tipo_Retribuzione', 'Mensile'),
                'perc_part_time': d.get('Perc_PT', 100),
                'data_assunzione': data_ass,
                'lordo_mensile_calcolato': d.get('lordo', 0),
                'costo_inps_ditta': d.get('inps_ditta', 0),
                'costo_inail_ditta': d.get('inail_ditta', 0),
                'rateo_tfr': d.get('tfr', 0),
                'ferie_residuo_ap': d.get('ferie_res', 0),
                'permessi_residuo_ap': d.get('perm_res', 0),
                'rol_residuo_ap': d.get('rol_res', 0),
                'ex_fest_residuo_ap': d.get('exfes_res', 0),
                'ore_lun': d['presenze_settimanali'].get('Lun', 0),
                'ore_mar': d['presenze_settimanali'].get('Mar', 0),
                'ore_mer': d['presenze_settimanali'].get('Mer', 0),
                'ore_gio': d['presenze_settimanali'].get('Gio', 0),
                'ore_ven': d['presenze_settimanali'].get('Ven', 0),
                'ore_sab': d['presenze_settimanali'].get('Sab', 0),
                'ore_dom': d['presenze_settimanali'].get('Dom', 0),
            }
        )

def mapper_dashboard(request):
    """Dashboard ETL GIS."""
    mapping_fields = {
        'anagrafica': ['Azienda_Cod', 'Azienda_Rag', 'Matricola', 'Nominativo', 'Qualifica', 'Tipo_Contratto', 'Livello', 'Perc_PT', 'Assunzione', 'Cessazione', 'Cessazione_Prevista'],
        'retribuzioni': ['Matricola', 'Tipo_Retribuzione', 'Retribuzione_Fatto'] + [f'Elemento_{i}' for i in range(1, 19)],
        'ratei': ['Matricola', 'Ferie_Res', 'Ferie_Mat', 'Perm_Res', 'Perm_Mat', 'Rol_Res', 'Rol_Mat', 'ExFes_Res', 'ExFes_Mat'],
        'stacos': ['Matricola', 'Inps_Ditta', 'Inail_Ditta', 'TFR'],
        'presenze': ['Matricola', 'Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']
    }
    
    context = {'files_data': {}, 'mapping_fields': mapping_fields, 'anteprima_finale': None, 'ore_standard': 173}
    fs = FileSystemStorage(location='/tmp/')

    config = ConfigurazioneMapper.objects.filter(nome_profilo="Ranocchi Standard").first()
    context['saved_mapping'] = config.mappatura_json if config else {}

    if request.method == 'POST':
        ore_std_input = request.POST.get('ore_standard', '173')
        context['ore_standard'] = ore_std_input

        if 'btn_ispeziona' in request.POST:
            for key in mapping_fields.keys():
                if key in request.FILES:
                    f = request.FILES[key]
                    
                    # --- MODIFICA PER GESTIONE ZIP PRESENZE ---
                    # Se il file è 'presenze' ed è un .zip, usiamo la nuova logica massiva
                    if key == 'presenze' and f.name.lower().endswith('.zip'):
                        try:
                            # Salviamo lo zip temporaneamente
                            path = fs.save(f.name, f)
                            full_path = fs.path(path)
                            
                            # Chiamiamo il servizio massivo
                            logs = importa_presenze_zip(full_path) # Passiamo il path del file
                            
                            # Feedback all'utente
                            count_ok = len([l for l in logs if "Aggiornati" in l])
                            if count_ok > 0:
                                messages.success(request, f"ZIP Presenze elaborato: {len(logs)} file processati.")
                            else:
                                messages.warning(request, "Elaborazione ZIP completata ma nessun dato aggiornato (controlla i log o il formato CSV).")
                                
                            # Non generiamo anteprima tabellare per lo ZIP
                            continue 
                        except Exception as e:
                            messages.error(request, f"Errore apertura ZIP: {e}")
                            continue
                    # ------------------------------------------

                    path = fs.save(f.name, f)
                    full_path = fs.path(path)
                    
                    # Fallback robusto se smart_read non dovesse funzionare per qualche motivo
                    try:
                        df = smart_read(full_path)
                    except NameError:
                        # Se smart_read manca (perché services è stato toccato), usiamo pandas diretto
                        df = pd.read_excel(full_path)
                    
                    context['files_data'][key] = {
                        'name': f.name, 'path': full_path, 'preview': df.values.tolist(), 'cols': range(len(df.columns))
                    }
                    request.session[f'path_{key}'] = full_path

        elif any(x in request.POST for x in ['btn_verifica', 'btn_genera_xml', 'btn_popola_db']):
            scelte = {k: {f: request.POST.get(f'map_{k}_{f}') for f in mapping_fields[k]} for k in mapping_fields.keys()}
            percorsi = {k: request.session.get(f'path_{k}') for k in mapping_fields.keys()}
            context['saved_mapping'] = scelte 

            if request.POST.get('salva_configurazione'):
                ConfigurazioneMapper.objects.update_or_create(nome_profilo="Ranocchi Standard", defaults={'mappatura_json': scelte})

            try:
                dati_finali = consolidamento_totale(scelte, percorsi, ore_standard=ore_std_input)
                
                if 'btn_popola_db' in request.POST:
                    sync_verso_presenze(dati_finali)
                    messages.success(request, f"🚀 Sincronizzazione riuscita! {len(dati_finali)} record salvati in 'Anagrafica'.")
                    context['anteprima_finale'] = dati_finali
                elif 'btn_verifica' in request.POST:
                    context['anteprima_finale'] = dati_finali
                elif 'btn_genera_xml' in request.POST:
                    xml_data, s_id = archivia_e_genera_xml(dati_finali, "Export.xml", ore_standard=ore_std_input)
                    response = HttpResponse(xml_data, content_type='application/xml')
                    response['Content-Disposition'] = f'attachment; filename="studio_etl_{s_id}.xml"'
                    return response

                for key in mapping_fields.keys():
                    p = percorsi[key]
                    if p and os.path.exists(p):
                        # Controllo per non rileggere file ZIP come excel
                        if key == 'presenze' and p.endswith('.zip'):
                            continue
                        
                        try:
                            df = smart_read(p)
                        except NameError:
                            df = pd.read_excel(p)
                            
                        context['files_data'][key] = {'name': os.path.basename(p), 'preview': df.values.tolist(), 'cols': range(len(df.columns))}

            except Exception as e:
                messages.error(request, f"Errore: {str(e)}")

    return render(request, 'importer/dashboard.html', context)

def storico_dashboard(request):
    sessione_id = request.GET.get('sessione')
    azienda_cod = request.GET.get('azienda')
    ricerca = request.GET.get('ricerca', '').strip()
    records = RecordStoricoDipendente.objects.select_related('sessione').all().order_by('-sessione__data_operazione', 'codice_azienda', 'nominativo')
    if sessione_id: records = records.filter(sessione_id=sessione_id)
    if azienda_cod: records = records.filter(codice_azienda=azienda_cod)
    if ricerca: records = records.filter(nominativo__icontains=ricerca) | records.filter(matricola__icontains=ricerca)
    context = {
        'records': records,
        'sessioni': SessioneImportazione.objects.all().order_by('-data_operazione'),
        'aziende': RecordStoricoDipendente.objects.values('codice_azienda', 'ragione_sociale').distinct(),
        'current_sessione': sessione_id, 'current_azienda': azienda_cod, 'current_ricerca': ricerca,
    }
    return render(request, 'importer/storico.html', context)