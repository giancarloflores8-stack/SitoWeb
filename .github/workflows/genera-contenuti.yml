name: Genera Contenuti da pensieri.txt

on:
  push:
    paths:
      - 'pensieri.txt'
      - 'genera_contenuti.py'

permissions:
  contents: write

jobs:
  genera-e-traduci:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    env:
      PYTHONUNBUFFERED: "1"
    steps:
      - name: Scarica il repository
        uses: actions/checkout@v3

      - name: Configura Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.x'

      - name: Installa dipendenze
        run: pip install beautifulsoup4 deepl

      - name: Genera Pensieri e Attività recente dal testo
        run: python genera_contenuti.py

      - name: Traduci in inglese le parti nuove
        env:
          DEEPL_API_KEY: ${{ secrets.DEEPL_API_KEY }}
        run: python script_traduzione.py

      - name: Salva e pubblica
        run: |
          git config --global user.name "GitHub Content Bot"
          git config --global user.email "bot@github.com"
          git add index.html
          git commit -m "Aggiornamento automatico contenuti da pensieri.txt [skip ci]" || exit 0
          git push
