import pandas as pd
import numpy as np
from datetime import datetime

# Importar el analizador de popularidad de la Tarea 5
try:
    from popularity_analyser import get_combination_popularity
except ImportError:
    # Solución simple si el script se ejecuta desde un directorio diferente al 'scripts'
    # o si hay problemas con el PYTHONPATH en el entorno de ejecución del sub-task.
    # Esto asume que popularity_analyser.py está en el mismo directorio.
    print("Advertencia: No se pudo importar 'popularity_analyser' directamente. Intentando importación alternativa.")
    try:
        # Intentar importar explícitamente si está en el mismo dir (para el subtask)
        import popularity_analyser
        get_combination_popularity = popularity_analyser.get_combination_popularity
        print("Importación alternativa de 'popularity_analyser' exitosa.")
    except Exception as e:
        print(f"Error en importación alternativa de 'popularity_analyser': {e}")
        # Fallback a una función dummy si todo falla, para que el script no se rompa completamente
        # aunque la funcionalidad 'AntiPopular' no funcionará correctamente.
        def get_combination_popularity(main_numbers, stars):
            print("ADVERTENCIA: Usando get_combination_popularity DUMMY. El módulo real no se cargó.")
            return 0


# --- Constantes del Juego ---
NUM_MAIN_NUMBERS_TO_PICK = 5
MAX_MAIN_NUMBER = 50
MIN_MAIN_NUMBER = 1
NUM_STAR_NUMBERS_TO_PICK = 2
MAX_STAR_NUMBER = 12
MIN_STAR_NUMBER = 1

# --- Modelo de Tendencia Histórica ---
# Columnas de números y estrellas (consistente con process_euromillions_data.py)
NUMBER_COLS = ['N1', 'N2', 'N3', 'N4', 'N5']
STAR_COLS = ['E1', 'E2']

def load_historical_data(file_path="data/euromillions_history_cleaned.parquet"):
    """Carga los datos históricos limpios."""
    try:
        df = pd.read_parquet(file_path)
        # Asegurarse que DrawDate es datetime
        df['DrawDate'] = pd.to_datetime(df['DrawDate'])
        print(f"Datos históricos cargados desde {file_path}")
        return df
    except FileNotFoundError:
        print(f"Error: El archivo histórico {file_path} no fue encontrado.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error cargando datos históricos: {e}")
        return pd.DataFrame()

def calculate_time_weighted_frequencies(df, date_col, value_cols, decay_factor=0.99):
    """
    Calcula frecuencias ponderadas temporalmente.
    Los sorteos más recientes tienen más peso.
    decay_factor: entre 0 y 1. Más cercano a 1 da más peso a lo reciente.
    """
    if df.empty or not value_cols:
        return pd.Series(dtype='float64')

    df_sorted = df.sort_values(by=date_col)

    all_values_weighted = {}

    # Calcular pesos basados en el orden del sorteo (más simple que usar fechas exactas)
    # El sorteo más reciente tiene peso 1, el anterior decay_factor, el anterior decay_factor^2, etc.
    # Corrected weight calculation: higher weight for more recent draws.
    # If sorted ascending by date, last rows are most recent.
    weights = decay_factor ** np.arange(len(df_sorted))[::-1]


    for i, row_tuple in enumerate(df_sorted.iterrows()):
        row = row_tuple[1] # iterrows() yields (index, Series)
        weight = weights[i]
        for col in value_cols:
            val = row[col]
            all_values_weighted[val] = all_values_weighted.get(val, 0) + weight

    weighted_frequencies = pd.Series(all_values_weighted)
    if weighted_frequencies.sum() == 0: # Evitar división por cero si no hay datos o pesos
        return pd.Series(dtype='float64')

    return weighted_frequencies / weighted_frequencies.sum() # Normalizar a probabilidades

class HistoricalTrendModel:
    def __init__(self, historical_data_path="data/euromillions_history_cleaned.parquet", decay_factor=0.995):
        self.historical_df = load_historical_data(historical_data_path)
        self.decay_factor = decay_factor
        self.main_probs = None
        self.star_probs = None
        self._prepare_probabilities()

    def _prepare_probabilities(self):
        if self.historical_df.empty:
            print("Modelo Histórico: No hay datos históricos, no se pueden calcular probabilidades.")
            # Fallback a uniforme si no hay datos
            self.main_probs = pd.Series(np.ones(MAX_MAIN_NUMBER) / MAX_MAIN_NUMBER, index=range(MIN_MAIN_NUMBER, MAX_MAIN_NUMBER + 1))
            self.star_probs = pd.Series(np.ones(MAX_STAR_NUMBER) / MAX_STAR_NUMBER, index=range(MIN_STAR_NUMBER, MAX_STAR_NUMBER + 1))
            return

        self.main_probs = calculate_time_weighted_frequencies(self.historical_df, 'DrawDate', NUMBER_COLS, self.decay_factor)
        self.star_probs = calculate_time_weighted_frequencies(self.historical_df, 'DrawDate', STAR_COLS, self.decay_factor)

        # Asegurar que todos los números posibles tengan una probabilidad (incluso si es muy pequeña)
        # para evitar errores en np.random.choice si un número nunca ha salido.
        for i in range(MIN_MAIN_NUMBER, MAX_MAIN_NUMBER + 1):
            if i not in self.main_probs: self.main_probs[i] = 1e-9 # Probabilidad muy pequeña
        self.main_probs = self.main_probs / self.main_probs.sum() # Re-normalizar

        for i in range(MIN_STAR_NUMBER, MAX_STAR_NUMBER + 1):
            if i not in self.star_probs: self.star_probs[i] = 1e-9
        self.star_probs = self.star_probs / self.star_probs.sum()


    def generate_combination(self):
        if self.main_probs is None or self.main_probs.empty or self.star_probs is None or self.star_probs.empty or self.main_probs.sum() == 0 or self.star_probs.sum() == 0:
            print("Modelo Histórico: Probabilidades no disponibles o inválidas. Usando generación uniforme como fallback.")
            return UniformRandomModel().generate_combination()

        main_numbers = np.random.choice(self.main_probs.index, size=NUM_MAIN_NUMBERS_TO_PICK, replace=False, p=self.main_probs.values)
        stars = np.random.choice(self.star_probs.index, size=NUM_STAR_NUMBERS_TO_PICK, replace=False, p=self.star_probs.values)
        return sorted(main_numbers.tolist()), sorted(stars.tolist())

# --- Modelo Aleatorio Uniforme ---
class UniformRandomModel:
    def generate_combination(self):
        main_numbers = np.random.choice(np.arange(MIN_MAIN_NUMBER, MAX_MAIN_NUMBER + 1), size=NUM_MAIN_NUMBERS_TO_PICK, replace=False)
        stars = np.random.choice(np.arange(MIN_STAR_NUMBER, MAX_STAR_NUMBER + 1), size=NUM_STAR_NUMBERS_TO_PICK, replace=False)
        return sorted(main_numbers.tolist()), sorted(stars.tolist())

# --- Modelo Anti-Popular ---
class AntiPopularModel:
    def __init__(self, num_candidates=1000):
        # Genera N candidatos (aleatorios) y elige el menos popular.
        self.num_candidates = num_candidates
        self.random_model = UniformRandomModel() # Usa el modelo uniforme para generar candidatos

    def generate_combination(self):
        candidates = []
        for _ in range(self.num_candidates):
            main_numbers, stars = self.random_model.generate_combination()
            candidates.append({'main': main_numbers, 'stars': stars})

        if not candidates:
            # Fallback si algo va mal
            return self.random_model.generate_combination()

        best_candidate = None
        lowest_popularity_score = float('inf')

        for cand_set in candidates:
            mn = cand_set['main']
            st = cand_set['stars']
            # Aquí es donde se usa get_combination_popularity
            # Asegurarse que la función es accesible.
            try:
                pop_score = get_combination_popularity(mn, st)
                if pop_score < lowest_popularity_score:
                    lowest_popularity_score = pop_score
                    best_candidate = (mn, st)
            except Exception as e:
                print(f"Error calculando popularidad para candidato: {mn}/{st}. Error: {e}")
                # Si falla el cálculo de popularidad, este candidato no puede ser el mejor.
                # Podríamos decidir devolver un aleatorio si esto pasa mucho.
                continue # Saltar este candidato

        if best_candidate:
            # Return copies to avoid modifying the list later if it's stored somewhere
            return list(best_candidate[0]), list(best_candidate[1])
        else:
            # Si todos los candidatos fallaron en el cálculo de popularidad (improbable pero posible)
            # o si no hay candidatos, devolvemos uno aleatorio.
            print("Advertencia: No se pudo determinar el mejor candidato anti-popular. Devolviendo uno aleatorio.")
            return self.random_model.generate_combination()


def main():
    print("--- Demostración de Estrategias de Generación de Números ---")

    print("\n1. Modelo Aleatorio Uniforme:")
    uniform_model = UniformRandomModel()
    for i in range(3):
        main, stars = uniform_model.generate_combination()
        print(f"  Ticket {i+1}: Números: {main}, Estrellas: {stars}")

    print("\n2. Modelo de Tendencia Histórica:")
    # Usará los datos simulados de euromillions_history_cleaned.parquet
    # Con datos simulados, las probabilidades pueden no ser muy significativas.
    historical_model = HistoricalTrendModel()
    if not historical_model.historical_df.empty:
        # print("Probabilidades principales (muestra):", historical_model.main_probs.head())
        # print("Probabilidades estrellas (muestra):", historical_model.star_probs.head())
        for i in range(3):
            main, stars = historical_model.generate_combination()
            print(f"  Ticket {i+1}: Números: {main}, Estrellas: {stars}")
    else:
        print("  No se pudieron cargar datos históricos para el modelo de tendencia.")


    print("\n3. Modelo Anti-Popular:")
    # Este modelo depende de 'popularity_analyser.py'
    # y de que 'get_combination_popularity' esté correctamente importado.
    anti_popular_model = AntiPopularModel(num_candidates=500) # 500 para rapidez en demo
    for i in range(3):
        main, stars = anti_popular_model.generate_combination()
        # Para verificar, podríamos calcular su popularidad aquí
        try:
            pop_score = get_combination_popularity(main, stars)
            print(f"  Ticket {i+1}: Números: {main}, Estrellas: {stars} (Popularidad: {pop_score})")
        except Exception as e:
             print(f"  Ticket {i+1}: Números: {main}, Estrellas: {stars} (Error al obtener popularidad: {e})")


if __name__ == "__main__":
    main()
