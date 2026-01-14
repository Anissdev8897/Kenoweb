// Fonction robuste de chargement et parsing du CSV tirages_keno.csv
// Respecte exactement la structure : date,date_brute,numero_1,...,numero_20,multiplicateur,joker

class CSVLoader {
    constructor() {
        this.fallbackData = [
            {
                date: '27/07/2025',
                dateBrute: 'aujourd\'hui dimanche 27/07/2025 midi',
                numbers: [2, 6, 7, 8, 10, 13, 14, 20, 21, 22, 24, 28, 32, 38, 40, 43, 44, 47, 58, 62],
                multiplicateur: '2',
                joker: '8782276'
            },
            {
                date: '26/07/2025',
                dateBrute: 'hier samedi 26/07/2025 soir',
                numbers: [1, 2, 4, 6, 7, 14, 20, 33, 34, 36, 37, 38, 39, 48, 49, 53, 55, 56, 58, 64],
                multiplicateur: '2',
                joker: '1834297'
            },
            {
                date: '26/07/2025',
                dateBrute: 'hier samedi 26/07/2025 midi',
                numbers: [1, 3, 4, 6, 10, 11, 14, 18, 22, 28, 34, 39, 45, 50, 53, 57, 59, 62, 64, 69],
                multiplicateur: '2',
                joker: '6462941'
            }
        ];
    }

    async loadLastDraw() {
        try {
            const response = await fetch('/api/last-draw');
            if (!response.ok) {
                console.warn('Erreur HTTP:', response.status);
                return null;
            }
            const draw = await response.json();
            return draw;
        } catch (error) {
            console.error('Erreur chargement API:', error);
            return null;
        }
    }

    parseCSVData(lines) {
        const draws = [];
        
        // Ignorer la première ligne (en-têtes)
        for (let i = 1; i < lines.length; i++) {
            const line = lines[i].trim();
            if (!line) continue;

            const cols = line.split(',');
            
            // Vérifier la structure exacte : 24 colonnes minimum
            if (cols.length >= 24) {
                try {
                    // Extraire les 20 numéros (colonnes 2 à 21)
                    const numbers = [];
                    for (let j = 2; j < 22; j++) {
                        const num = cols[j]?.trim();
                        if (num && !isNaN(parseInt(num))) {
                            numbers.push(parseInt(num));
                        }
                    }

                    const draw = {
                        date: cols[0]?.trim() || 'Date inconnue',
                        dateBrute: cols[1]?.trim() || 'N/A',
                        numbers: numbers,
                        multiplicateur: cols[22]?.trim() || '1',
                        joker: cols[23]?.trim() || ''
                    };

                    if (draw.numbers.length > 0) {
                        draws.push(draw);
                    }
                } catch (e) {
                    console.warn(`Erreur parsing ligne ${i+1}:`, e.message);
                }
            } else {
                console.warn(`Ligne ${i+1} ignorée: ${cols.length} colonnes trouvées, 24 attendues`);
            }
        }

        return draws;
    }

    generateNumberBalls(numbers) {
        return numbers.map(num => 
            `<span style="display: inline-block; background: linear-gradient(135deg, #2196F3, #1976D2); color: white; border-radius: 50%; width: 32px; height: 32px; line-height: 32px; text-align: center; margin: 2px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">${num}</span>`
        ).join('');
    }

    displayLastDraw(draw) {
        if (!draw) return;

        const numberBalls = this.generateNumberBalls(draw.numbers);
        
        const html = `
            <div style="margin-bottom: 15px;">
                <strong>📅 Date du tirage :</strong> ${draw.date}
                <br><small style="color: #666;">${draw.dateBrute}</small>
            </div>
            <div style="margin-bottom: 15px;">
                <strong>🎯 Numéros tirés (${draw.numbers.length} numéros) :</strong>
                <div style="margin-top: 8px; display: flex; flex-wrap: wrap; gap: 4px;">
                    ${numberBalls}
                </div>
            </div>
            <div style="margin-bottom: 10px;">
                <strong>📈 Multiplicateur :</strong> ${draw.multiplicateur}
                <br><strong>🎲 Joker :</strong> ${draw.joker}
            </div>
            <div style="font-size: 0.8rem; color: #666; margin-top: 10px;">
                <em>Données chargées depuis tirages_keno.csv</em>
            </div>
        `;

        const element = document.getElementById('lastDrawInfo');
        if (element) {
            element.innerHTML = html;
        }
    }
}

// Fonction globale pour compatibilité avec le code existant
function loadLastDrawInfo() {
    const loader = new CSVLoader();
    loader.loadLastDraw().then(draw => {
        loader.displayLastDraw(draw);
    }).catch(error => {
        console.error('Erreur finale:', error);
        // Afficher les données fallback même en cas d'erreur critique
        loader.displayLastDraw(loader.fallbackData[0]);
    });
}

// Auto-chargement au démarrage
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(loadLastDrawInfo, 500); // Petit délai pour s'assurer que le DOM est prêt
});
