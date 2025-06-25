import pandas as pd
from scipy.stats import chisquare
import numpy as np

# Columnas de números y estrellas (consistente con process_euromillions_data.py)
NUMBER_COLS = ['N1', 'N2', 'N3', 'N4', 'N5']
STAR_COLS = ['E1', 'E2']

# Rangos para números y estrellas
MIN_MAIN_NUMBER = 1
MAX_MAIN_NUMBER = 50
MIN_STAR_NUMBER = 1
MAX_STAR_NUMBER = 12

def load_cleaned_data(file_path="data/euromillions_history_cleaned.parquet"):
    """Carga los datos limpios desde el archivo Parquet."""
    try:
        df = pd.read_parquet(file_path)
        print(f"Datos cargados exitosamente desde {file_path}")
        return df
    except FileNotFoundError:
        print(f"Error: El archivo {file_path} no fue encontrado. Ejecuta primero el script de procesamiento.")
        return pd.DataFrame() # Devuelve DataFrame vacío para evitar errores posteriores
    except Exception as e:
        print(f"Error cargando datos: {e}")
        return pd.DataFrame()

def calculate_observed_frequencies(df, columns, min_val, max_val):
    """Calcula las frecuencias observadas para los números en las columnas dadas."""
    all_numbers = []
    for col in columns:
        all_numbers.extend(df[col].tolist())

    observed_counts = pd.Series(all_numbers).value_counts().sort_index()

    # Asegurar que todos los números en el rango estén presentes, con cuenta 0 si no aparecieron
    full_range_counts = pd.Series(index=range(min_val, max_val + 1), dtype='int64').fillna(0)
    observed_frequencies = full_range_counts.add(observed_counts, fill_value=0)

    return observed_frequencies

def perform_chi_squared_test(observed_frequencies, total_draws, num_categories_in_draw, category_range_size):
    """
    Realiza el test de Chi-cuadrado.
    - observed_frequencies: Serie de pandas con las cuentas observadas para cada número.
    - total_draws: Número total de sorteos en los datos.
    - num_categories_in_draw: Cuántos números de esta categoría se sortean por evento (e.g., 5 para principales, 2 para estrellas).
    - category_range_size: El tamaño total del rango del que se eligen los números (e.g., 50 para principales, 12 para estrellas).
    """
    if observed_frequencies.sum() == 0: # No hay datos
        print("No hay datos observados para realizar el test.")
        return np.nan, np.nan

    # La frecuencia esperada para cada número es el total de números sorteados dividido por el rango posible.
    # Total de números sorteados = total_draws * num_categories_in_draw
    total_numbers_drawn = total_draws * num_categories_in_draw
    expected_frequency_per_number = total_numbers_drawn / category_range_size

    # Las frecuencias esperadas para el test de chi-cuadrado deben ser un array del mismo tamaño que observed_frequencies
    expected_frequencies = np.full(len(observed_frequencies), expected_frequency_per_number)

    # Realizar el test. f_obs son las cuentas, f_exp son las esperadas.
    chi2_stat, p_value = chisquare(f_obs=observed_frequencies, f_exp=expected_frequencies)

    return chi2_stat, p_value

def main():
    """Orquesta el análisis de frecuencias."""
    print("Iniciando análisis de frecuencias con Test Chi-cuadrado...")
    df = load_cleaned_data()

    if df.empty:
        print("No se pudieron cargar los datos. Abortando análisis.")
        return

    num_draws = len(df)
    print(f"Número total de sorteos analizados: {num_draws}")

    if num_draws == 0:
        print("No hay sorteos en los datos para analizar.")
        return

    # Análisis para números principales
    print("\n--- Análisis de Números Principales (1-50) ---")
    observed_main_numbers = calculate_observed_frequencies(df, NUMBER_COLS, MIN_MAIN_NUMBER, MAX_MAIN_NUMBER)
    print("Frecuencias Observadas (Números Principales):")
    print(observed_main_numbers)

    if observed_main_numbers.sum() > 0 :
        chi2_main, p_main = perform_chi_squared_test(observed_main_numbers, num_draws, len(NUMBER_COLS), MAX_MAIN_NUMBER)
        print(f"Estadístico Chi-cuadrado (Números Principales): {chi2_main:.4f}")
        print(f"Valor P (Números Principales): {p_main:.4f}")
        alpha = 0.05
        if p_main < alpha:
            print(f"Conclusión (Números Principales): Se rechaza la hipótesis nula (p < {alpha}). La distribución de los números principales NO parece ser uniforme.")
        else:
            print(f"Conclusión (Números Principales): No se puede rechazar la hipótesis nula (p >= {alpha}). La distribución de los números principales SÍ parece ser uniforme.")
    else:
        print("No hay datos de números principales para analizar.")

    # Análisis para números estrella
    print("\n--- Análisis de Números Estrella (1-12) ---")
    observed_stars = calculate_observed_frequencies(df, STAR_COLS, MIN_STAR_NUMBER, MAX_STAR_NUMBER)
    print("Frecuencias Observadas (Estrellas):")
    print(observed_stars)

    if observed_stars.sum() > 0:
        chi2_star, p_star = perform_chi_squared_test(observed_stars, num_draws, len(STAR_COLS), MAX_STAR_NUMBER)
        print(f"Estadístico Chi-cuadrado (Estrellas): {chi2_star:.4f}")
        print(f"Valor P (Estrellas): {p_star:.4f}")
        alpha = 0.05
        if p_star < alpha:
            print(f"Conclusión (Estrellas): Se rechaza la hipótesis nula (p < {alpha}). La distribución de las estrellas NO parece ser uniforme.")
        else:
            print(f"Conclusión (Estrellas): No se puede rechazar la hipótesis nula (p >= {alpha}). La distribución de las estrellas SÍ parece ser uniforme.")
    else:
        print("No hay datos de estrellas para analizar.")

    print("\nAnálisis de frecuencias completado.")

if __name__ == "__main__":
    main()
