import csv
import requests
from bs4 import BeautifulSoup


def fetch_latest_draws(url):
    """Scrape les 2 derniers tirages depuis le site."""
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    draws = []

    for table in soup.find_all("table", class_="table table-condensed table-striped"):
        raw = table.find_all("td")
        if len(raw) >= 4:
            draw_data = raw[3].get_text(" ", strip=True)
            numbers = [int(num) for num in draw_data.split()[:20]]
            draws.append(numbers)
            if len(draws) == 2:
                break
    return draws


def predict_next_draw(draw1, draw2):
    """Additionne les 10 premiers numéros et applique aussi la méthode des écarts inversés."""
    # Méthode 1 : addition des 10 premiers
    additioned = [draw1[i] + draw2[i] for i in range(10)]

    # Méthode 2 : soustraction des écarts inversés sur les 10 derniers
    diffs = [draw1[-10 + i] - draw2[-10 + i] for i in range(10)]
    reversed_simulation = [draw1[-10 + i] - diffs[i] for i in range(10)]

    return additioned, reversed_simulation


def save_to_csv(file_path, numbers):
    with open(file_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(numbers)


def main():
    url = "https://www.reducmiz.com/resultat_fdj.php?jeu=keno&nb=all"
    csv_file = "historique_tirages.csv"

    print("\n🔢 Chargement des 2 derniers tirages...")
    draws = fetch_latest_draws(url)
    if len(draws) < 2:
        print("❌ Impossible de récupérer deux tirages complets.")
        return

    draw1, draw2 = draws
    print(f"\n🎯 Tirage 1 : {draw1}\n🎯 Tirage 2 : {draw2}")

    add_result, reverse_result = predict_next_draw(draw1, draw2)

    print("\n📈 Résultat par addition (méthode 1) :")
    print(add_result)
    print("\n📉 Résultat par écart inversé (méthode 2) :")
    print(reverse_result)

    save = input("\n💾 Souhaitez-vous sauvegarder le résultat dans un fichier CSV ? (y/n) : ").strip().lower()
    if save == 'y':
        save_to_csv(csv_file, add_result)
        save_to_csv(csv_file, reverse_result)
        print(f"✅ Résultats ajoutés à {csv_file}")

    choix = input("\n🔍 Entrez une position (1-20) pour analyser un numéro spécifique : ")
    try:
        pos = int(choix)
        if 1 <= pos <= 20:
            print(f"\n👉 À la position {pos}, tirage 1 = {draw1[pos-1]}, tirage 2 = {draw2[pos-1]}")
            print(f"   ➕ Somme : {draw1[pos-1] + draw2[pos-1]}")
            print(f"   ➖ Écart inversé : {draw1[20-pos] - (draw1[20-pos] - draw2[20-pos])}")
        else:
            print("⚠️ Position invalide.")
    except ValueError:
        print("⚠️ Entrée invalide. Veuillez entrer un nombre entre 1 et 20.")


if __name__ == "__main__":
    main()
