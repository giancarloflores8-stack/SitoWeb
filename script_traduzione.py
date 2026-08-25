import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from bs4 import BeautifulSoup
import deepl

MAX_RETRY = 3
TIMEOUT_CHIAMATA = 15  # secondi massimi per ogni singola richiesta a DeepL

DEEPL_API_KEY = os.environ.get('DEEPL_API_KEY')
if not DEEPL_API_KEY:
    print("❌ Variabile d'ambiente DEEPL_API_KEY non trovata.")
    print("   Aggiungila tra i Secrets del repository (Settings > Secrets and variables > Actions)")
    print("   e passala al workflow con: env: DEEPL_API_KEY: ${{ secrets.DEEPL_API_KEY }}")
    sys.exit(1)

traduttore = deepl.Translator(DEEPL_API_KEY)
_esecutore = ThreadPoolExecutor(max_workers=1)


def con_timeout(funzione, *args, **kwargs):
    """Esegue una funzione con un timeout forzato, così se DeepL non
    risponde per qualche motivo lo script non resta appeso per sempre."""
    futuro = _esecutore.submit(funzione, *args, **kwargs)
    try:
        return futuro.result(timeout=TIMEOUT_CHIAMATA)
    except FutureTimeoutError:
        raise TimeoutError(f"Nessuna risposta da DeepL entro {TIMEOUT_CHIAMATA}s")


def traduci_html(html_it):
    """Traduce un frammento HTML con DeepL. Grazie a tag_handling='html',
    DeepL gestisce da solo eventuali tag annidati (es. <small>Bio</small>,
    <span class="fresh"></span>): traduce solo il testo e lascia i tag
    intatti, quindi non serve più smontare il contenuto pezzo per pezzo
    a mano come si doveva fare con Google/MyMemory."""
    if not html_it or not html_it.strip():
        return html_it

    for tentativo in range(1, MAX_RETRY + 1):
        try:
            risultato = con_timeout(
                traduttore.translate_text,
                html_it,
                source_lang='IT',
                target_lang='EN-GB',
                tag_handling='html',
            )
            if risultato and risultato.text and risultato.text.strip():
                return risultato.text
            raise ValueError("Risposta vuota da DeepL")
        except Exception as e:
            attesa = 2 ** tentativo
            print(f"⚠️ DeepL, tentativo {tentativo}/{MAX_RETRY} fallito ({e}). Riprovo tra {attesa}s...")
            time.sleep(attesa)

    return None  # fallito per davvero dopo tutti i tentativi


def estrai_html_interno(tag):
    """Ritorna l'HTML *dentro* al tag così com'è (testo + eventuali tag
    annidati tipo <small> o <span>), invece di prendere solo il primo nodo
    di testo."""
    return ''.join(str(c) for c in tag.contents).strip()


def estrai_dizionario_esistente(testo_html, lingua):
    """Legge quello che è già scritto in index.html per 'it' o 'en',
    così da non ritradurre da zero ogni volta."""
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

    for i, el in enumerate(elementi_i18n, start=1):
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

        print(f"[{i}/{len(elementi_i18n)}] Traduco '{chiave}'...")
        html_en = traduci_html(html_it_originale)

        if not html_en or not html_en.strip():
            fallimenti.append(chiave)
            if en_vecchio:
                print(f"↩️  '{chiave}': traduzione fallita, mantengo quella precedente.")
                dizionario_en[chiave] = en_vecchio
            else:
                print(f"❌ '{chiave}': nessuna traduzione disponibile, va sistemata a mano.")
            continue

        testo_en_clean = html_en.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').replace('\r', '')
        dizionario_en[chiave] = testo_en_clean
        print(f"✅ '{chiave}' tradotta.")

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
