import re
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

def traduci_testo(testo):
    if not testo or not testo.strip():
        return testo
    try:
        # Traduce pulendo eventuali spazi inutili
        tradotto = GoogleTranslator(source='it', target='en').translate(testo.strip())
        return tradotto
    except Exception as e:
        print(f"⚠️ Errore traduzione: {e}")
        return testo

def aggiorna_traduzioni_sito():
    with open('index.html', 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')
    elementi_i18n = soup.find_all(attrs={"data-i18n": True})

    dizionario_en = {}

    print(f"🔍 Trovati {len(elementi_i18n)} elementi con data-i18n...")

    for el in elementi_i18n:
        chiave = el['data-i18n']
        
        # 1. FIX BUG: Estrae SOLO il testo pulito ignorando tag figli come <span class="fresh">
        testo_it = el.find(text=True, recursive=False)
        if not testo_it:
            testo_it = el.get_text()
            
        testo_it = testo_it.strip() if testo_it else ""

        if testo_it and chiave not in dizionario_en:
            print(f"🔄 Traducendo [{chiave}]...")
            testo_en = traduci_testo(testo_it)
            
            # 2. FIX BUG: Pulisce virgolette e A Capo per evitare errori di sintassi JS
            testo_en_clean = (
                testo_en.replace('\\', '\\\\')
                        .replace('"', '\\"')
                        .replace('\n', ' ')
                        .replace('\r', '')
            )
            dizionario_en[chiave] = testo_en_clean

    # 3. Costruzione sicura del blocco JavaScript
    righe_en = []
    for chiave, valore in dizionario_en.items():
        righe_en.append(f'      {chiave}: "{valore}",')
    
    nuovo_blocco_en = "en: {\n" + "\n".join(righe_en) + "\n    }"

    # 4. FIX BUG: Sostituzione mirata del dizionario EN senza toccare IT o altri script
    pattern = r'en:\s*\{[\s\S]*?\n\s*\}'
    if re.search(pattern, html_content):
        html_aggiornato = re.sub(pattern, nuovo_blocco_en, html_content, count=1)
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(html_aggiornato)
        print("✅ Traduzione completata e index.html aggiornato con successo!")
    else:
        print("❌ ERRORE: Impossibile individuare il blocco 'en: { ... }' nel file index.html")

if __name__ == "__main__":
    aggiorna_traduzioni_sito()
