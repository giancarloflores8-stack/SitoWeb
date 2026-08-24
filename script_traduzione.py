import os
import deepl

# Legge la chiave senza esporla nel codice sorgente
DEEPL_API_KEY = os.environ.get('DEEPL_API_KEY')

def traduci(testo, src='IT', dest='EN-US'):
    if not testo or not testo.strip():
        return testo
    
    if not DEEPL_API_KEY:
        print("⚠️ Secret DEEPL_API_KEY non trovato nei GitHub Secrets.")
        return testo

    try:
        translator = deepl.Translator(DEEPL_API_KEY)
        # tag_handling="html" mantiene intatti i tag come <br> e <span>
        result = translator.translate_text(
            testo, 
            source_lang=src, 
            target_lang=dest, 
            tag_handling="html"
        )
        return result.text
    except Exception as e:
        print(f"⚠️ Errore di traduzione: {e}")
        # Restituisce il testo originale invece di far fallire la build
        return testo
