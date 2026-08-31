import re
import sys

try:
    import language_tool_python
except ImportError:
    print("⚠️  Libreria language-tool-python non installata, controllo grammaticale saltato.")
    sys.exit(0)

_strumento = None


def ottieni_strumento():
    """Si collega al servizio pubblico e gratuito di LanguageTool, in
    italiano. Nessuna chiave API richiesta."""
    global _strumento
    if _strumento is None:
        _strumento = language_tool_python.LanguageToolPublicAPI('it')
    return _strumento


def correggi_testo(testo):
    """Corregge un pezzo di testo in italiano usando LanguageTool.
    Se il servizio non risponde (es. problema di rete temporaneo),
    lascia il testo originale invariato invece di far fallire tutto."""
    if not testo or not testo.strip():
        return testo
    try:
        strumento = ottieni_strumento()
        return strumento.correct(testo)
    except Exception as e:
        print(f"⚠️  Correzione saltata per un problema di rete/servizio: {e}")
        return testo


def correggi_pensieri_txt(percorso='pensieri.txt'):
    """Legge pensieri.txt, corregge SOLO il testo dentro PENSIERO: e
    TIMELINE: (mai DATA:, TAG: o FOTO:, che devono restare esattamente
    nel formato che genera_contenuti.py si aspetta), e riscrive il file."""
    with open(percorso, 'r', encoding='utf-8') as f:
        contenuto_originale = f.read()

    blocchi = contenuto_originale.split('---')
    nuovi_blocchi = []
    numero_correzioni = 0

    for blocco in blocchi:
        if not blocco.strip():
            nuovi_blocchi.append(blocco)
            continue

        righe = blocco.split('\n')
        nuove_righe = []

        for riga in righe:
            match_pensiero = re.match(r'^(PENSIERO:\s*)(.*)$', riga)
            match_timeline = re.match(r'^(TIMELINE:\s*)(.*)$', riga)

            if match_pensiero:
                prefisso, testo = match_pensiero.groups()
                testo_corretto = correggi_testo(testo)
                if testo_corretto != testo:
                    numero_correzioni += 1
                    print(f"  ✏️  PENSIERO corretto:\n     prima: {testo}\n     dopo:  {testo_corretto}")
                nuove_righe.append(prefisso + testo_corretto)
            elif match_timeline:
                prefisso, testo = match_timeline.groups()
                testo_corretto = correggi_testo(testo)
                if testo_corretto != testo:
                    numero_correzioni += 1
                    print(f"  ✏️  TIMELINE corretta:\n     prima: {testo}\n     dopo:  {testo_corretto}")
                nuove_righe.append(prefisso + testo_corretto)
            else:
                # DATA, TAG, FOTO e qualsiasi altra riga restano identiche
                nuove_righe.append(riga)

        nuovi_blocchi.append('\n'.join(nuove_righe))

    nuovo_contenuto = '---'.join(nuovi_blocchi)

    if nuovo_contenuto != contenuto_originale:
        with open(percorso, 'w', encoding='utf-8') as f:
            f.write(nuovo_contenuto)
        print(f"\n✅ Controllo grammaticale completato: {numero_correzioni} correzioni applicate.")
    else:
        print("\n✅ Controllo grammaticale completato: nessuna correzione necessaria.")


if __name__ == '__main__':
    correggi_pensieri_txt()
