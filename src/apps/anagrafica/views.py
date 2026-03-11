from django.views.generic import TemplateView, DetailView
from django.db.models import Sum, F, DecimalField
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from datetime import date, datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
import calendar
import json
import csv
import io

from .models import (
    Dipendente, CaricamentoDati, Azienda, 
    PresenzaGiornaliera, EventoAssenza, CausaleAssenza
)
from .services import genera_dati_anteprima, is_giorno_festivo

# ==============================================================================
# FUNZIONE DI SICUREZZA (Posizionata correttamente a livello globale)
# ==============================================================================
def check_permessi_azienda(user, azienda):
    """Controlla se l'utente è lo Studio (staff) oppure se è l'azienda proprietaria."""
    if user.is_staff or user.is_superuser:
        return True
    if hasattr(user, 'azienda_gestita') and user.azienda_gestita == azienda:
        return True
    return False

# ==============================================================================
# 1. DASHBOARD GENERALE (CON REDIRECT INTELLIGENTE PER I CLIENTI)
# ==============================================================================
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'anagrafica/dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        # --- IL TELETRASPORTO (Smart Redirect) ---
        # Se chi fa il login NON è lo Studio, ma è un Cliente collegato a un'azienda:
        if not (user.is_staff or user.is_superuser):
            if hasattr(user, 'azienda_gestita') and user.azienda_gestita:
                oggi = date.today()
                # Lo fiondiamo direttamente alla TUA pagina delle presenze del mese in corso!
                return redirect('dashboard_azienda', pk=user.azienda_gestita.id, anno=oggi.year, mese=oggi.month)
        # Se invece è lo Studio, lo facciamo passare alla pagina generale.
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # FILTRO DI SICUREZZA
        if user.is_staff or user.is_superuser:
            dipendenti_qs = Dipendente.objects.select_related('azienda', 'ccnl').all()
            aziende = Azienda.objects.all()
        else:
            if hasattr(user, 'azienda_gestita') and user.azienda_gestita:
                dipendenti_qs = Dipendente.objects.select_related('azienda', 'ccnl').filter(azienda=user.azienda_gestita)
                aziende = Azienda.objects.filter(id=user.azienda_gestita.id)
            else:
                dipendenti_qs = Dipendente.objects.none()
                aziende = Azienda.objects.none()

        costo_tot = Decimal('0.00')
        debito_tot = Decimal('0.00')
        dip_list = []
        for d in dipendenti_qs:
            budget = ((d.lordo_mensile_calcolato or 0) + (d.costo_inps_ditta or 0) + (d.costo_inail_ditta or 0) + (d.rateo_tfr or 0))
            costo_tot += budget
            ore_res = ((d.ferie_residuo_attuale or 0) + (d.permessi_residuo_attuale or 0))
            debito = (ore_res * d.calcola_costo_orario_reale)
            debito_tot += debito
            dip_list.append({
                'obj': d, 'azienda': d.azienda.ragione_sociale, 
                'costo_ora': d.calcola_costo_orario_reale, 
                'ore_residue': ore_res, 'debito_residui': debito, 'budget_mensile': budget
            })
            
        context.update({
            'totale_dipendenti': dipendenti_qs.count(), 
            'totale_aziende': aziende.count(), 
            'costo_totale_mensile': costo_tot, 
            'debito_ratei_totale': debito_tot, 
            'dipendenti': dip_list
        })
        return context

# ==============================================================================
# 2. ANTEPRIMA IMPORTAZIONE (INVARIATA)
# ==============================================================================
class PreviewSincroView(LoginRequiredMixin, DetailView):
    model = CaricamentoDati
    template_name = 'anagrafica/preview_sincro.html'
    context_object_name = 'caricamento'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Solo lo Studio può accedere a questa funzione.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        context['preview_ana'] = genera_dati_anteprima(obj.mappatura, obj.file_anagrafica)
        context['preview_ret'] = genera_dati_anteprima(obj.mappatura, obj.file_retribuzioni)
        context['preview_pres'] = {'info': "Anteprima ZIP processata."}
        return context

# ==============================================================================
# 3. DASHBOARD AZIENDA (LOGICA "PRESUNZIONE DI PRESENZA" + RATEI SMART)
# ==============================================================================
@login_required
def dashboard_azienda(request, pk, anno=None, mese=None):
    azienda = get_object_or_404(Azienda, pk=pk)
    
    # --- LUCCHETTO DI SICUREZZA: Controlla se l'utente può vedere questa azienda ---
    if not check_permessi_azienda(request.user, azienda):
        raise PermissionDenied("Non hai i permessi per visualizzare questa azienda.")
    # -----------------------------------------------------------------------------

    oggi = date.today()
    anno = int(anno) if anno else oggi.year
    mese = int(mese) if mese else oggi.month
    
    data_corr = date(anno, mese, 1)
    mese_prec = data_corr - timedelta(days=1)
    mese_succ = data_corr + timedelta(days=32)
    num_giorni = calendar.monthrange(anno, mese)[1]
    
    nomi_mesi = {1: 'Gennaio', 2: 'Febbraio', 3: 'Marzo', 4: 'Aprile', 5: 'Maggio', 6: 'Giugno', 7: 'Luglio', 8: 'Agosto', 9: 'Settembre', 10: 'Ottobre', 11: 'Novembre', 12: 'Dicembre'}
    nomi_giorni = {'Mon': 'LUN', 'Tue': 'MAR', 'Wed': 'MER', 'Thu': 'GIO', 'Fri': 'VEN', 'Sat': 'SAB', 'Sun': 'DOM'}
    
    giorni_mese = []
    for g in range(1, num_giorni + 1):
        d = date(anno, mese, g)
        wd_eng = d.strftime('%a')
        giorni_mese.append({
            'giorno': g, 'weekday': nomi_giorni.get(wd_eng, wd_eng), 
            'is_festivo': is_giorno_festivo(d, azienda), 'data_iso': d.strftime('%Y-%m-%d')
        })

    dip_data = []
    totali_azienda = {'costo': Decimal(0), 'ore': Decimal(0)}
    dipendenti = azienda.dipendenti.select_related('ccnl').all().order_by('cognome_nome')

    for dip in dipendenti:
        presenze = {p.data.day: p for p in dip.presenze.filter(data__year=anno, data__month=mese)}
        
        row_lav = []; row_not = []
        row_ass1_ore = []; row_ass1_cod = []
        row_ass2_ore = []; row_ass2_cod = []
        
        tot_ore_lav = Decimal(0); tot_ore_not = Decimal(0); tot_ore_ass = Decimal(0)
        goduto_ferie = Decimal(0); goduto_rol = Decimal(0)

        orario_sett = [dip.ore_lun, dip.ore_mar, dip.ore_mer, dip.ore_gio, dip.ore_ven, dip.ore_sab, dip.ore_dom]

        for info in giorni_mese:
            g = info['giorno']
            d = date(anno, mese, g)
            wd = d.weekday()
            ore_standard = orario_sett[wd] if not info['is_festivo'] else Decimal(0)
            
            p = presenze.get(g)
            
            val_lav = ""; val_not = ""
            val_ass1_ore = ""; val_ass1_cod = ""
            val_ass2_ore = ""; val_ass2_cod = ""
            
            if p:
                eventi = list(EventoAssenza.objects.filter(giornata=p).order_by('id'))
                
                if len(eventi) > 0:
                    val_ass1_cod = eventi[0].causale.codice
                    val_ass1_ore = f"{eventi[0].ore:g}"
                    tot_ore_ass += eventi[0].ore
                    cod = eventi[0].causale.codice.upper()
                    if 'F' in cod: goduto_ferie += eventi[0].ore
                    elif 'R' in cod or 'P' in cod: goduto_rol += eventi[0].ore

                if len(eventi) > 1:
                    val_ass2_cod = eventi[1].causale.codice
                    val_ass2_ore = f"{eventi[1].ore:g}"
                    tot_ore_ass += eventi[1].ore
                    cod = eventi[1].causale.codice.upper()
                    if 'F' in cod: goduto_ferie += eventi[1].ore
                    elif 'R' in cod or 'P' in cod: goduto_rol += eventi[1].ore
                
                if p.ore_lavorate > 0:
                    val_lav = f"{p.ore_lavorate:g}"
                    tot_ore_lav += p.ore_lavorate
                elif not eventi and ore_standard > 0 and not info['is_festivo']:
                    pass 

                if p.di_cui_notturne > 0: 
                    val_not = f"{p.di_cui_notturne:g}"
                    tot_ore_not += p.di_cui_notturne
            else:
                if ore_standard > 0:
                    val_lav = f"{ore_standard:g}" 
                    tot_ore_lav += ore_standard   
            
            base_cell = {'giorno': g, 'is_festivo': info['is_festivo'], 'data_iso': info['data_iso'], 'std': f"{ore_standard:g}"}
            
            row_lav.append({**base_cell, 'val': val_lav})
            row_not.append({**base_cell, 'val': val_not})
            row_ass1_ore.append({**base_cell, 'val': val_ass1_ore})
            row_ass1_cod.append({**base_cell, 'val': val_ass1_cod})
            row_ass2_ore.append({**base_cell, 'val': val_ass2_ore})
            row_ass2_cod.append({**base_cell, 'val': val_ass2_cod})

        ore_totali_retribuite = tot_ore_lav + tot_ore_ass
        costo_mese = ore_totali_retribuite * dip.calcola_costo_orario_reale
        
        totali_azienda['costo'] += costo_mese
        totali_azienda['ore'] += ore_totali_retribuite

        residuo_ferie_netto = (dip.ferie_residuo_attuale or 0) - goduto_ferie
        residuo_rol_netto = (dip.permessi_residuo_attuale or 0) - goduto_rol

        dip_data.append({
            'obj': dip,
            'rows': {'lav': row_lav, 'not': row_not, 'ass1_ore': row_ass1_ore, 'ass1_cod': row_ass1_cod, 'ass2_ore': row_ass2_ore, 'ass2_cod': row_ass2_cod},
            'stats': {
                'ore_lav': tot_ore_lav, 'ore_ass': tot_ore_ass, 'ore_not': tot_ore_not, 'costo': costo_mese,
                'ferie_res': residuo_ferie_netto, 'rol_res': residuo_rol_netto
            }
        })

    lista_causali = CausaleAssenza.objects.all().order_by('codice')
    return render(request, 'anagrafica/dashboard_azienda.html', {
        'azienda': azienda, 'dipendenti': dip_data, 'giorni_mese': giorni_mese,
        'lista_causali': lista_causali, 'totali_azienda': totali_azienda,
        'periodo': {'m': mese, 'a': anno, 'nome': nomi_mesi[mese], 'prec': {'m': mese_prec.month, 'a': mese_prec.year}, 'succ': {'m': mese_succ.month, 'a': mese_succ.year}}
    })

# ==============================================================================
# 4. API SALVATAGGIO (INTELLIGENZA: SOTTRAZIONE DIFFERENZIALE + RANGE SMART)
# ==============================================================================
@login_required
def salva_presenze_json(request):
    if request.method != 'POST': return JsonResponse({'status': 'error'}, status=405)
    
    try:
        data = json.loads(request.body)
        modifiche = data.get('modifiche', [])
        
        with transaction.atomic():
            for item in modifiche:
                dip = Dipendente.objects.get(pk=item['dip_id'])
                
                # Controllo permessi prima di salvare
                if not check_permessi_azienda(request.user, dip.azienda):
                    continue

                data_obj = datetime.strptime(item['data'], '%Y-%m-%d').date()
                campo = item['campo']
                valore = str(item['valore']).strip().upper()
                
                wd = data_obj.weekday()
                orario_sett = [dip.ore_lun, dip.ore_mar, dip.ore_mer, dip.ore_gio, dip.ore_ven, dip.ore_sab, dip.ore_dom]
                is_festivo_val = is_giorno_festivo(data_obj, dip.azienda)
                ore_std = orario_sett[wd] if not is_festivo_val else Decimal(0)

                if 'cod' in campo and ore_std == 0: continue 

                presenza, _ = PresenzaGiornaliera.objects.get_or_create(
                    dipendente=dip, data=data_obj, defaults={'is_festivo': is_festivo_val}
                )

                eventi = list(EventoAssenza.objects.filter(giornata=presenza).order_by('id'))
                while len(eventi) < 2: eventi.append(None)

                if campo == 'lav':
                    presenza.ore_lavorate = Decimal(valore.replace(',', '.')) if valore else Decimal(0)
                    presenza.save()
                elif campo == 'not':
                    presenza.di_cui_notturne = Decimal(valore.replace(',', '.')) if valore else Decimal(0)
                    presenza.save()
                elif campo == 'ass1_cod':
                    if not valore: 
                        if eventi[0]: eventi[0].delete()
                    else:
                        causale = CausaleAssenza.objects.filter(codice=valore).first()
                        if causale:
                            if eventi[0]:
                                eventi[0].causale = causale
                                eventi[0].ore = ore_std
                                eventi[0].save()
                            else:
                                EventoAssenza.objects.create(giornata=presenza, causale=causale, ore=ore_std)
                            nuove_lavorate = max(0, ore_std - ore_std)
                            presenza.ore_lavorate = nuove_lavorate
                            presenza.save()
                elif campo == 'ass1_ore':
                    ore_assenza_inserita = Decimal(valore.replace(',', '.')) if valore else Decimal(0)
                    if eventi[0]:
                        eventi[0].ore = ore_assenza_inserita
                        eventi[0].save()
                        ore_ass_totali = ore_assenza_inserita
                        if eventi[1]: ore_ass_totali += eventi[1].ore
                        nuove_lavorate = max(0, ore_std - ore_ass_totali)
                        presenza.ore_lavorate = nuove_lavorate
                        presenza.save()
                elif campo == 'ass2_cod':
                    if not valore: 
                        if eventi[1]: eventi[1].delete()
                    else:
                        causale = CausaleAssenza.objects.filter(codice=valore).first()
                        if causale:
                            if eventi[1]:
                                eventi[1].causale = causale
                                eventi[1].ore = ore_std 
                                eventi[1].save()
                            else:
                                EventoAssenza.objects.create(giornata=presenza, causale=causale, ore=ore_std)
                            presenza.ore_lavorate = Decimal(0)
                            presenza.save()
                elif campo == 'ass2_ore':
                    ore = Decimal(valore.replace(',', '.')) if valore else Decimal(0)
                    if eventi[1]:
                        eventi[1].ore = ore
                        eventi[1].save()
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)}, status=500)

# ==============================================================================
# 5. SIMULAZIONE BUSTA PAGA
# ==============================================================================
@login_required
def simulazione_busta_paga_view(request, dipendente_id, anno, mese):
    dip = get_object_or_404(Dipendente, pk=dipendente_id)
    
    if not check_permessi_azienda(request.user, dip.azienda):
        raise PermissionDenied("Non hai i permessi per visualizzare questo dipendente.")

    ore_settimanali_contratto = (dip.ore_lun + dip.ore_mar + dip.ore_mer + dip.ore_gio + dip.ore_ven + dip.ore_sab + dip.ore_dom)
    ore_ccnl_fulltime = Decimal(40) 
    perc_part_time = Decimal(1.0)
    if ore_settimanali_contratto > 0 and ore_settimanali_contratto < ore_ccnl_fulltime:
        perc_part_time = ore_settimanali_contratto / ore_ccnl_fulltime

    presenze = dip.presenze.filter(data__year=anno, data__month=mese)
    ore_ord = Decimal(0); ore_ass = Decimal(0)
    ore_notturne_tot = Decimal(0); ore_straordinarie_tot = Decimal(0)
    
    num_giorni = calendar.monthrange(anno, mese)[1]
    orario_sett = [dip.ore_lun, dip.ore_mar, dip.ore_mer, dip.ore_gio, dip.ore_ven, dip.ore_sab, dip.ore_dom]
    presenze_dict = {p.data.day: p for p in presenze}
    goduto_ferie_ore = Decimal(0); goduto_permessi_ore = Decimal(0)

    for g in range(1, num_giorni + 1):
        d = date(anno, mese, g)
        p = presenze_dict.get(g)
        ore_std = orario_sett[d.weekday()] if not is_giorno_festivo(d, dip.azienda) else Decimal(0)
        
        if p:
            lavorate = p.ore_lavorate
            ore_ord += lavorate
            ore_notturne_tot += p.di_cui_notturne
            if lavorate > ore_std: ore_straordinarie_tot += (lavorate - ore_std)
            for ev in EventoAssenza.objects.filter(giornata=p):
                ore_ass += ev.ore
                cod = ev.causale.codice.upper()
                if 'F' in cod: goduto_ferie_ore += ev.ore
                elif 'R' in cod or 'P' in cod: goduto_permessi_ore += ev.ore
        else:
            ore_ord += ore_std 

    lordo_mensile_full = dip.lordo_mensile_calcolato or Decimal(0)
    lordo_mensile_riproporzionato = lordo_mensile_full * perc_part_time
    paga_oraria = lordo_mensile_full / 173 
    valore_notturno = ore_notturne_tot * paga_oraria * Decimal('0.20')
    valore_straord = ore_straordinarie_tot * paga_oraria * Decimal('1.30')
    lordo_totale = lordo_mensile_riproporzionato + valore_notturno + valore_straord
    
    aliquota_inps = Decimal('0.0919')
    trattenuta_inps = lordo_totale * aliquota_inps
    imponibile_irpef = lordo_totale - trattenuta_inps
    
    irpef_lorda = Decimal(0)
    if imponibile_irpef <= 2333: irpef_lorda = imponibile_irpef * Decimal('0.23')
    else: irpef_lorda = imponibile_irpef * Decimal('0.25')
    detrazioni = Decimal(100) * perc_part_time 
    if irpef_lorda < detrazioni: detrazioni = irpef_lorda
    
    irpef_netta = irpef_lorda - detrazioni
    netto_busta = imponibile_irpef - irpef_netta
    
    inps_ditta = lordo_totale * Decimal('0.30')
    inail = lordo_totale * Decimal('0.004')
    tfr = lordo_totale / Decimal('13.5')
    costo_azienda = lordo_totale + inps_ditta + inail + tfr

    maturato_ferie_mese = Decimal('2.166') 
    maturato_rol_mese = (Decimal('6.00') * perc_part_time)
    orario_medio_gg = ore_settimanali_contratto / 5 if ore_settimanali_contratto else 8
    goduto_ferie_gg = goduto_ferie_ore / Decimal(orario_medio_gg) if orario_medio_gg else 0
    saldo_ferie = (dip.ferie_residuo_attuale or 0) + maturato_ferie_mese - goduto_ferie_gg
    saldo_rol = (dip.permessi_residuo_attuale or 0) + maturato_rol_mese - goduto_permessi_ore

    context = {
        'dipendente': dip,
        'periodo': {'anno': anno, 'mese': mese},
        'dati': {
            'perc_part_time': round(perc_part_time * 100, 0),
            'ore_settimanali': ore_settimanali_contratto,
            'ore_lavorate': ore_ord, 'ore_assenza': ore_ass, 'ore_notturne': ore_notturne_tot,
            'ore_straordinarie': ore_straordinarie_tot, 'valore_notturno': valore_notturno, 'valore_straord': valore_straord,
            'lordo_totale': lordo_totale, 'inps_dip': trattenuta_inps, 'irpef_netta': irpef_netta,
            'netto': netto_busta, 'costo_azienda': costo_azienda,
            'ratei': {'ferie': {'prec': dip.ferie_residuo_attuale, 'mat': maturato_ferie_mese, 'god': goduto_ferie_gg, 'saldo': saldo_ferie},
                      'rol': {'prec': dip.permessi_residuo_attuale, 'mat': maturato_rol_mese, 'god': goduto_permessi_ore, 'saldo': saldo_rol}}
        }
    }
    return render(request, 'anagrafica/simulazione_busta.html', context)

# ==============================================================================
# 6. FUNZIONI DI SUPPORTO
# ==============================================================================
@login_required
def inserimento_massivo_view(request, azienda_id):
    if request.method != 'POST': return redirect('dashboard_generale')
    return redirect(request.META.get('HTTP_REFERER', '/'))

# ==============================================================================
# 7. EXPORT CSV RANOCCHI
# ==============================================================================
@login_required
def export_csv_view(request, azienda_id, anno, mese):
    azienda = get_object_or_404(Azienda, pk=azienda_id)
    
    if not check_permessi_azienda(request.user, azienda):
        raise PermissionDenied("Non hai i permessi per scaricare questi dati.")

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_NONE)
    
    writer.writerow(['Azienda', azienda.codice, 'Sede', '0000', azienda.ragione_sociale])
    writer.writerow(['Anno', str(anno), 'Mese', str(mese).zfill(2)])
    
    header_giorni = ['', '', ''] + [str(g) for g in range(1, 32)]
    writer.writerow([]) 
    writer.writerow(header_giorni)
    
    writer.writerow(['Matricola', 'Cognome e nome', 'Tipo'] + ['Ore' for _ in range(1, 32)])

    for dip in azienda.dipendenti.all():
        presenze = {p.data.day: p for p in dip.presenze.filter(data__year=anno, data__month=mese)}
        righe_dati = [[] for _ in range(13)]

        for g in range(1, 32):
            try:
                data_corr = date(anno, mese, g)
            except ValueError:
                for r in range(13): righe_dati[r].append('')
                continue

            p = presenze.get(g)
            ore_lav = ''; ore_not = ''
            
            orario_sett = [dip.ore_lun, dip.ore_mar, dip.ore_mer, dip.ore_gio, dip.ore_ven, dip.ore_sab, dip.ore_dom]
            ore_std = orario_sett[data_corr.weekday()] if not is_giorno_festivo(data_corr, azienda) else Decimal(0)

            if p:
                if p.ore_lavorate > 0: ore_lav = str(p.ore_lavorate).replace('.', ',')
                if p.di_cui_notturne > 0: ore_not = str(p.di_cui_notturne).replace('.', ',')
            else:
                if ore_std > 0: ore_lav = str(ore_std).replace('.', ',')

            righe_dati[0].append(ore_lav) 
            righe_dati[1].append(ore_not)  

            eventi = []
            if p:
                eventi = list(EventoAssenza.objects.filter(giornata=p).order_by('id'))
            
            current_slot_idx = 2 
            for i in range(5):
                causale_val = ''; ore_val = ''
                if i < len(eventi):
                    causale_val = eventi[i].causale.codice
                    ore_val = str(eventi[i].ore).replace('.', ',')
                righe_dati[current_slot_idx].append(causale_val)    
                righe_dati[current_slot_idx + 1].append(ore_val)     
                current_slot_idx += 2 

            righe_dati[12].append('')

        cf = getattr(dip, 'codice_fiscale', getattr(dip, 'cf', ''))
        nome_completo = f"{dip.cognome_nome} - {cf}" if cf else dip.cognome_nome

        writer.writerow([dip.codice, nome_completo, 'Ore lavorate'] + righe_dati[0])
        writer.writerow(['', '', 'di cui notturne'] + righe_dati[1])
        
        idx_causale = 1
        for r in range(2, 12, 2):
            writer.writerow(['', '', f'Causale {idx_causale}'] + righe_dati[r])
            writer.writerow(['', '', 'Ore'] + righe_dati[r+1])
            idx_causale += 1
            
        writer.writerow(['', '', 'Turno'] + righe_dati[12])

    response = HttpResponse(output.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="PRE_{azienda.codice}_{anno}_{mese}.csv"'
    return response

# ==============================================================================
# 8. REPORT COSTI AZIENDALI
# ==============================================================================
@login_required
def report_costi_azienda_view(request, azienda_id, anno, mese):
    azienda = get_object_or_404(Azienda, pk=azienda_id)
    
    if not check_permessi_azienda(request.user, azienda):
        raise PermissionDenied("Non hai i permessi per visualizzare questo report.")

    dipendenti = azienda.dipendenti.all().order_by('cognome_nome')
    nomi_mesi = {1: 'Gennaio', 2: 'Febbraio', 3: 'Marzo', 4: 'Aprile', 5: 'Maggio', 6: 'Giugno', 
                 7: 'Luglio', 8: 'Agosto', 9: 'Settembre', 10: 'Ottobre', 11: 'Novembre', 12: 'Dicembre'}
    
    dati_report = []
    totale_azienda_mensile = Decimal(0)
    totale_debito_ratei = Decimal(0)

    for dip in dipendenti:
        ore_settimanali = (dip.ore_lun + dip.ore_mar + dip.ore_mer + dip.ore_gio + dip.ore_ven + dip.ore_sab + dip.ore_dom)
        perc_part_time = Decimal(1.0)
        if ore_settimanali > 0 and ore_settimanali < 40:
            perc_part_time = ore_settimanali / Decimal(40)

        lordo_full = dip.lordo_mensile_calcolato or Decimal(0)
        lordo_pt = lordo_full * perc_part_time
        inps_ditta = lordo_pt * Decimal('0.30')
        inail = lordo_pt * Decimal('0.004')
        tfr = lordo_pt / Decimal('13.5')
        
        costo_mensile = lordo_pt + inps_ditta + inail + tfr
        costo_settimanale = costo_mensile / Decimal('4.33')
        
        ore_mese = Decimal('173') * perc_part_time
        costo_orario = costo_mensile / ore_mese if ore_mese > 0 else Decimal(0)

        orario_medio_gg = ore_settimanali / 5 if ore_settimanali else 8
        costo_giornaliero = costo_orario * Decimal(orario_medio_gg)

        ferie_res = dip.ferie_residuo_attuale or Decimal(0)
        rol_res = dip.permessi_residuo_attuale or Decimal(0)
        
        debito_ferie = ferie_res * costo_giornaliero
        debito_rol = rol_res * costo_orario
        debito_totale = debito_ferie + debito_rol

        totale_azienda_mensile += costo_mensile
        totale_debito_ratei += debito_totale

        dati_report.append({
            'dipendente': dip,
            'ore_settimanali': ore_settimanali,
            'perc_pt': round(perc_part_time * 100, 1),
            'costo_mensile': costo_mensile,
            'costo_settimanale': costo_settimanale,
            'costo_orario': costo_orario,
            'ferie_res': ferie_res,
            'rol_res': rol_res,
            'debito_totale': debito_totale,
            'incidenza': 0  
        })

    for r in dati_report:
        if totale_azienda_mensile > 0:
            r['incidenza'] = (r['costo_mensile'] / totale_azienda_mensile) * 100

    context = {
        'azienda': azienda,
        'periodo': f"{nomi_mesi[int(mese)]} {anno}",
        'dati': dati_report,
        'totali': {
            'mensile': totale_azienda_mensile,
            'settimanale': totale_azienda_mensile / Decimal('4.33'),
            'debito': totale_debito_ratei
        }
    }
    
    return render(request, 'anagrafica/report_costi.html', context)

# ==============================================================================
# 9. API AZZERAMENTO PRESENZE (Ritorna allo standard contrattuale)
# ==============================================================================
@login_required
def azzera_presenze_json(request):
    if request.method != 'POST': return JsonResponse({'status': 'error'}, status=405)
    
    try:
        data = json.loads(request.body)
        dip_id = data.get('dip_id')
        anno = int(data.get('anno'))
        mese = int(data.get('mese'))
        azienda_id = int(data.get('azienda_id'))

        # Controllo sicurezza sull'azienda in questione
        azienda = Azienda.objects.get(pk=azienda_id)
        if not check_permessi_azienda(request.user, azienda):
            return JsonResponse({'status': 'error', 'msg': 'Permesso negato.'}, status=403)

        presenze = PresenzaGiornaliera.objects.filter(data__year=anno, data__month=mese)

        if dip_id != 'all':
            presenze = presenze.filter(dipendente_id=dip_id)
        else:
            presenze = presenze.filter(dipendente__azienda_id=azienda_id)

        presenze.delete()

        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)}, status=500)