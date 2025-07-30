def save_prediction(self, user_id, method, numeros=None, confidence=0.0, session_id=None):
    try:
        # 🔹 Compatibilité avec clés différentes (numbers vs numeros)
        if numeros is None:
            logger.warning("Le paramètre 'numeros' est None, vérifiez votre API.")
            return None

        # 🔹 Conversion sécurisée en liste d'entiers (si la source est chaîne ou tuple)
        if isinstance(numeros, str):
            try:
                numeros = [int(x) for x in numeros.replace('[', '').replace(']', '').split(',')]
            except Exception as e:
                logger.error(f"Erreur de conversion de numeros depuis une chaîne: {e}")
                return None
        elif not isinstance(numeros, list):
            logger.error(f"Type inattendu pour 'numeros': {type(numeros)}")
            return None

        with self.engine.connect() as conn:
            with conn.begin():
                result = conn.execute(text("""
                    INSERT INTO predictions (user_id, method, numeros, confidence, session_id)
                    VALUES (:user_id, :method, :numeros, :confidence, :session_id)
                    RETURNING id
                """), {
                    "user_id": user_id,
                    "method": method,
                    "numeros": numeros,
                    "confidence": confidence or 0.0,
                    "session_id": session_id
                })
                prediction_id = result.fetchone()[0]
                logger.info(f"✅ Prédiction sauvegardée: {user_id} - {method} (ID: {prediction_id})")
                return prediction_id

    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde prédiction: {e}")
        return None
