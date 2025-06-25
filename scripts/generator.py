import argparse

# Intentar importar las estrategias. Asumimos que number_strategies.py está en el mismo directorio.
try:
    from number_strategies import UniformRandomModel, HistoricalTrendModel, AntiPopularModel
    STRATEGIES_AVAILABLE = {
        "random": UniformRandomModel,
        "historical": HistoricalTrendModel,
        "antipopular": AntiPopularModel
    }
    print("Estrategias importadas correctamente.")
except ImportError as e:
    print(f"Error al importar estrategias desde number_strategies: {e}")
    print("Asegúrate de que 'number_strategies.py' esté en el mismo directorio o en el PYTHONPATH.")
    # Fallback si la importación falla para que el script no se rompa al definir argparse
    STRATEGIES_AVAILABLE = {}


def parse_arguments():
    """Parsea los argumentos de la línea de comandos."""
    parser = argparse.ArgumentParser(description="Generador de combinaciones de EuroMillions usando diversas estrategias.")

    parser.add_argument(
        "-n", "--num_tickets",
        type=int,
        default=10,
        help="Número de boletos a generar (por defecto: 10)."
    )

    parser.add_argument(
        "-s", "--strategy",
        type=str,
        default="antipopular",
        choices=list(STRATEGIES_AVAILABLE.keys()) if STRATEGIES_AVAILABLE else ['random', 'historical', 'antipopular'], # Evitar error si STRATEGIES_AVAILABLE está vacío
        help="Estrategia de generación a utilizar (por defecto: antipopular)."
    )

    parser.add_argument(
        "--candidates_antipopular",
        type=int,
        default=1000,
        help="Número de candidatos a generar para la estrategia antipopular (por defecto: 1000)."
    )

    # Podríamos añadir argumentos para el HistoricalTrendModel como decay_factor si quisiéramos
    # parser.add_argument("--decay", type=float, default=0.995, help="Factor de decaimiento para el modelo histórico.")

    return parser.parse_args()

def main():
    """Función principal para generar y mostrar los boletos."""
    args = parse_arguments()

    if not STRATEGIES_AVAILABLE:
        print("Error crítico: No se pudieron cargar las estrategias de generación. Abortando.")
        return

    print(f"Generando {args.num_tickets} boleto(s) usando la estrategia '{args.strategy}'.")

    StrategyModel = STRATEGIES_AVAILABLE.get(args.strategy)
    if not StrategyModel: # Should not happen if choices are properly set from STRATEGIES_AVAILABLE.keys()
        print(f"Error: Estrategia '{args.strategy}' no reconocida. Usando 'random' por defecto.")
        StrategyModel = UniformRandomModel # Fallback, though argparse choices should prevent this.

    # Instanciar el modelo. Pasar argumentos específicos del modelo si es necesario.
    if args.strategy == "antipopular":
        model = StrategyModel(num_candidates=args.candidates_antipopular)
    # elif args.strategy == "historical":
    #     model = StrategyModel(decay_factor=args.decay) # Ejemplo si añadiéramos el arg --decay
    else:
        model = StrategyModel()

    print("\n--- Boletos Generados ---")
    for i in range(args.num_tickets):
        main_numbers, stars = model.generate_combination()
        # Formatear para mejor lectura
        main_str = ", ".join(map(str, sorted(main_numbers)))
        stars_str = ", ".join(map(str, sorted(stars)))
        print(f"Boleto {i+1:02d}: Números: [{main_str}] - Estrellas: [{stars_str}]")

        # Si es antipopular, podríamos opcionalmente mostrar su score de popularidad
        if args.strategy == "antipopular":
            try:
                # Intentar importar get_combination_popularity aquí, por si number_strategies no lo hizo
                # o para mantener la lógica de visualización separada.
                from popularity_analyser import get_combination_popularity
                pop_score = get_combination_popularity(main_numbers, stars)
                print(f"             (Popularidad: {pop_score})")
            except ImportError:
                # Esto podría pasar si popularity_analyser.py no está accesible
                print("             (Advertencia: No se pudo calcular la popularidad - módulo no encontrado)")
            except Exception as e:
                print(f"             (Error al obtener popularidad: {e})")


    print("\nGeneración completada.")

if __name__ == "__main__":
    main()
