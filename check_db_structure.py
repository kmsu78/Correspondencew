import sqlite3
import os
from app import app

def check_table_structure(table_name):
    """Verificar la estructura de una tabla en la base de datos"""
    
    # Obtener la ruta de la base de datos
    db_path = os.path.join(app.instance_path, 'correspondence.db')
    
    # Verificar si la base de datos existe
    if not os.path.exists(db_path):
        print(f"Error: La base de datos no existe en {db_path}")
        return
    
    print(f"Verificando estructura de la tabla {table_name} en {db_path}")
    
    # Conectar a la base de datos
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Obtener información de la tabla
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        if not columns:
            print(f"La tabla {table_name} no existe en la base de datos")
            return
        
        print(f"\nEstructura de la tabla {table_name}:")
        print("ID | Nombre | Tipo | NotNull | ValorPredeterminado | PK")
        print("-" * 70)
        
        for col in columns:
            print(f"{col[0]} | {col[1]} | {col[2]} | {col[3]} | {col[4]} | {col[5]}")
        
        # Verificar si hay datos en la tabla
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"\nLa tabla {table_name} contiene {count} registros")
        
        if count > 0:
            # Mostrar algunos registros de ejemplo
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
            rows = cursor.fetchall()
            
            print("\nEjemplos de registros:")
            for row in rows:
                print(row)
    
    except Exception as e:
        print(f"Error al verificar la estructura: {str(e)}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    # Verificar la estructura de las tablas relevantes
    check_table_structure("permission_change")
    check_table_structure("permission")
    check_table_structure("role")
