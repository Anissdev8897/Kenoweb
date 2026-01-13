import numpy as np
import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer, StandardScaler

class KenoFeatureEncoder:
    """
    Encoder for Keno data to prepare features for Machine Learning models.
    Handles transformation of raw draw data into feature vectors.
    """

    def __init__(self, window_size=10):
        self.window_size = window_size
        self.scaler = StandardScaler()
        self.mlb = MultiLabelBinarizer(classes=range(1, 71))
        self.is_fitted = False

    def fit(self, draws_data):
        """
        Fit the encoder on the historical data.
        Expects a list of draws or a DataFrame.
        """
        # Fit logic if needed for global stats, currently mainly scaling
        # We need to generate features first to fit the scaler
        features, _ = self._generate_features_targets(draws_data)
        if features is not None and len(features) > 0:
            self.scaler.fit(features)
            self.is_fitted = True

    def transform(self, draws_data):
        """
        Transform draws data into feature vectors.
        """
        if not self.is_fitted:
            raise ValueError("Encoder must be fitted before transform")

        features, targets = self._generate_features_targets(draws_data)
        if features is not None:
            features_scaled = self.scaler.transform(features)
            return features_scaled, targets
        return None, None

    def _generate_features_targets(self, draws_data):
        """
        Internal method to generate features and targets from draws.
        """
        # Convert to matrix of numbers if it's a list of dicts
        if isinstance(draws_data, list):
            # Sort by date asc
            draws_data = sorted(draws_data, key=lambda x: x['date'])
            numbers_matrix = [d['numbers'] for d in draws_data]
        elif isinstance(draws_data, pd.DataFrame):
             # Extract number columns
            numero_cols = [col for col in draws_data.columns if col.startswith('numero_')]
            numbers_matrix = draws_data[numero_cols].values
        else:
            return None, None

        numbers_matrix = np.array(numbers_matrix)

        features = []
        targets = []

        if len(numbers_matrix) <= self.window_size:
            return None, None

        for i in range(self.window_size, len(numbers_matrix)):
            # Features: history window
            feature_vector = []

            # 1. Frequency in window (One-Hot-ish weighted by frequency)
            window_numbers = numbers_matrix[i-self.window_size:i].flatten()
            freq_vector = np.zeros(70)
            for num in window_numbers:
                if 1 <= num <= 70:
                    freq_vector[num-1] += 1

            # Normalize frequencies
            if np.sum(freq_vector) > 0:
                freq_vector = freq_vector / np.sum(freq_vector)
            feature_vector.extend(freq_vector)

            # 2. Gaps (time since last appearance)
            last_draw = numbers_matrix[i-1]
            gap_vector = np.zeros(70)

            for j in range(70):
                num = j + 1
                if num in last_draw:
                    gap_vector[j] = 0
                else:
                    gap = 1
                    # Look back
                    found = False
                    for k in range(i-2, max(0, i-self.window_size-1), -1):
                        if num in numbers_matrix[k]:
                            gap = i - 1 - k
                            found = True
                            break
                    if not found:
                        gap = self.window_size
                    gap_vector[j] = gap

            feature_vector.extend(gap_vector)

            # 3. Temporal/Meta features
            feature_vector.extend([
                i % 7, # Simulated day of week (imperfect if not using real dates)
                np.mean(window_numbers), # Mean of numbers
                np.std(window_numbers)   # Std dev of numbers
            ])

            features.append(feature_vector)

            # Target: Next draw (Multi-hot encoded)
            current_draw = numbers_matrix[i]
            target_vector = np.zeros(70)
            for num in current_draw:
                if 1 <= num <= 70:
                    target_vector[num-1] = 1
            targets.append(target_vector)

        return np.array(features), np.array(targets)

    def encode_single_draw(self, recent_history):
        """
        Encode a single sequence (recent history) to predict the NEXT draw.
        Used for inference.
        """
        if not self.is_fitted:
             raise ValueError("Encoder must be fitted")

        # Create a single feature vector from the last 'window_size' draws
        # Reuse the logic from _generate_features_targets but for a single instance

        # ... (Implementation similar to loop body above) ...
        # For brevity, I'll simplify or ideally refactor the common logic.
        # Let's just create a dummy "draws_data" with the recent history + 1 dummy draw
        # so _generate_features_targets can process it, and we take the last feature.

        if len(recent_history) < self.window_size:
             return None

        # Add dummy next draw
        dummy_data = recent_history + [{'numbers': []}] # structure depends on input type
        # Ideally we refactor. For now, let's implement the extraction logic directly for a single vector.

        numbers_matrix = np.array([d['numbers'] for d in recent_history[-self.window_size:]])

        feature_vector = []

        # Freq
        window_numbers = numbers_matrix.flatten()
        freq_vector = np.zeros(70)
        for num in window_numbers:
            if 1 <= num <= 70:
                freq_vector[num-1] += 1
        if np.sum(freq_vector) > 0:
            freq_vector = freq_vector / np.sum(freq_vector)
        feature_vector.extend(freq_vector)

        # Gaps
        last_draw = numbers_matrix[-1]
        gap_vector = np.zeros(70)
        for j in range(70):
            num = j + 1
            if num in last_draw:
                gap_vector[j] = 0
            else:
                gap = 1
                found = False
                for k in range(len(numbers_matrix)-2, -1, -1):
                    if num in numbers_matrix[k]:
                        gap = len(numbers_matrix) - 1 - k
                        found = True
                        break
                if not found:
                    gap = self.window_size
                gap_vector[j] = gap
        feature_vector.extend(gap_vector)

        # Meta
        feature_vector.extend([
            0, # Day (dummy)
            np.mean(window_numbers),
            np.std(window_numbers)
        ])

        # Scale
        feature_vector = np.array(feature_vector).reshape(1, -1)
        return self.scaler.transform(feature_vector)
