import re
import sys
import time
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

MAX_RETRY = 4
PAUSA_TRA_CHIAMATE = 1.2  # secondi, per non farsi bloccare da Google

def traduci_testo(testo):
    """Traduce con retry ed exponential backoff. Ritorna None se fallisce
    davvero (mai il testo italiano spacciato per inglese)."""
    if not testo or not testo.strip():
        return testo

    for tentativo in range(1, MAX_RETRY + 1):
        try:
            risultato = GoogleTranslator(source='it', target='en').translate(testo.strip())
            time.sleep(PAUSA_TRA_CHIAMATE)
            if risultato and risultato.strip():
                return risultato
            raise ValueError("Risposta vuota da Google Translate")
        except Exception as e:
            attesa = 2 ** tentativo
            print(f"⚠️ Tentativo {tentativo}/{MAX_RETRY} fallito ({e}). Riprovo tra {attesa}s...")
            time.sleep(attesa)

    return None  # fallito per davvero dopo tutti i tentativi


def estrai_dizionario_esistente(soup_o_testo, lingua):
    """Legge quello che è già scritto in index.html per 'it' o 'en',
    cosi da non ritradurre da zero ogni volta e non perdere correzioni manuali."""
    pattern = rf'{lingua}:\s*\{{([\s\S]*?)\n\s*\}}'
    match = re.search(pattern, soup_o_testo)
    diz = {}
    if not match:
        return diz
    corpo = match.group(1)
    # righe tipo:  chiave: "valore",
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

    # Traduzioni già presenti nel file (per non ripartire da zero ogni volta)
    dizionario_it_vecchio = estrai_dizionario_esistente(html_content, 'it')
    dizionario_en_vecchio = estrai_dizionario_esistente(html_content, 'en')

    dizionario_it = {}
    dizionario_en = {}
    fallimenti = []

    for el in elementi_i18n:
        chiave = el['data-i18n']
        if chiave in dizionario_it:
            continue  # chiave già processata in questo giro

        testo_it_raw = el.find(text=True, recursive=False)
        if not testo_it_raw:
            testo_it_raw = el.get_text()
        testo_it = testo_it_raw.strip() if testo_it_raw else ""
        if not testo_it:
            continue

        testo_it_clean = testo_it.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').replace('\r', '')
        dizionario_it[chiave] = testo_it_clean

        # Se il testo italiano non è cambiato rispetto all'ultima esecuzione
        # e avevamo già una traduzione inglese valida e diversa dall'italiano,
        # la riusiamo: zero chiamate inutili a Google, zero rischio di rompere
        # una traduzione già corretta.
        it_invariato = dizionario_it_vecchio.get(chiave) == testo_it_clean
        en_vecchio = dizionario_en_vecchio.get(chiave)
        if it_invariato and en_vecchio:
            dizionario_en[chiave] = en_vecchio
            continue

        testo_en = traduci_testo(testo_it)
        if testo_en is None:
            fallimenti.append(chiave)
            # Non scriviamo l'italiano al posto dell'inglese: teniamo la
            # vecchia traduzione se esiste, altrimenti segnaliamo il buco.
            if en_vecchio:
                print(f"↩️  '{chiave}': traduzione fallita, mantengo quella precedente.")
                dizionario_en[chiave] = en_vecchio
            else:
                print(f"❌ '{chiave}': nessuna traduzione disponibile, va sistemata a mano.")
        else:
            testo_en_clean = testo_en.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').replace('\r', '')
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
        # Fallisce la Action così te ne accorgi nei log invece che scoprirlo
        # mesi dopo guardando il sito in inglese pieno di frasi in italiano.
        sys.exit(1)

    print("✅ Traduzioni IT ed EN sincronizzate con successo!")


if __name__ == "__main__":
    aggiorna_traduzioni_sito()
