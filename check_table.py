import sqlite3
import os

# Ruta de la base de datos
db_path = 'instance/correspondence.db'

# Verificar si la base de datos existe
if not os.path.exists(db_path):
    print(f"Error: La base de datos no existe en {db_path}")
    exit(1)

print(f"Verificando estructura de la tabla permission_change en {db_path}")

# Conectar a la base de datos
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Obtener información de la tabla
    cursor.execute("PRAGMA table_info(permission_change)")
    columns = cursor.fetchall()
    
    if not columns:
        print("La tabla permission_change no existe en la base de datos")
        exit(1)
    
    print("\nEstructura de la tabla permission_change:")
    print("ID | Nombre | Tipo | NotNull | ValorPredeterminado | PK")
    print("-" * 70)
    
    for col in columns:
        print(f"{col[0]} | {col[1]} | {col[2]} | {col[3]} | {col[4]} | {col[5]}")
    
except Exception as e:
    print(f"Error al verificar la estructura: {str(e)}")
finally:
    conn.close()
