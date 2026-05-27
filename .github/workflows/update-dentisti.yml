name: Actualizare saptamanala dentisti
on:
  schedule:
    - cron: '0 6 * * 1'
  workflow_dispatch:
jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Ruleaza script
        env:
          GOOGLE_PLACES_API_KEY: ${{ secrets.GOOGLE_PLACES_API_KEY }}
        run: python update_dentisti.py
      - name: Commit
        run: |
          git config user.name "Bot"
          git config user.email "bot@bot.com"
          git add dentistaproape/data/dentisti.json || true
          git diff --staged --quiet || git commit -m "update $(date '+%Y-%m-%d')"
          git push || true
      - name: Deploy FTP
        uses: SamKirkland/FTP-Deploy-Action@v4.3.4
        with:
          server: ${{ secrets.FTP_SERVER }}
          username: ${{ secrets.FTP_USERNAME }}
          password: ${{ secrets.FTP_PASSWORD }}
          local-dir: dentistaproape/data/
          server-dir: public_html/data/
