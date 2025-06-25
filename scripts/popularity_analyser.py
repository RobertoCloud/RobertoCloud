import numpy as np

# --- Parámetros de Popularidad (Ajustables) ---

# Números principales (1-50)
POPULARITY_THRESHOLD_DAY = 31
POPULARITY_SCORE_IS_DAY = 10  # Puntos extra si es un día del mes
POPULARITY_SCORE_VERY_LOW_NUMBER = 5 # Puntos extra para números muy bajos (e.g. <= 10)
POPULARITY_SCORE_SINGLE_DIGIT = 3 # Puntos extra si es de un solo dígito (1-9)

# Estrellas (1-12)
STAR_POPULARITY_SCORE_LOW = 5 # Puntos extra para estrellas bajas (e.g. <=6)

# Combinaciones (lista de 5 números principales, lista de 2 estrellas)
COMBO_MAX_DAYS_THRESHOLD = 3 # Más de X números <=31 en la combo principal añade popularidad
COMBO_MAX_DAYS_PENALTY = 20 # Penalización por exceso de "días"

COMBO_ARITHMETIC_SEQUENCE_PENALTY = 15 # Penalización por secuencias aritméticas
COMBO_ALL_EVEN_ODD_PENALTY = 10 # Penalización si todos los números son pares o impares

# --- Funciones de Cálculo de Popularidad ---

def get_number_popularity(number, is_star=False):
    """Calcula el índice de popularidad para un número individual."""
    score = 0
    if is_star:
        if number <= 6:
            score += STAR_POPULARITY_SCORE_LOW
    else: # Número principal
        if number <= POPULARITY_THRESHOLD_DAY:
            score += POPULARITY_SCORE_IS_DAY
        if number <= 10:
            score += POPULARITY_SCORE_VERY_LOW_NUMBER
        if number <= 9:
            score += POPULARITY_SCORE_SINGLE_DIGIT
    return score

def get_combination_popularity(main_numbers, stars):
    """
    Calcula el índice de popularidad para una combinación completa.
    Un score más alto significa MÁS popular (y por ende, menos deseable para la estrategia anti-popular).
    """
    combo_score = 0

    # 1. Suma de popularidad de números individuales
    for num in main_numbers:
        combo_score += get_number_popularity(num, is_star=False)
    for star in stars:
        combo_score += get_number_popularity(star, is_star=True)

    # 2. Penalización por demasiados números "día" (<=31)
    day_numbers_count = sum(1 for num in main_numbers if num <= POPULARITY_THRESHOLD_DAY)
    if day_numbers_count > COMBO_MAX_DAYS_THRESHOLD:
        combo_score += COMBO_MAX_DAYS_PENALTY

    # 3. Penalización por secuencias aritméticas (simple: diferencia constante)
    # Ordenar primero para chequear secuencia
    sorted_main = sorted(main_numbers)
    if len(sorted_main) >= 3: # Necesitamos al menos 3 números para una secuencia simple
        diffs = np.diff(sorted_main)
        if len(set(diffs)) == 1: # Todas las diferencias son iguales
             combo_score += COMBO_ARITHMETIC_SEQUENCE_PENALTY
        # Podríamos añadir chequeos de secuencias más complejas aquí (ej. Fibonacci, etc.)

    # 4. Penalización si todos los números principales son pares o todos impares
    num_even = sum(1 for num in main_numbers if num % 2 == 0)
    num_odd = sum(1 for num in main_numbers if num % 2 != 0)
    if num_even == len(main_numbers) or num_odd == len(main_numbers):
        combo_score += COMBO_ALL_EVEN_ODD_PENALTY

    # Podríamos añadir más heurísticas:
    # - Patrones en el boleto (más difícil, requiere layout)
    # - Suma total de los números (gente tiende a evitar sumas muy altas o muy bajas)
    # - Repetición de dígitos finales, etc.

    return combo_score

def main():
    """Ejemplos de uso del analizador de popularidad."""
    print("--- Analizador de Popularidad de Números y Combinaciones ---")

    print("\nEjemplos de popularidad de números individuales (principales):")
    for i in [1, 7, 15, 31, 32, 48]:
        print(f"Popularidad del número {i}: {get_number_popularity(i)}")

    print("\nEjemplos de popularidad de estrellas:")
    for i in [1, 6, 7, 12]:
        print(f"Popularidad de la estrella {i}: {get_number_popularity(i, is_star=True)}")

    print("\nEjemplos de popularidad de combinaciones:")

    combo1_main = [1, 2, 3, 4, 5] # Muy popular: secuencia, muchos días, todos impares/pares (depende)
    combo1_stars = [1, 2]
    pop1 = get_combination_popularity(combo1_main, combo1_stars)
    print(f"Combinación {combo1_main} / {combo1_stars} - Popularidad: {pop1}")

    combo2_main = [7, 14, 21, 28, 35] # Popular: secuencia, múltiples de 7
    combo2_stars = [7, 11]
    pop2 = get_combination_popularity(combo2_main, combo2_stars)
    print(f"Combinación {combo2_main} / {combo2_stars} - Popularidad: {pop2}")

    combo3_main = [10, 20, 30, 40, 50] # Popular: secuencia
    combo3_stars = [3, 9]
    pop3 = get_combination_popularity(combo3_main, combo3_stars)
    print(f"Combinación {combo3_main} / {combo3_stars} - Popularidad: {pop3}")

    combo4_main = [5, 18, 23, 37, 48] # Menos obviamente popular
    combo4_stars = [4, 11]
    pop4 = get_combination_popularity(combo4_main, combo4_stars)
    print(f"Combinación {combo4_main} / {combo4_stars} - Popularidad: {pop4}")

    combo5_main = [1, 12, 21, 31, 42] # mezcla de "días"
    combo5_stars = [5, 10]
    pop5 = get_combination_popularity(combo5_main, combo5_stars)
    print(f"Combinación {combo5_main} / {combo5_stars} - Popularidad: {pop5}")

    # Combinación con todos pares
    combo6_main = [2, 4, 6, 8, 10]
    combo6_stars = [2, 4]
    pop6 = get_combination_popularity(combo6_main, combo6_stars)
    print(f"Combinación {combo6_main} / {combo6_stars} - Popularidad: {pop6}")


if __name__ == "__main__":
    main()
