import re
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

def traduci_testo(testo):
    if not testo or testo.strip() == "":
        return testo
    try:
        tradotto = GoogleTranslator(source='it', target='en').translate(testo.strip())
        return tradotto
    except Exception as e:
        print(f"Errore durante la traduzione: {e}")
        return testo

def aggiorna_traduzioni_sito():
    with open('index.html', 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')
    elementi_i18n = soup.find_all(attrs={"data-i18n": True})

    dizionario_en = {}

    for el in elementi_i18n:
        chiave = el['data-i18n']
        testo_it = el.decode_contents().strip()

        if testo_it:
            testo_en = traduci_testo(testo_it)
            testo_en_clean = testo_en.replace('"', '\\"').replace('\n', ' ')
            dizionario_en[chiave] = testo_en_clean

    nuovo_blocco_en = "en: {\n"
    for chiave, valore in dizionario_en.items():
        nuovo_blocco_en += f'      {chiave}: "{valore}",\n'
    nuovo_blocco_en += "    }"

    html_aggiornato = re.sub(
        r'en:\s*\{[^}]*\}',
        nuovo_blocco_en,
        html_content,
        flags=re.DOTALL
    )

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_aggiornato)

if __name__ == "__main__":
    aggiorna_traduzioni_sito()
