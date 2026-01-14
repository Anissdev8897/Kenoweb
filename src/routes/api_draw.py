from flask import Blueprint, jsonify
from config import DATABASE_CONFIG
import pandas as pd
from sqlalchemy import create_engine

api_draw_bp = Blueprint('api_draw', __name__)

@api_draw_bp.route('/api/last-draw', methods=['GET'])
def last_draw():
    engine = create_engine(DATABASE_CONFIG['postgresql_url'])
    query = "SELECT * FROM tirages_keno ORDER BY date DESC LIMIT 1;"
    df = pd.read_sql(query, engine)
    if df.empty:
        return jsonify({"error": "Aucun tirage trouvé"}), 404
    row = df.iloc[0]
    numbers = [row[f'numero_{i}'] for i in range(1, 21) if row.get(f'numero_{i}') is not None]
    result = {
        "date": row['date'],
        "dateBrute": row.get('date_brute', ''),
        "numbers": numbers,
        "multiplicateur": row.get('multiplicateur', ''),
        "joker": row.get('joker', '')
    }
    return jsonify(result)
