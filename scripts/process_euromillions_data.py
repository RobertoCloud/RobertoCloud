import pandas as pd
import numpy as np # Importado para usar np.nan
from datetime import datetime

# Simulación de datos como estarían en un CSV de origen, AHORA CON JACKPOT
SIMULATED_RAW_DATA = {
    'DrawDate': ['10/01/2020', '17/01/2020', '24/01/2020', '31/01/2020', '07/02/2020', None, '14/02/2020', '21/02/2020'],
    'N1': [5, 10, 15, 20, 25, 30, 1, 8],
    'N2': [12, 18, 22, 28, 33, 38, 2, 18],
    'N3': [20, 25, 30, 35, 40, 45, 3, 28],
    'N4': [30, 38, 42, 45, 48, 49, 4, 38],
    'N5': [40, 45, 48, 50, 3, 4, 5, 48],
    'E1': [1, 3, 5, 7, 9, 10, 2, 6],
    'E2': [2, 6, 8, 10, 11, None, 4, 12],
    'Jackpot': [50000000, 60000000, 160000000, 75000000, 180000000, 20000000, 200000000, 90000000] # Ejemplo de Jackpots
}

# Columnas esperadas para los números y estrellas
NUMBER_COLS = ['N1', 'N2', 'N3', 'N4', 'N5']
STAR_COLS = ['E1', 'E2']

def load_raw_data_from_source(file_path=None):
    """
    Carga datos crudos. Si file_path es None, usa datos simulados.
    En un caso real, esto leería de un CSV, API, etc.
    """
    if file_path:
        print(f"Simulando carga desde {file_path}")
        # df = pd.read_csv(file_path, parse_dates=['DrawDate']) # Ejemplo real
        df = pd.DataFrame(SIMULATED_RAW_DATA) # Para prueba con path, usamos simulado
    else:
        print("Usando datos simulados internos.")
        df = pd.DataFrame(SIMULATED_RAW_DATA)
    return df

def clean_data(df):
    """
    Limpia los datos:
    - Convierte DrawDate a datetime.
    - Asegura que los números y estrellas sean enteros.
    - Procesa la columna Jackpot.
    - Maneja valores faltantes.
    """
    df_cleaned = df.copy()

    # Manejar fechas
    df_cleaned['DrawDate'] = pd.to_datetime(df_cleaned['DrawDate'], errors='coerce', dayfirst=True)
    df_cleaned.dropna(subset=['DrawDate'], inplace=True)

    # Convertir columnas de números y estrellas a numérico (integer), errores a NaN
    for col in NUMBER_COLS + STAR_COLS:
        df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')

    # Procesar Jackpot: convertir a numérico, errores a NaN (o un valor por defecto como -1 si se prefiere)
    if 'Jackpot' in df_cleaned.columns:
        df_cleaned['Jackpot'] = pd.to_numeric(df_cleaned['Jackpot'], errors='coerce')
        # Opcional: Llenar Jackpots faltantes/no numéricos con un valor (ej. media, mediana, o 0/NaN)
        # Por ahora, los NaNs se mantendrán y se filtrarán después si es necesario para análisis específico.
        # df_cleaned['Jackpot'].fillna(0, inplace=True) # Ejemplo de llenar con 0
    else:
        print("Advertencia: Columna 'Jackpot' no encontrada en los datos crudos.")
        df_cleaned['Jackpot'] = np.nan # Añadir columna con NaNs si no existe

    # Eliminar filas con cualquier NaN en números o estrellas después de la conversión
    df_cleaned.dropna(subset=NUMBER_COLS + STAR_COLS, inplace=True)

    # Convertir a enteros ahora que los NaNs problemáticos están fuera
    for col in NUMBER_COLS + STAR_COLS:
        df_cleaned[col] = df_cleaned[col].astype(int)

    # Validar rangos
    for col in NUMBER_COLS:
        df_cleaned = df_cleaned[df_cleaned[col].between(1, 50)]
    for col in STAR_COLS:
        df_cleaned = df_cleaned[df_cleaned[col].between(1, 12)]

    df_cleaned.sort_values(by='DrawDate', ascending=False, inplace=True)
    df_cleaned.reset_index(drop=True, inplace=True)

    return df_cleaned

def save_to_parquet(df, output_path):
    """Guarda el DataFrame limpio a formato Parquet con compresión zstd."""
    try:
        df.to_parquet(output_path, compression='zstd', index=False)
        print(f"Datos guardados exitosamente en {output_path}")
    except Exception as e:
        print(f"Error guardando a Parquet: {e}")

def main():
    print("Iniciando procesamiento de datos de EuroMillions (con Jackpot)...")
    raw_df = load_raw_data_from_source()

    print("\nDatos Crudos Cargados (primeras filas):")
    print(raw_df.head())
    raw_df.info()

    cleaned_df = clean_data(raw_df.copy())

    print("\nDatos Limpios (primeras filas):")
    print(cleaned_df.head())
    cleaned_df.info()

    if not cleaned_df.empty:
        # Sobrescribir el archivo Parquet existente con la nueva estructura y datos
        output_file = "data/euromillions_history_cleaned.parquet"
        save_to_parquet(cleaned_df, output_file)
    else:
        print("No hay datos limpios para guardar.")

    print("\nProcesamiento de datos (con Jackpot) completado.")

if __name__ == "__main__":
    main()
