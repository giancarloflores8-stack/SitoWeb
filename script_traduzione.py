import re
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

def traduci_testo(testo):
    if not testo or not testo.strip():
        return testo
    try:
        return GoogleTranslator(source='it', target='en').translate(testo.strip())
    except Exception as e:
        print(f"⚠️ Errore traduzione: {e}")
        return testo

def aggiorna_traduzioni_sito():
    with open('index.html', 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')
    elementi_i18n = soup.find_all(attrs={"data-i18n": True})

    dizionario_it = {}
    dizionario_en = {}

    print(f"🔍 Trovati {len(elementi_i18n)} elementi con data-i18n...")

    for el in elementi_i18n:
        chiave = el['data-i18n']
        
        # Estrae solo il testo pulito ignorando i tag figli (es. <span class="fresh">)
        testo_it = el.find(text=True, recursive=False)
        if not testo_it:
            testo_it = el.get_text()
            
        testo_it = testo_it.strip() if testo_it else ""

        if testo_it and chiave not in dizionario_en:
            testo_en = traduci_testo(testo_it)
            
            # Pulisce virgolette e A Capo per la sintassi JS
            testo_it_clean = testo_it.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').replace('\r', '')
            testo_en_clean = testo_en.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').replace('\r', '')
            
            dizionario_it[chiave] = testo_it_clean
            dizionario_en[chiave] = testo_en_clean

    # 1. Costruzione blocco IT
    righe_it = [f'      {chiave}: "{valore}",' for chiave, valore in dizionario_it.items()]
    nuovo_blocco_it = "it: {\n" + "\n".join(righe_it) + "\n    }"

    # 2. Costruzione blocco EN
    righe_en = [f'      {chiave}: "{valore}",' for chiave, valore in dizionario_en.items()]
    nuovo_blocco_en = "en: {\n" + "\n".join(righe_en) + "\n    }"

    # Sostituzione sicura nel file index.html
    pattern_it = r'it:\s*\{[\s\S]*?\n\s*\}'
    pattern_en = r'en:\s*\{[\s\S]*?\n\s*\}'

    html_aggiornato = re.sub(pattern_it, nuovo_blocco_it, html_content, count=1)
    html_aggiornato = re.sub(pattern_en, nuovo_blocco_en, html_aggiornato, count=1)

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_aggiornato)

    print("✅ Traduzioni IT ed EN sincronizzate con successo!")

if __name__ == "__main__":
    aggiorna_traduzioni_sito()
