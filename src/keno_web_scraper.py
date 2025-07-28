#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de scraping des résultats Keno depuis reducmiz.com
Adapté pour intégration dans l'application Flask
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
import locale
import sys

class KenoWebScraper:
    def __init__(self):
        self.url = "https://www.reducmiz.com/resultat_fdj.php?jeu=keno&nb=all"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def convertir_date_francaise(self, date_str):
        if re.match(r'\d{1,2}/\d{1,2}/\d{4}', date_str):
            return date_str
        mois_fr = {
            'janvier': '01', 'février': '02', 'mars': '03', 'avril': '04',
            'mai': '05', 'juin': '06', 'juillet': '07', 'août': '08',
            'septembre': '09', 'octobre': '10', 'novembre': '11', 'décembre': '12'
        }
        pattern_text = r'(\d{1,2})\s+(\w+)\s+(\d{4})'
        match_text = re.search(pattern_text, date_str)
        if match_text:
            jour, mois_nom, annee = match_text.groups()
            mois_nom = mois_nom.lower().replace('é', 'e').replace('û', 'u')
            if mois_nom in mois_fr:
                jour = jour.zfill(2)
                mois = mois_fr[mois_nom]
                return f"{jour}/{mois}/{annee}"
        return date_str

    def extraire_numeros_tirage(self, cell_content):
        text = cell_content.get_text(strip=True).replace('\xa0', ' ')
        numeros = []
        for num_str in text.split():
            try:
                num = int(num_str)
                if 1 <= num <= 70:
                    numeros.append(num)
            except ValueError:
                continue
        return numeros if len(numeros) == 20 else []

    def scraper_tirages(self):
        print("Début du scraping des tirages Keno...")
        try:
            response = requests.get(self.url, headers=self.headers, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.content, 'html.parser')

            tirages = []
            tables = soup.find_all('table')

            for table in tables:
                rows = table.find_all('tr')
                tirage_data = {}
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        label = cells[0].get_text(strip=True)
                        value_cell = cells[1]

                        if label == 'date du tirage':
                            date_brute = value_cell.get_text(strip=True)
                            tirage_data['date_brute'] = date_brute
                            tirage_data['date'] = self.convertir_date_francaise(date_brute)

                        elif label == 'tirage':
                            numeros = self.extraire_numeros_tirage(value_cell)
                            if numeros:
                                tirage_data['numeros'] = numeros

                        elif label == 'multiplicateur':
                            try:
                                tirage_data['multiplicateur'] = int(value_cell.get_text(strip=True))
                            except ValueError:
                                tirage_data['multiplicateur'] = 1

                        elif label == 'numéro JOKER+®':
                            tirage_data['joker'] = value_cell.get_text(strip=True)
                            if all(key in tirage_data for key in ['date', 'numeros', 'multiplicateur']):
                                if len(tirage_data['numeros']) == 20:
                                    tirages.append(tirage_data.copy())
                            tirage_data = {}

            print(f"Nombre de tirages extraits: {len(tirages)}")
            return tirages

        except Exception as e:
            print(f"Erreur lors du scraping: {e}")
            return []

    def scraper_tirages_df(self):
        """Transforme les tirages scrapés en DataFrame directement exploitable"""
        tirages = self.scraper_tirages()
        if not tirages:
            return pd.DataFrame()

        data = []
        for tirage in tirages:
            row = {
                'date_tirage': tirage['date'],
                'heure_tirage': '13:00',  # Valeur par défaut
                'multiplicateur': tirage.get('multiplicateur', None),
                'joker': tirage.get('joker', '')
            }
            for i, num in enumerate(tirage['numeros'], 1):
                row[f'numero_{i}'] = num
            data.append(row)

        df = pd.DataFrame(data)
        df['date_tirage'] = pd.to_datetime(df['date_tirage'], format='%d/%m/%Y', errors='coerce')
        df = df.sort_values('date_tirage', ascending=False).reset_index(drop=True)
        return df

# Pour tests indépendants
if __name__ == "__main__":
    scraper = KenoWebScraper()
    df = scraper.scraper_tirages_df()
    if not df.empty:
        print(df.head())
        df.to_csv("tirages_keno.csv", index=False)
        print(f"✅ {len(df)} tirages enregistrés dans tirages_keno.csv")
    else:
        print("❌ Aucun tirage trouvé.")
