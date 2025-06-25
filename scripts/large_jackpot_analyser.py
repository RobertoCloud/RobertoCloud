import pandas as pd
import numpy as np
from scipy.stats import chi2_contingency, mannwhitneyu

# Columnas de números y estrellas (consistente con process_euromillions_data.py)
NUMBER_COLS = ['N1', 'N2', 'N3', 'N4', 'N5']
STAR_COLS = ['E1', 'E2']
JACKPOT_THRESHOLD = 150_000_000 # 150 Millones

# Importar funciones de análisis de frecuencia si es necesario o redefinirlas
# Para este script, podríamos reusar o adaptar partes de analyse_frequencies.py
# Por simplicidad, algunas funciones básicas de conteo se pueden redefinir aquí.

def load_cleaned_data_with_jackpot(file_path="data/euromillions_history_cleaned.parquet"):
    """Carga los datos limpios que incluyen la columna 'Jackpot'."""
    try:
        df = pd.read_parquet(file_path)
        if 'Jackpot' not in df.columns:
            print(f"Error: La columna 'Jackpot' no se encuentra en {file_path}.")
            return pd.DataFrame()
        # Asegurar que DrawDate es datetime y Jackpot es numérico
        df['DrawDate'] = pd.to_datetime(df['DrawDate'])
        df['Jackpot'] = pd.to_numeric(df['Jackpot'], errors='coerce')
        df.dropna(subset=['Jackpot'], inplace=True) # Quitar filas donde el Jackpot no es numérico
        print(f"Datos cargados desde {file_path}: {len(df)} registros con Jackpot válido.")
        return df
    except FileNotFoundError:
        print(f"Error: El archivo {file_path} no fue encontrado.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error cargando datos: {e}")
        return pd.DataFrame()

def get_all_numbers(df, columns):
    """Extrae todos los números de las columnas especificadas en una lista."""
    all_numbers = []
    for col in columns:
        all_numbers.extend(df[col].tolist())
    return all_numbers

def compare_number_distributions(df_group1, df_group2, value_cols, group1_name, group2_name, min_val, max_val):
    """
    Compara las distribuciones de números entre dos grupos de sorteos.
    Usa Chi-cuadrado sobre tablas de contingencia de frecuencias.
    """
    numbers_group1 = get_all_numbers(df_group1, value_cols)
    numbers_group2 = get_all_numbers(df_group2, value_cols)

    if not numbers_group1 or not numbers_group2:
        print(f"No hay suficientes datos en uno o ambos grupos para comparar {value_cols[0][:-1]}.")
        return

    counts_group1 = pd.Series(numbers_group1).value_counts().reindex(range(min_val, max_val + 1), fill_value=0)
    counts_group2 = pd.Series(numbers_group2).value_counts().reindex(range(min_val, max_val + 1), fill_value=0)

    # Tabla de contingencia: [grupo1_counts, grupo2_counts]
    contingency_table = pd.DataFrame({group1_name: counts_group1, group2_name: counts_group2})
    print(f"\nTabla de contingencia para {value_cols[0][:-1]}s ({group1_name} vs {group2_name}):")
    print(contingency_table.T) # Transponer para mejor visualización de grupos como filas

    try:
        chi2, p, dof, expected = chi2_contingency(contingency_table)
        print(f"Test Chi-cuadrado de independencia ({value_cols[0][:-1]}s):")
        print(f"  Estadístico Chi2: {chi2:.4f}, Valor-p: {p:.4f}, Grados de libertad: {dof}")
        alpha = 0.05
        if p < alpha:
            print(f"  Conclusión: Se rechaza la hipótesis nula (p < {alpha}). Hay una diferencia estadísticamente significativa en la distribución de {value_cols[0][:-1]}s entre los grupos.")
        else:
            print(f"  Conclusión: No se puede rechazar la hipótesis nula (p >= {alpha}). No hay evidencia de diferencia significativa en la distribución de {value_cols[0][:-1]}s.")
    except ValueError as e:
        # Esto puede pasar si una de las series está vacía o tiene ceros en todos lados
        print(f"No se pudo realizar el test Chi-cuadrado para {value_cols[0][:-1]}s: {e}")
        print("Esto puede ser debido a muy pocos datos o nula varianza en las frecuencias.")


def compare_mean_popularity_of_winning_numbers(df_group1, df_group2, group1_name, group2_name):
    """
    (CONCEPTUAL) Compara la popularidad media de las combinaciones ganadoras.
    Esto requeriría que 'get_combination_popularity' esté disponible y sea aplicable
    a las combinaciones GANADORAS, no a las generadas.
    """
    print(f"\nAnálisis Conceptual: Popularidad de Combinaciones GANADORAS ({group1_name} vs {group2_name})")
    try:
        from popularity_analyser import get_combination_popularity

        pop_scores_g1 = []
        for _, row in df_group1.iterrows():
            main_nums = row[NUMBER_COLS].tolist()
            star_nums = row[STAR_COLS].tolist()
            pop_scores_g1.append(get_combination_popularity(main_nums, star_nums))

        pop_scores_g2 = []
        for _, row in df_group2.iterrows():
            main_nums = row[NUMBER_COLS].tolist()
            star_nums = row[STAR_COLS].tolist()
            pop_scores_g2.append(get_combination_popularity(main_nums, star_nums))

        if not pop_scores_g1 or not pop_scores_g2:
            print("  No hay suficientes datos para comparar la popularidad de las combinaciones ganadoras.")
            return

        mean_pop_g1 = np.mean(pop_scores_g1)
        mean_pop_g2 = np.mean(pop_scores_g2)
        print(f"  Popularidad Media Estimada (Combinaciones Ganadoras) - {group1_name}: {mean_pop_g1:.2f}")
        print(f"  Popularidad Media Estimada (Combinaciones Ganadoras) - {group2_name}: {mean_pop_g2:.2f}")

        # Test de Mann-Whitney U para ver si las medianas de popularidad son diferentes
        # (más robusto que t-test si las distribuciones no son normales)
        try:
            # alternative='two-sided' es el default, pero lo ponemos explícito.
            # continuity correction es True por default, lo cual es generalmente bueno para muestras pequeñas.
            u_stat, p_value_mw = mannwhitneyu(pop_scores_g1, pop_scores_g2, alternative='two-sided', use_continuity=True)
            print(f"  Test de Mann-Whitney U (Popularidad Ganadora): U-stat={u_stat:.2f}, p-value={p_value_mw:.4f}")
            alpha = 0.05
            if p_value_mw < alpha:
                print(f"  Conclusión: Hay una diferencia estadísticamente significativa en la popularidad media de las combinaciones GANADORAS entre los grupos.")
            else:
                print(f"  Conclusión: No hay evidencia de diferencia significativa en la popularidad media de las combinaciones GANADORAS.")
        except ValueError as e_mw: # Puede ocurrir si una muestra es muy pequeña o no hay varianza.
             print(f"  No se pudo realizar el test de Mann-Whitney U: {e_mw}")


    except ImportError:
        print("  'popularity_analyser' no disponible. No se puede realizar este análisis conceptual.")
    except Exception as e:
        print(f"  Error durante el análisis conceptual de popularidad: {e}")


def main():
    print("Iniciando Análisis de Comportamiento en Botes Grandes (>150M €)...")
    df = load_cleaned_data_with_jackpot()

    if df.empty or len(df) < 2: # Necesitamos al menos algunos datos para comparar
        print("No hay suficientes datos históricos con información de Jackpot para el análisis.")
        return

    large_jackpot_draws = df[df['Jackpot'] > JACKPOT_THRESHOLD].copy() # Usar .copy() para evitar SettingWithCopyWarning
    normal_jackpot_draws = df[df['Jackpot'] <= JACKPOT_THRESHOLD].copy()

    print(f"Número de sorteos con bote > {JACKPOT_THRESHOLD/1e6:.0f}M €: {len(large_jackpot_draws)}")
    print(f"Número de sorteos con bote <= {JACKPOT_THRESHOLD/1e6:.0f}M €: {len(normal_jackpot_draws)}")

    if len(large_jackpot_draws) == 0 or len(normal_jackpot_draws) == 0:
        print("No hay suficientes datos en uno o ambos grupos (bote grande/normal) para realizar la comparación.")
        print("Con los datos simulados actuales, es posible que no haya suficientes sorteos en ambas categorías.")
        # Si solo hay un grupo, podríamos mostrar sus estadísticas descriptivas, pero no comparar.
        if not large_jackpot_draws.empty:
            print("\nEstadísticas solo para sorteos de Bote Grande:")
            print(large_jackpot_draws[NUMBER_COLS + STAR_COLS + ['Jackpot']].describe())
        if not normal_jackpot_draws.empty:
            print("\nEstadísticas solo para sorteos de Bote Normal:")
            print(normal_jackpot_draws[NUMBER_COLS + STAR_COLS + ['Jackpot']].describe())
        return

    # Comparar distribuciones de números principales
    compare_number_distributions(large_jackpot_draws, normal_jackpot_draws, NUMBER_COLS, "Bote Grande", "Bote Normal", 1, 50)

    # Comparar distribuciones de estrellas
    compare_number_distributions(large_jackpot_draws, normal_jackpot_draws, STAR_COLS, "Bote Grande", "Bote Normal", 1, 12)

    # Comparar (conceptualmente) la popularidad de las combinaciones GANADORAS
    compare_mean_popularity_of_winning_numbers(large_jackpot_draws, normal_jackpot_draws, "Bote Grande", "Bote Normal")

    print("\n--- Discusión de Limitaciones ---")
    print("Este análisis se basa en las frecuencias de los NÚMEROS GANADORES.")
    print("Una diferencia en estas frecuencias NO implica directamente un cambio en el COMPORTAMIENTO DEL JUGADOR,")
    print("ya que los sorteos son aleatorios. Sin embargo, si los números ganadores en botes grandes")
    print("tendieran a ser, por ejemplo, de menor valor (más 'fechas de cumpleaños'), podría ser un indicio indirecto")
    print("de que más gente jugó ese tipo de combinaciones, y por ende, una de ellas resultó ganadora.")
    print("Un análisis más directo del comportamiento del jugador requeriría datos sobre las apuestas realizadas,")
    print("los cuales no están públicamente disponibles.")
    print("Con los datos simulados actuales (pocos registros), es improbable obtener resultados estadísticamente significativos.")

    print("\nAnálisis de Botes Grandes completado.")

if __name__ == "__main__":
    main()
