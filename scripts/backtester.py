import pandas as pd
import numpy as np
from collections import defaultdict

# Importar estrategias y modelos
try:
    from number_strategies import UniformRandomModel, HistoricalTrendModel, AntiPopularModel
    from popularity_analyser import get_combination_popularity # Para mostrar popularidad si es relevante
    STRATEGIES_TO_TEST = {
        "random": UniformRandomModel,
        "historical": HistoricalTrendModel,
        "antipopular": AntiPopularModel
    }
    print("Estrategias y analizador de popularidad importados correctamente.")
except ImportError as e:
    print(f"Error importando módulos: {e}. Asegúrate que los scripts estén accesibles.")
    STRATEGIES_TO_TEST = {} # Evitar crash

# Columnas de números y estrellas en el archivo histórico
NUMBER_COLS_HIST = ['N1', 'N2', 'N3', 'N4', 'N5']
STAR_COLS_HIST = ['E1', 'E2']

def load_historical_draws(file_path="data/euromillions_history_cleaned.parquet"):
    """Carga los sorteos históricos limpios."""
    try:
        df = pd.read_parquet(file_path)
        # Asegurar que DrawDate es datetime y ordenar por fecha para simulación cronológica
        df['DrawDate'] = pd.to_datetime(df['DrawDate'])
        df.sort_values(by='DrawDate', ascending=True, inplace=True)
        print(f"Sorteos históricos cargados desde {file_path}: {len(df)} registros.")
        return df
    except FileNotFoundError:
        print(f"Error: El archivo histórico {file_path} no fue encontrado.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error cargando datos históricos: {e}")
        return pd.DataFrame()

def compare_ticket_with_draw(ticket_main, ticket_stars, draw_main, draw_stars):
    """
    Compara un boleto generado con un sorteo real.
    Retorna (aciertos_main, aciertos_stars).
    """
    aciertos_main = len(set(ticket_main) & set(draw_main))
    aciertos_stars = len(set(ticket_stars) & set(draw_stars))
    return aciertos_main, aciertos_stars

def run_backtest(historical_draws, strategies, num_tickets_per_draw=1, antipopular_candidates=200):
    """
    Ejecuta el back-testing para las estrategias dadas.
    - historical_draws: DataFrame con los sorteos históricos.
    - strategies: Diccionario de estrategias a probar.
    - num_tickets_per_draw: Cuántos boletos generar por estrategia para cada sorteo histórico.
    - antipopular_candidates: Número de candidatos para la estrategia antipopular.
    """
    if historical_draws.empty:
        print("No hay datos históricos para el back-testing.")
        return None

    results = {} # { 'strategy_name': {'hits_distribution': defaultdict(int), 'details': []} }

    for strategy_name, StrategyModelClass in strategies.items():
        print(f"\nProbando estrategia: {strategy_name}...")

        # Instanciar el modelo
        # For HistoricalTrendModel, it's initialized once here with all historical data by default.
        # For a step-by-step retraining, this instantiation would need to be inside the loop
        # or the model would need an update method.
        if strategy_name == "antipopular":
            model = StrategyModelClass(num_candidates=antipopular_candidates)
        elif strategy_name == "historical":
            # Initialize with full data for now, or pass specific data if model supports it
             model = StrategyModelClass(historical_data_path="data/euromillions_history_cleaned.parquet")
        else:
            model = StrategyModelClass()


        current_strategy_results = {
            'hits_distribution': defaultdict(int), # (main_hits, star_hits) -> count
            'minor_hits_summary': defaultdict(int), # '2+0', '2+1', etc. -> count
            'details': [] # Lista de tuplas (draw_date, ticket_main, ticket_stars, main_hits, star_hits)
        }

        for index, draw_row in historical_draws.iterrows():
            draw_date = draw_row['DrawDate']
            actual_main_numbers = draw_row[NUMBER_COLS_HIST].values.tolist()
            actual_stars = draw_row[STAR_COLS_HIST].values.tolist()

            # Model re-training logic for HistoricalTrendModel for a more rigorous backtest
            # This section would replace the single initialization of 'model' above for 'historical'
            current_model = model
            if strategy_name == "historical":
                if index == 0: # First draw, no prior data to train on for this specific draw
                    # Generate randomly or skip, as no historical data *before* this draw to train on.
                    # For simplicity, we'll use the model trained on all data, which is not ideal for the first draw.
                    # Or, we could use a UniformRandom for the very first draw if no history.
                    pass # Uses the model trained on all data
                else:
                    # Create a temporary model instance trained only on data up to the previous draw
                    # This is computationally more expensive.
                    temp_historical_df_for_training = historical_draws.iloc[:index].copy()
                    if not temp_historical_df_for_training.empty:
                        # Need to ensure the HistoricalTrendModel can be initialized with a DataFrame directly
                        # or can be updated. Assuming it re-evaluates its probs if historical_df is changed.
                        # This requires HistoricalTrendModel to have a flexible init or an update method.
                        # For now, the HistoricalTrendModel in number_strategies.py initializes from file or uses passed df.
                        # Let's assume we can re-initialize it (path=None, df=temp_df)
                        # This path is not fully implemented here due to model design;
                        # Current HistoricalTrendModel loads ALL data from file in __init__.
                        # A true backtest would need:
                        # current_model = StrategyModelClass(historical_data_df=temp_historical_df_for_training)
                        # This part is a placeholder for the more rigorous approach:
                        pass # Fallbacks to using the model trained once with all data.


            for _ in range(num_tickets_per_draw):
                generated_main, generated_stars = current_model.generate_combination()

                main_hits, star_hits = compare_ticket_with_draw(generated_main, generated_stars, actual_main_numbers, actual_stars)

                current_strategy_results['hits_distribution'][(main_hits, star_hits)] += 1
                current_strategy_results['details'].append({
                    'date': draw_date,
                    'ticket_main': generated_main,
                    'ticket_stars': generated_stars,
                    'actual_main': actual_main_numbers,
                    'actual_stars': actual_stars,
                    'main_hits': main_hits,
                    'star_hits': star_hits
                })

                hit_key = f"{main_hits}+{star_hits}"
                current_strategy_results['minor_hits_summary'][hit_key] += 1

        results[strategy_name] = current_strategy_results
        print(f"Estrategia {strategy_name} probada. Total de boletos simulados: {len(historical_draws) * num_tickets_per_draw}")

    return results

def print_results(backtest_results, historical_draws_count, num_tickets_per_draw):
    if not backtest_results:
        print("No hay resultados de back-testing para mostrar.")
        return

    total_simulated_tickets_overall = historical_draws_count * num_tickets_per_draw

    print("\n--- Resultados del Back-testing ---")
    print(f"Número total de sorteos históricos en el análisis: {historical_draws_count}")
    print(f"Número de boletos simulados por sorteo por estrategia: {num_tickets_per_draw}")

    for strategy_name, res_data in backtest_results.items():
        print(f"\nResultados para la Estrategia: {strategy_name.upper()}")

        total_tickets_for_strategy = len(res_data['details']) # Should be historical_draws_count * num_tickets_per_draw

        print("  Distribución de Aciertos (Aciertos Principales + Aciertos Estrella):")
        if not res_data['minor_hits_summary']:
            print("    No se registraron aciertos.")
        else:
            sorted_hits = sorted(res_data['minor_hits_summary'].items(), key=lambda item: (int(item[0].split('+')[0]), int(item[0].split('+')[1])), reverse=True)
            for (hit_type, count) in sorted_hits:
                 percentage = (count / total_tickets_for_strategy) * 100
                 print(f"    {hit_type}: {count} veces ({percentage:.2f}%)")

        at_least_2_plus_0 = 0
        for (main_hits, star_hits), count in res_data['hits_distribution'].items():
            if main_hits >= 2:
                at_least_2_plus_0 += count

        if total_tickets_for_strategy > 0:
            percentage_at_least_2_plus_0 = (at_least_2_plus_0 / total_tickets_for_strategy) * 100
            print(f"  Tasa de aciertos de al menos 2 números principales: {percentage_at_least_2_plus_0:.2f}% ({at_least_2_plus_0} veces de {total_tickets_for_strategy} boletos)")
        else:
            print("  No hay boletos simulados para calcular tasas de acierto.")

    print("\n--- Consideraciones sobre 'Análisis de Premio Compartido (Hipotético)' ---")
    print("Para realizar un análisis de premio compartido, necesitaríamos datos históricos sobre:")
    print("1. El número de ganadores para cada categoría de premio en cada sorteo.")
    print("2. Los montos de los premios para cada categoría.")
    print("Con esos datos, para cada 'acierto simulado' significativo, podríamos comparar:")
    print("  - Si el boleto generado (especialmente con 'antipopular') es menos común que los boletos ganadores reales (si esa info existiera).")
    print("  - Estimar si el premio hipotético hubiera sido mayor debido a menos ganadores compartiendo el pozo.")
    print("Actualmente, nuestros datos simulados no incluyen esta información, por lo que este análisis es solo conceptual aquí.")


def main():
    print("Iniciando Back-testing de Estrategias de EuroMillions...")

    if not STRATEGIES_TO_TEST:
        print("Error crítico: No hay estrategias disponibles para probar. Abortando.")
        return

    historical_data = load_historical_draws()
    if historical_data.empty:
        print("No se pueden ejecutar pruebas sin datos históricos.")
        return

    num_tickets_simulated_per_draw = 1
    antipop_candidates = 200

    results = run_backtest(historical_data, STRATEGIES_TO_TEST, num_tickets_simulated_per_draw, antipop_candidates)

    print_results(results, len(historical_data), num_tickets_simulated_per_draw)

    print("\nBack-testing completado.")

if __name__ == "__main__":
    main()
