import os
import re
import json
from bs4 import BeautifulSoup
import deepl

DEEPL_API_KEY = os.environ.get('DEEPL_API_KEY')

def genera_traduzioni():
    with open('index.html', 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')
    
    dict_it = {}
    dict_en = {}
    
    translator = deepl.Translator(DEEPL_API_KEY) if DEEPL_API_KEY else None

    # 1. Trova TUTTI gli elementi con data-i18n nell'HTML
    elements = soup.find_all(attrs={"data-i18n": True})
    print(f"🔍 Trovati {len(elements)} elementi da processare...")

    for el in elements:
        key = el['data-i18n']
        # Prende il testo italiano direttamente dal tag HTML
        text_it = el.decode_contents().strip()
        
        if not key or not text_it:
            continue

        dict_it[key] = text_it

        # 2. Traduce automaticamente in Inglese con DeepL
        if translator:
            try:
                translated = translator.translate_text(
                    text_it, 
                    source_lang="IT", 
                    target_lang="EN-US", 
                    tag_handling="html"
                )
                dict_en[key] = translated.text
            except Exception as e:
                print(f"⚠️ Errore traduzione per {key}: {e}")
                dict_en[key] = text_it
        else:
            dict_en[key] = text_it # Fallback se manca la chiave API

    # 3. Costruisce il nuovo oggetto JavaScript
    new_translations_js = f"const translations = {{\n  it: {json.dumps(dict_it, ensure_ascii=False, indent=4)},\n  en: {json.dumps(dict_en, ensure_ascii=False, indent=4)}\n}};"

    # 4. Sostituisce 'const translations = { ... };' dentro index.html
    pattern = r'const translations\s*=\s*\{[\s\S]*?\};'
    if re.search(pattern, html_content):
        updated_html = re.sub(pattern, new_translations_js, html_content)
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(updated_html)
        print("✅ Traduzioni generate e sovrascritte con successo in index.html!")
    else:
        print("❌ Impossibile trovare 'const translations = {...}' nel file index.html.")

if __name__ == '__main__':
    genera_traduzioni()
