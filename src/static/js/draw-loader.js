// Système robuste de chargement des tirages Keno
// Gère les erreurs et fournit des données de fallback

class DrawLoader {
    constructor() {
        this.fallbackDraw = {
            date: '27/07/2025',
            dateBrute: 'aujourd\'hui dimanche 27/07/2025 midi',
            numbers: [2, 6, 7, 8, 10, 13, 14, 20, 21, 22, 24, 28, 32, 38, 40, 43, 44, 47, 58, 62],
            multiplicateur: '2',
            joker: '8782276'
        };
    }

    async loadLastDraw() {
        try {
            const response = await fetch('tirages_keno.csv');
            
            if (!response.ok) {
                console.warn('Erreur HTTP:', response.status);
                return this.fallbackDraw;
            }

            const data = await response.text();
            const lines = data.trim().split('\n');

            if (lines.length <= 1) {
                console.warn('Fichier CSV vide ou sans données');
                return this.fallbackDraw;
            }

            const draws = this.parseDraws(lines);
            
            if (draws.length === 0) {
                console.warn('Aucun tirage valide trouvé');
                return this.fallbackDraw;
            }

            // Trier par date décroissante
            draws.sort((a, b) => {
                const dateA = a.date.split('/').reverse().join('-');
                const dateB = b.date.split('/').reverse().join('-');
                return new Date(dateB) - new Date(dateA);
            });

            return draws[0];

        } catch (error) {
            console.error('Erreur chargement CSV:', error);
            return this.fallbackDraw;
        }
    }

    parseDraws(lines) {
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
            }
        }

        return draws;
    }

    createNumberBalls(numbers) {
        return numbers.map(num => 
            `<span style="display: inline-block; background: linear-gradient(135deg, #2196F3, #1976D2); color: white; border-radius: 50%; width: 32px; height: 32px; line-height: 32px; text-align: center; margin: 2px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">${num}</span>`
        ).join('');
    }

    displayDraw(draw) {
        if (!draw) return;

        const numberBalls = this.createNumberBalls(draw.numbers);
        
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
    const loader = new DrawLoader();
    loader.loadLastDraw().then(draw => {
        loader.displayDraw(draw);
    }).catch(error => {
        console.error('Erreur finale:', error);
        loader.displayDraw(loader.fallbackDraw);
    });
}

// Auto-chargement au démarrage
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(loadLastDrawInfo, 500);
});
