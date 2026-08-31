import os
import re
import sys
from datetime import datetime
from collections import Counter

MESI_IT = {
    'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4, 'maggio': 5, 'giugno': 6,
    'luglio': 7, 'agosto': 8, 'settembre': 9, 'ottobre': 10, 'novembre': 11, 'dicembre': 12
}
MESI_ABBR_IT = {
    1: 'gen', 2: 'feb', 3: 'mar', 4: 'apr', 5: 'mag', 6: 'giu',
    7: 'lug', 8: 'ago', 9: 'set', 10: 'ott', 11: 'nov', 12: 'dic'
}
MESI_NOME_IT = {v: k.capitalize() for k, v in MESI_IT.items()}

COLORI_DOT = [
    '--dot-fotografia', '--dot-video', '--dot-musica',
    '--dot-cinema', '--dot-gaming', '--dot-note'
]

# Note "speciali" con contenuti che il formato testo semplice di pensieri.txt
# non può rappresentare (più foto in un carosello, layout particolare...).
# Vanno aggiunte qui a mano (basta chiedere a Claude), ma da qui in poi il
# resto del sistema le inserisce da solo nella cartella del mese giusto,
# nella posizione cronologica corretta insieme a tutte le altre.
NOTE_MANUALI = [
    {
        'data_obj': datetime(2026, 8, 17),
        'html': (
            '              <details class="note-item">\n'
            '                <summary class="note-date" data-i18n="note_sardinia_date">+ Dal 17 al 21 agosto 2026</summary>\n'
            '                <p data-i18n="note_sardinia_p1">Una settimana ad Alghero che si potrebbe riassumere in: mare cristallino, escursioni in barca, aperitivi al tramonto e un\'Odissea finale in aeroporto.</p>\n'
            '                <p data-i18n="note_sardinia_p2">Il viaggio è iniziato sotto i migliori auspici: l\'andata in volo è volata via in modo perfetto, liscio e puntualissimo. Una volta atterrati, ci siamo tuffati nei ritmi rilassati della Sardegna. Abbiamo esplorato la costa da un\'altra prospettiva grazie a un giro in barca indimenticabile, fermandoci sotto le imponenti scogliere calcaree del promontorio per fare snorkeling in calette trasparenti insieme ai pesci.</p>\n'
            '                <p data-i18n="note_sardinia_p3">Le giornate si sono divise tra avventure in acqua, nuotate in apnea e passeggiate serali per le vie del centro storico di Alghero, fino ad attendere il tramonto dorato sulla spiaggia con la vista del promontorio sullo sfondo.</p>\n'
            '\n'
            '                <div class="note-carousel" id="sardiniaCarousel">\n'
            '                  <button class="carousel-nav prev" type="button" onclick="moveCarousel(this, -1)">&#10094;</button>\n'
            '                  <div class="carousel-track">\n'
            '                    <div class="carousel-item active" onclick="openMediaZoom(this)">\n'
            '                      <img src="foto/sar1.jpg" alt="Dek, Fava ed Io">\n'
            '                    </div>\n'
            '                    <div class="carousel-item" onclick="openMediaZoom(this)">\n'
            '                      <img src="foto/sar2.jpg" alt="ichnusa con il mare piu bello d\'italia">\n'
            '                    </div>\n'
            '                    <div class="carousel-item" onclick="openMediaZoom(this)">\n'
            '                      <img src="foto/sar3.jpg" alt="Tramonto Alghero">\n'
            '                    </div>\n'
            '                  </div>\n'
            '                  <button class="carousel-nav next" type="button" onclick="moveCarousel(this, 1)">&#10095;</button>\n'
            '                </div>\n'
            '\n'
            '                <p data-i18n="note_sardinia_p4">L\'unico vero momento "avventuroso" (e decisamente meno piacevole) è arrivato proprio alla fine: al momento di tornare a casa, il volo di rientro ha deciso di testare la nostra pazienza accumulate ben 12 ore di ritardo. Una maratona in aeroporto che ha messo a dura prova il nostro relax, ma che non è riuscita a scalzare il ricordo dei giorni fantastici passati in barca tra amici.</p>\n'
            '              </details>'
        ),
    },
]


def slugify(testo):
    """Crea una chiave sicura (per data-i18n) a partire da un testo qualsiasi."""
    testo = testo.lower()
    sostituzioni = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', ' ': '_'}
    for a, b in sostituzioni.items():
        testo = testo.replace(a, b)
    testo = re.sub(r'[^a-z0-9_]', '', testo)
    return testo[:40] or 'voce'


def parse_data_italiana(testo_data):
    """Es: '25 agosto 2026' -> datetime(2026, 8, 25).
    Supporta anche intervalli tipo 'Dal 17 al 21 agosto 2026' (usa il giorno finale)."""
    testo = testo_data.strip().lower()
    parte_utile = testo.split(' al ')[-1] if ' al ' in testo else testo

    match = re.search(r'(\d{1,2})\s+([a-zàèéìòù]+)\s+(\d{4})', parte_utile)
    if not match:
        raise ValueError(f"Non riesco a interpretare la data: '{testo_data}'")

    giorno, mese_nome, anno = match.group(1), match.group(2), match.group(3)
    mese = MESI_IT.get(mese_nome)
    if not mese:
        raise ValueError(f"Mese non riconosciuto: '{mese_nome}' (in '{testo_data}')")

    return datetime(int(anno), mese, int(giorno))


def escapa_html(testo):
    """Escape minimo per inserire testo utente dentro attributi/HTML in sicurezza."""
    return (testo.replace('&', '&amp;')
                 .replace('<', '&lt;')
                 .replace('>', '&gt;'))


def parse_pensieri_txt(percorso='pensieri.txt'):
    with open(percorso, 'r', encoding='utf-8') as f:
        contenuto = f.read()

    blocchi = [b.strip() for b in contenuto.split('---') if b.strip()]
    voci = []

    for numero_blocco, blocco in enumerate(blocchi, start=1):
        campi = {}
        chiave_corrente = None

        for riga in blocco.splitlines():
            m = re.match(r'^(DATA|PENSIERO|TIMELINE|TAG|FOTO)\s*:\s*(.*)$', riga.strip(), re.IGNORECASE)
            if m:
                chiave_corrente = m.group(1).upper()
                campi[chiave_corrente] = m.group(2).strip()
            elif chiave_corrente and riga.strip():
                # riga di continuazione (es. un PENSIERO scritto su più righe)
                campi[chiave_corrente] += ' ' + riga.strip()

        if 'DATA' not in campi:
            print(f"⚠️  Blocco {numero_blocco} ignorato: manca il campo DATA.")
            continue
        if 'PENSIERO' not in campi and 'TIMELINE' not in campi:
            print(f"⚠️  Blocco {numero_blocco} ignorato: serve almeno PENSIERO o TIMELINE.")
            continue

        try:
            data_obj = parse_data_italiana(campi['DATA'])
        except ValueError as e:
            print(f"⚠️  Blocco {numero_blocco} ignorato: {e}")
            continue

        voci.append({
            'data_testo': campi['DATA'],
            'data_obj': data_obj,
            'pensiero': campi.get('PENSIERO'),
            'timeline': campi.get('TIMELINE'),
            'tag': campi.get('TAG', 'Update'),
            'foto': campi.get('FOTO'),
        })

    voci.sort(key=lambda v: v['data_obj'])
    return voci


def genera_html_foto(voce, chiave_slug):
    """Se la voce ha un campo FOTO, genera l'HTML della foto:
    - una sola immagine -> foto singola cliccabile, senza freccine
    - più immagini (separate da virgola) -> carosello con freccine avanti/indietro
    Ritorna stringa vuota se non ci sono foto."""
    foto_raw = voce.get('foto')
    if not foto_raw:
        return ''

    nomi = [n.strip() for n in foto_raw.split(',') if n.strip()]
    if not nomi:
        return ''

    if len(nomi) == 1:
        return (
            f'\n                <div class="note-photo-single" onclick="openMediaZoom(this)">\n'
            f'                  <img src="foto/{escapa_html(nomi[0])}" alt="Foto del {escapa_html(voce["data_testo"])}">\n'
            f'                </div>\n'
        )

    slide_html = []
    for i, nome in enumerate(nomi):
        attivo = ' active' if i == 0 else ''
        slide_html.append(
            f'                    <div class="carousel-item{attivo}" onclick="openMediaZoom(this)">\n'
            f'                      <img src="foto/{escapa_html(nome)}" alt="Foto {i + 1} del {escapa_html(voce["data_testo"])}">\n'
            f'                    </div>'
        )

    return (
        f'\n                <div class="note-carousel" id="carousel_{chiave_slug}">\n'
        f'                  <button class="carousel-nav prev" type="button" onclick="moveCarousel(this, -1)">&#10094;</button>\n'
        f'                  <div class="carousel-track">\n'
        + '\n'.join(slide_html) +
        f'\n                  </div>\n'
        f'                  <button class="carousel-nav next" type="button" onclick="moveCarousel(this, 1)">&#10095;</button>\n'
        f'                </div>\n'
    )


def genera_html_pensieri(voci):
    """Genera i <details class="year-folder"> (2026, 2027...) con dentro,
    per ognuno, i <details class="month-folder"> (Agosto, Settembre...)
    con le note vere e proprie. Raggruppa sia le note testuali da
    pensieri.txt sia quelle manuali con foto da NOTE_MANUALI, ordinate
    per data. Tutte le cartelle restano SEMPRE chiuse di default."""
    voci_con_pensiero = [v for v in voci if v.get('pensiero')]

    elementi = [{'data_obj': v['data_obj'], 'tipo': 'auto', 'dato': v} for v in voci_con_pensiero]
    elementi += [{'data_obj': nm['data_obj'], 'tipo': 'manuale', 'dato': nm} for nm in NOTE_MANUALI]

    if not elementi:
        return '          <!-- nessuna nota trovata -->'

    elementi.sort(key=lambda e: e['data_obj'])

    # Il bollino "nuovo" va solo sull'ultima nota testuale (quelle manuali
    # sono di solito ricordi passati, non l'ultimo aggiornamento del sito)
    date_auto = [v['data_obj'] for v in voci_con_pensiero]
    ultima_data_auto = max(date_auto) if date_auto else None

    # Raggruppo prima per anno, poi per mese dentro ogni anno
    anni = {}
    for e in elementi:
        anno = e['data_obj'].year
        mese = e['data_obj'].month
        anni.setdefault(anno, {}).setdefault(mese, []).append(e)

    blocchi_anno = []

    for anno in sorted(anni.keys()):
        mesi_anno = anni[anno]
        blocchi_mese = []
        contatore_slug = {}  # condiviso su tutto l'anno, per sicurezza sulle chiavi uniche

        for mese in sorted(mesi_anno.keys()):
            elementi_mese = mesi_anno[mese]
            mese_nome = MESI_NOME_IT[mese]

            righe_note = []
            for e in elementi_mese:
                if e['tipo'] == 'manuale':
                    righe_note.append(e['dato']['html'])
                    continue

                v = e['dato']
                slug_base = slugify(f"{v['data_obj'].day}{mese_nome}{anno}")
                contatore_slug[slug_base] = contatore_slug.get(slug_base, 0) + 1
                slug = slug_base if contatore_slug[slug_base] == 1 else f"{slug_base}_{contatore_slug[slug_base]}"
                chiave_date = f"note_{slug}_date"
                chiave_testo = f"note_{slug}_text"
                e_fresca = ultima_data_auto is not None and v['data_obj'] == ultima_data_auto
                badge = ' <span class="fresh"></span>' if e_fresca else ''
                testo_pensiero = escapa_html(v['pensiero'])
                html_foto = genera_html_foto(v, slug)

                righe_note.append(
                    f'                <details class="note-item">\n'
                    f'                  <summary class="note-date" data-i18n="{chiave_date}">+ {v["data_testo"]}{badge}</summary>\n'
                    f'                  <p data-i18n="{chiave_testo}">{testo_pensiero}</p>'
                    f'{html_foto}'
                    f'\n                </details>'
                )

            blocchi_mese.append(
                f'            <details class="month-folder">\n'
                f'              <summary class="month-header">📁 {mese_nome}</summary>\n'
                f'              <div class="month-body">\n'
                + '\n\n'.join(righe_note) +
                f'\n              </div>\n'
                f'            </details>'
            )

        blocchi_anno.append(
            f'          <details class="year-folder">\n'
            f'            <summary class="year-header">📅 {anno}</summary>\n'
            f'            <div class="year-body">\n'
            + '\n\n'.join(blocchi_mese) +
            f'\n            </div>\n'
            f'          </details>'
        )

    return '\n\n'.join(blocchi_anno)


def genera_html_timeline(voci, mostra_sempre=1):
    """Genera tutte le righe della timeline 'Attività recente'.
    Solo le voci che hanno un TIMELINE. Le più recenti (ultime
    'mostra_sempre') restano sempre visibili, quelle più vecchie vengono
    nascoste dietro il bottone 'Carica altro' — così la lista non diventa
    un elenco lunghissimo sempre tutto visibile."""
    voci_timeline = [v for v in voci if v.get('timeline')]
    if not voci_timeline:
        return '    <!-- nessuna voce per la timeline trovata in pensieri.txt -->'

    n_totali = len(voci_timeline)
    righe = []
    contatore_slug = {}

    for i, v in enumerate(voci_timeline):
        colore = COLORI_DOT[i % len(COLORI_DOT)]
        data_breve = f"{v['data_obj'].day} {MESI_ABBR_IT[v['data_obj'].month]} {v['data_obj'].year}"
        slug_base = slugify(f"{v['data_obj'].day}{v['data_obj'].month}{v['data_obj'].year}tl")
        contatore_slug[slug_base] = contatore_slug.get(slug_base, 0) + 1
        slug = slug_base if contatore_slug[slug_base] == 1 else f"{slug_base}_{contatore_slug[slug_base]}"
        chiave_testo = f"log_{slug}"
        testo_timeline = escapa_html(v['timeline'])
        tag = escapa_html(v['tag'])

        e_vecchia = i < (n_totali - mostra_sempre)
        e_ultima = (i == n_totali - 1)  # la voce più recente in assoluto

        classe = 'entry extra-entry' if e_vecchia else 'entry'
        if e_ultima:
            classe += ' newest'
        stile = ' style="display:none;"' if e_vecchia else ''
        badge = ' <span class="fresh"></span>' if e_ultima else ''

        righe.append(
            f'    <div class="{classe}"{stile}>\n'
            f'      <div class="dot" style="background: var({colore});"></div>\n'
            f'      <div class="entry-body">\n'
            f'        <span class="entry-date">{data_breve}</span>{badge}\n'
            f'        <span class="entry-text" data-i18n="{chiave_testo}">{testo_timeline}</span>\n'
            f'        <span class="entry-tag">{tag}</span>\n'
            f'      </div>\n'
            f'    </div>'
        )

    return '\n\n'.join(righe)


def genera_html_loadmore(voci, mostra_sempre=1):
    """Genera il bottone 'Carica altro', ma solo se ci sono davvero voci
    nascoste da rivelare. Va tenuto FUORI dal div della timeline (con il
    suo marcatore separato), altrimenti la lineetta verticale della
    timeline si allunga fino a coprire anche lo spazio del bottone."""
    voci_timeline = [v for v in voci if v.get('timeline')]
    n_totali = len(voci_timeline)

    if n_totali <= mostra_sempre:
        return '  <!-- nessuna voce nascosta, bottone non necessario -->'

    return '  <button class="load-more" id="loadMoreBtn" data-i18n="load_more">Carica altro</button>'


def sostituisci_tra_marcatori(html, nome_marcatore, nuovo_contenuto):
    pattern = rf'(<!-- {nome_marcatore}:START -->)([\s\S]*?)(<!-- {nome_marcatore}:END -->)'
    if not re.search(pattern, html):
        print(f"❌ Marcatori '{nome_marcatore}:START/END' non trovati in index.html!")
        sys.exit(1)
    sostituzione = f"\\1\n{nuovo_contenuto}\n    \\3"
    # usiamo una funzione invece di una stringa di sostituzione diretta per
    # evitare problemi con eventuali backslash/simboli speciali nel testo
    return re.sub(pattern, lambda m: f"{m.group(1)}\n{nuovo_contenuto}\n    {m.group(3)}", html, count=1)


# ============ RECAP: "il mio archivio in numeri" ============
# Analizza tutti i Pensieri scritti finora e genera statistiche + un
# grafico dell'andamento dell'umore, calcolati automaticamente ogni volta
# che pensieri.txt cambia. L'umore è una stima giocosa (parole ed emoji
# chiave), non un'analisi seria: va presa con lo spirito giusto.

STOPWORDS_IT = {
    'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una', 'di', 'a', 'da', 'in', 'con', 'su',
    'per', 'tra', 'fra', 'e', 'o', 'ma', 'se', 'che', 'chi', 'cui', 'non', 'mi', 'ti', 'si', 'ci',
    'vi', 'ho', 'hai', 'ha', 'abbiamo', 'avete', 'hanno', 'sono', 'sei', 'è', 'siamo', 'siete',
    'del', 'della', 'dei', 'delle', 'dello', 'degli', 'al', 'allo', 'alla', 'ai', 'agli', 'alle',
    'come', 'più', 'anche', 'ancora', 'già', 'poi', 'quindi', 'perché', 'però', 'così', 'tutto',
    'tutti', 'tutta', 'tutte', 'questo', 'questa', 'questi', 'queste', 'quello', 'quella',
    'quelli', 'quelle', 'mio', 'mia', 'miei', 'mie', 'suo', 'sua', 'loro', 'nostro', 'nostra',
    'me', 'te', 'lui', 'lei', 'noi', 'voi', 'essere', 'stato', 'stata', 'stati', 'avevo', 'era',
    'erano', 'sarà', 'saranno', 'ogni', 'qualche', 'molto', 'molti', 'molta', 'poco', 'pochi',
    'due', 'tre', 'giorno', 'oggi', 'poi', 'quando', 'dove', 'sempre', 'quasi', 'senza', 'fino',
}

PAROLE_POSITIVE = {
    'felice', 'bello', 'bella', 'belli', 'belle', 'vittoria', 'grande', 'piace', 'piaciuto',
    'piacevole', 'buon', 'buono', 'buona', 'ottimo', 'bene', 'riposo', 'relax', 'goduriosa',
    'curato', 'fantastico', 'fantastici', 'indimenticabile', 'divertente', 'soddisfatto',
    'scoperta', 'solida', 'solido', 'vinto', 'riuscito', 'riusciti', 'successo', 'orgoglioso',
    'contento', 'bellissima', 'perfetto', 'perfetta',
}
PAROLE_NEGATIVE = {
    'traumatico', 'stanco', 'stanca', 'frustrante', 'difficile', 'problema', 'problemi', 'rompi',
    'rotto', 'brutto', 'brutta', 'uggiosa', 'stress', 'stressante', 'odissea', 'ritardo',
    'faticoso', 'estenuante', 'deluso', 'deludermi', 'traffico', 'infiniti',
}
EMOJI_POSITIVI = ['😄', '😁', '🤩', '✅', '😊', '😍', '🥳', '🎉', '😎', '💪']
EMOJI_NEGATIVI = ['😱', '😢', '😭', '😡', '🙁', '😔', '💥']

GIORNI_IT = {
    'Monday': 'lunedì', 'Tuesday': 'martedì', 'Wednesday': 'mercoledì', 'Thursday': 'giovedì',
    'Friday': 'venerdì', 'Saturday': 'sabato', 'Sunday': 'domenica',
}


def _pulisci_parole(testo):
    testo = testo.lower()
    parole = re.findall(r"[a-zàèéìòùç]+", testo)
    return [p for p in parole if len(p) > 2 and p not in STOPWORDS_IT]


def _calcola_umore(testo):
    testo_lower = testo.lower()
    punteggio = 0
    for parola in PAROLE_POSITIVE:
        if parola in testo_lower:
            punteggio += 1
    for parola in PAROLE_NEGATIVE:
        if parola in testo_lower:
            punteggio -= 1
    for emo in EMOJI_POSITIVI:
        punteggio += testo.count(emo)
    for emo in EMOJI_NEGATIVI:
        punteggio -= testo.count(emo)
    return punteggio


def genera_recap(voci):
    """Genera la sezione 'Il mio archivio in numeri': statistiche e un
    grafico SVG dell'umore, ricalcolati ogni volta da zero sui Pensieri
    presenti in pensieri.txt."""
    voci_con_pensiero = [v for v in voci if v.get('pensiero')]
    if len(voci_con_pensiero) < 2:
        return '          <!-- Recap non generato: servono almeno 2 pensieri con testo -->'

    voci_con_pensiero = sorted(voci_con_pensiero, key=lambda v: v['data_obj'])

    tutte_parole = []
    punteggi_umore = []
    lunghezze = []
    tutti_emoji = []
    contatore_emoji_regex = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF]")

    for v in voci_con_pensiero:
        testo = v['pensiero']
        tutte_parole.extend(_pulisci_parole(testo))
        lunghezze.append(len(testo.split()))
        punteggi_umore.append(_calcola_umore(testo))
        tutti_emoji.extend(contatore_emoji_regex.findall(testo))

    n_pensieri = len(voci_con_pensiero)
    totale_parole = sum(lunghezze)
    media_parole = round(totale_parole / n_pensieri) if n_pensieri else 0

    contatore_parole = Counter(tutte_parole)
    parola_top = contatore_parole.most_common(1)[0][0] if contatore_parole else '—'

    contatore_emoji = Counter(tutti_emoji)
    emoji_top = contatore_emoji.most_common(1)[0][0] if contatore_emoji else '—'

    contatore_giorni = Counter(v['data_obj'].strftime('%A') for v in voci_con_pensiero)
    giorno_top_eng = contatore_giorni.most_common(1)[0][0] if contatore_giorni else None
    giorno_top_it = GIORNI_IT.get(giorno_top_eng, '—')
    chiave_giorno = f"recap_day_{giorno_top_eng.lower()}" if giorno_top_eng else None

    # --- Grafico SVG dell'andamento dell'umore, usa le variabili CSS del sito ---
    larghezza = 600
    altezza = 130
    margine = 16
    n = len(punteggi_umore)
    max_assoluto = max(1, max(abs(p) for p in punteggi_umore))

    punti = []
    for i, punteggio in enumerate(punteggi_umore):
        x = margine + (i / max(1, n - 1)) * (larghezza - 2 * margine)
        y = (altezza / 2) - (punteggio / max_assoluto) * (altezza / 2 - margine)
        punti.append((round(x, 1), round(y, 1)))

    punti_linea = ' '.join(f"{x},{y}" for x, y in punti)
    cerchi = '\n'.join(
        f'                  <circle cx="{x}" cy="{y}" r="3.5" fill="var(--forest)"></circle>'
        for x, y in punti
    )

    html_grafico = (
        f'              <svg viewBox="0 0 {larghezza} {altezza}" class="recap-mood-chart" preserveAspectRatio="none">\n'
        f'                <line x1="{margine}" y1="{altezza / 2}" x2="{larghezza - margine}" y2="{altezza / 2}" stroke="var(--line)" stroke-width="1" stroke-dasharray="4 4"></line>\n'
        f'                <polyline points="{punti_linea}" fill="none" stroke="var(--forest)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"></polyline>\n'
        f'{cerchi}\n'
        f'              </svg>'
    )

    giorno_html = (
        f'<span data-i18n="{chiave_giorno}">{giorno_top_it}</span>' if chiave_giorno else giorno_top_it
    )

    html = (
        f'          <div class="recap-grid">\n'
        f'            <div class="recap-stat">\n'
        f'              <div class="recap-num">{n_pensieri}</div>\n'
        f'              <div class="recap-label" data-i18n="recap_label_pensieri">Pensieri scritti</div>\n'
        f'            </div>\n'
        f'            <div class="recap-stat">\n'
        f'              <div class="recap-num">{totale_parole}</div>\n'
        f'              <div class="recap-label" data-i18n="recap_label_parole">Parole totali</div>\n'
        f'            </div>\n'
        f'            <div class="recap-stat">\n'
        f'              <div class="recap-num">{media_parole}</div>\n'
        f'              <div class="recap-label" data-i18n="recap_label_media">Parole a nota</div>\n'
        f'            </div>\n'
        f'            <div class="recap-stat">\n'
        f'              <div class="recap-num recap-num-small">{giorno_html}</div>\n'
        f'              <div class="recap-label" data-i18n="recap_label_giorno">Giorno più attivo</div>\n'
        f'            </div>\n'
        f'            <div class="recap-stat">\n'
        f'              <div class="recap-num recap-num-small">"{parola_top}"</div>\n'
        f'              <div class="recap-label" data-i18n="recap_label_parola">Parola più usata</div>\n'
        f'            </div>\n'
        f'            <div class="recap-stat">\n'
        f'              <div class="recap-num">{emoji_top}</div>\n'
        f'              <div class="recap-label" data-i18n="recap_label_emoji">Emoji preferita</div>\n'
        f'            </div>\n'
        f'          </div>\n'
        f'\n'
        f'          <div class="recap-mood-box">\n'
        f'            <div class="recap-mood-title" data-i18n="recap_mood_title">Andamento dell\'umore</div>\n'
        f'{html_grafico}\n'
        f'          </div>'
    )

    return html


def main():
    voci = parse_pensieri_txt()
    if not voci:
        print("Nessuna voce valida trovata in pensieri.txt: niente da generare.")
        return

    with open('index.html', 'r', encoding='utf-8') as f:
        html = f.read()

    html_pensieri = genera_html_pensieri(voci)
    html_timeline = genera_html_timeline(voci)
    html_loadmore = genera_html_loadmore(voci)
    html_recap = genera_recap(voci)
    html = sostituisci_tra_marcatori(html, 'AUTO-PENSIERI', html_pensieri)
    html = sostituisci_tra_marcatori(html, 'AUTO-TIMELINE', html_timeline)
    html = sostituisci_tra_marcatori(html, 'AUTO-LOADMORE', html_loadmore)
    html = sostituisci_tra_marcatori(html, 'AUTO-RECAP', html_recap)

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)

    n_pensieri = sum(1 for v in voci if v.get('pensiero'))
    n_timeline = sum(1 for v in voci if v.get('timeline'))
    print(f"✅ Generate {n_pensieri} note in 'Pensieri' e {n_timeline} voci in 'Attività recente'. Recap aggiornato.")


if __name__ == '__main__':
    main()
