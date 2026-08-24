import time
from deep_translator import GoogleTranslator, MyMemoryTranslator

def traduci_testo(testo, src='it', dest='en'):
    if not testo or not testo.strip():
        return testo

    # Pulizia preliminare di eventuali tag HTML o entity
    testo_prep = testo.replace('<br>', ' --- ')
    
    # 1. Tentativo con Google Translator (usa 'it' e 'en')
    try:
        traduzione = GoogleTranslator(source=src, target=dest).translate(testo_prep)
        if traduzione:
            return traduzione.replace(' --- ', '<br>')
    except Exception as e:
        print(f"⚠️ Google fallito per '{testo[:30]}...': {e}")
    
    time.sleep(1)

    # 2. Fallback con MyMemory (richiede codici ISO estesi come 'it-IT' e 'en-GB')
    try:
        lang_map_mymemory = {
            'it': 'it-IT',
            'en': 'en-GB'
        }
        src_mm = lang_map_mymemory.get(src, src)
        dest_mm = lang_map_mymemory.get(dest, dest)
        
        traduzione = MyMemoryTranslator(source=src_mm, target=dest_mm).translate(testo_prep)
        if traduzione:
            return traduzione.replace(' --- ', '<br>')
    except Exception as e:
        print(f"⚠️ MyMemory fallito per '{testo[:30]}...': {e}")

    # 3. Se entrambe le API falliscono, restituisce il testo originale per evitare il blocco (exit code 1)
    return testo
