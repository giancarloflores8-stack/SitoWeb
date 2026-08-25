import re
import sys
import time
from bs4 import BeautifulSoup, NavigableString, Tag
from deep_translator import GoogleTranslator, MyMemoryTranslator

MAX_RETRY = 4
PAUSA_TRA_CHIAMATE = 1.2  # secondi, per non farsi bloccare
MYMEMORY_MAX_CHARS = 480  # margine di sicurezza sotto il limite di ~500 di MyMemory


def _traduci_con_mymemory(testo):
    """MyMemory ha un limite di ~500 caratteri per richiesta: se il testo è
    più lungo (es. i paragrafi lunghi del diario) lo spezziamo per frasi e
    ricomponiamo il risultato."""
    if len(testo) <= MYMEMORY_MAX_CHARS:
        return MyMemoryTranslator(source='it', target='en').translate(testo)

    frasi = re.split(r'(?<=[.!?])\s+', testo)
    pezzi_tradotti = []
    blocco = ''
    for frase in frasi:
        if blocco and len(blocco) + len(frase) + 1 > MYMEMORY_MAX_CHARS:
            pezzi_tradotti.append(MyMemoryTranslator(source='it', target='en').translate(blocco))
            time.sleep(PAUSA_TRA_CHIAMATE)
            blocco = frase
        else:
            blocco = (blocco + ' ' + frase).strip()
    if blocco:
        pezzi_tradotti.append(MyMemoryTranslator(source='it', target='en').translate(blocco))

    return ' '.join(p for p in pezzi_tradotti if p)


def traduci_testo(testo):
    """Traduce con due traduttori in cascata:
    1) Google Translate (di solito la qualità migliore, ma sui server di
       GitHub Actions viene spesso bloccato perché lo scraping non ufficiale
       viene riconosciuto come traffico automatico)
    2) MyMemory come ripiego automatico: è una vera API pensata per essere
       chiamata in modo automatico, quindi molto più affidabile da una CI.

    Ritorna None solo se ENTRAMBI falliscono (mai il testo italiano
    spacciato per inglese)."""
    if not testo or not testo.strip():
        return testo

    testo = testo.strip()

    # 1) Google Translate, tentativo rapido (se è bloccato lo è per l'intera
    # sessione, insistere a lungo qui è solo tempo perso)
    for tentativo in range(1, 3):
        try:
            risultato = GoogleTranslator(source='it', target='en').translate(testo)
            time.sleep(PAUSA_TRA_CHIAMATE)
            if risultato and risultato.strip():
                return risultato
            raise ValueError("Risposta vuota da Google Translate")
        except Exception as e:
            print(f"⚠️ Google, tentativo {tentativo}/2 fallito ({e}).")
            time.sleep(2 ** tentativo)

    # 2) MyMemory come traduttore di riserva
    print("↪️  Google non risponde, provo con MyMemory come traduttore di riserva...")
    for tentativo in range(1, MAX_RETRY + 1):
        try:
            risultato = _traduci_con_mymemory(testo)
            time.sleep(PAUSA_TRA_CHIAMATE)
            if risultato and risultato.strip():
                return risultato
            raise ValueError("Risposta vuota da MyMemory")
        except Exception as e:
            attesa = 2 ** tentativo
            print(f"⚠️ MyMemory, tentativo {tentativo}/{MAX_RETRY} fallito ({e}). Riprovo tra {attesa}s...")
            time.sleep(attesa)

    return None  # falliti entrambi i traduttori dopo tutti i tentativi


def estrai_html_interno(tag):
    """Ritorna l'HTML *dentro* al tag così com'è (testo + eventuali tag
    annidati tipo <small> o <span>), invece di prendere solo il primo nodo
    di testo."""
    return ''.join(str(c) for c in tag.contents).strip()


def formatta_attributi(attrs):
    """BeautifulSoup interpreta alcuni attributi (es. class) come liste,
    non stringhe. Senza questa funzione si otterrebbe class="['fresh']"
    invece di class="fresh"."""
    pezzi = []
    for chiave, valore in attrs.items():
        if isinstance(valore, list):
            valore = ' '.join(valore)
        pezzi.append(f' {chiave}="{valore}"')
    return ''.join(pezzi)


def traduci_contenuto(tag):
    """Traduce il testo dentro un tag preservando STRUTTURALMENTE eventuali
    tag figli (es. <small>Bio</small>, <span class="fresh"></span>):
    - i nodi di puro testo vengono tradotti
    - i tag annidati vengono ricreati identici (stesso nome, stessi attributi),
      traducendo solo il testo al loro interno (se presente; se sono vuoti,
      tipo <span class="fresh"></span>, restano vuoti)

    Gestisce un livello di annidamento, che è quanto usato in questo sito.

    Ritorna (html_tradotto, c'è_stato_un_fallimento).
    """
    pezzi = []
    fallimento = False

    for figlio in tag.contents:
        if isinstance(figlio, NavigableString):
            testo = str(figlio)
            testo_pulito = testo.strip()
            if not testo_pulito:
                pezzi.append(testo)
                continue
            # Preservo eventuali spazi prima/dopo (es. lo spazio tra il testo
            # e un tag successivo come <span>), persi con lo strip completo.
            spazio_prima = testo[:len(testo) - len(testo.lstrip())]
            spazio_dopo = testo[len(testo.rstrip()):]
            tradotto = traduci_testo(testo_pulito)
            if tradotto is None:
                fallimento = True
                pezzi.append(spazio_prima + testo_pulito + spazio_dopo)
            else:
                pezzi.append(spazio_prima + tradotto + spazio_dopo)

        elif isinstance(figlio, Tag):
            testo_interno = figlio.get_text().strip()
            if testo_interno:
                tradotto = traduci_testo(testo_interno)
                if tradotto is None:
                    fallimento = True
                    tradotto = testo_interno
            else:
                tradotto = ''  # tag vuoto tipo <span class="fresh"></span>: resta vuoto

            attrs = formatta_attributi(figlio.attrs)
            pezzi.append(f'<{figlio.name}{attrs}>{tradotto}</{figlio.name}>')

        else:
            pezzi.append(str(figlio))

    return ''.join(pezzi), fallimento


def estrai_dizionario_esistente(testo_html, lingua):
    """Legge quello che è già scritto in index.html per 'it' o 'en',
    così da non ritradurre da zero ogni volta e non perdere correzioni manuali."""
    pattern = rf'{lingua}:\s*\{{([\s\S]*?)\n\s*\}}'
    match = re.search(pattern, testo_html)
    diz = {}
    if not match:
        return diz
    corpo = match.group(1)
    for riga in re.finditer(r'(\w+):\s*"((?:[^"\\]|\\.)*)"\s*,?', corpo):
        chiave, valore = riga.group(1), riga.group(2)
        diz[chiave] = valore.replace('\\"', '"').replace('\\\\', '\\')
    return diz


def aggiorna_traduzioni_sito():
    with open('index.html', 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')
    elementi_i18n = soup.find_all(attrs={"data-i18n": True})
    print(f"🔍 Trovati {len(elementi_i18n)} elementi con data-i18n...")

    dizionario_it_vecchio = estrai_dizionario_esistente(html_content, 'it')
    dizionario_en_vecchio = estrai_dizionario_esistente(html_content, 'en')

    dizionario_it = {}
    dizionario_en = {}
    fallimenti = []

    for el in elementi_i18n:
        chiave = el['data-i18n']
        if chiave in dizionario_it:
            continue

        html_it_originale = estrai_html_interno(el)
        if not html_it_originale:
            continue

        testo_it_clean = html_it_originale.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').replace('\r', '')
        dizionario_it[chiave] = testo_it_clean

        it_invariato = dizionario_it_vecchio.get(chiave) == testo_it_clean
        en_vecchio = dizionario_en_vecchio.get(chiave)
        if it_invariato and en_vecchio:
            dizionario_en[chiave] = en_vecchio
            continue

        html_en, fallimento = traduci_contenuto(el)

        if fallimento:
            fallimenti.append(chiave)

        if not html_en or not html_en.strip():
            if en_vecchio:
                print(f"↩️  '{chiave}': traduzione fallita, mantengo quella precedente.")
                dizionario_en[chiave] = en_vecchio
            else:
                print(f"❌ '{chiave}': nessuna traduzione disponibile, va sistemata a mano.")
            continue

        testo_en_clean = html_en.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').replace('\r', '')
        dizionario_en[chiave] = testo_en_clean

    righe_it = [f'      {chiave}: "{valore}",' for chiave, valore in dizionario_it.items()]
    nuovo_blocco_it = "it: {\n" + "\n".join(righe_it) + "\n    }"

    righe_en = [f'      {chiave}: "{valore}",' for chiave, valore in dizionario_en.items()]
    nuovo_blocco_en = "en: {\n" + "\n".join(righe_en) + "\n    }"

    pattern_it = r'it:\s*\{[\s\S]*?\n\s*\}'
    pattern_en = r'en:\s*\{[\s\S]*?\n\s*\}'
    html_aggiornato = re.sub(pattern_it, lambda _m: nuovo_blocco_it, html_content, count=1)
    html_aggiornato = re.sub(pattern_en, lambda _m: nuovo_blocco_en, html_aggiornato, count=1)

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_aggiornato)

    if fallimenti:
        print(f"\n⚠️ {len(fallimenti)} chiavi senza traduzione valida: {', '.join(fallimenti)}")
        sys.exit(1)

    print("✅ Traduzioni IT ed EN sincronizzate con successo!")


if __name__ == "__main__":
    aggiorna_traduzioni_sito()
