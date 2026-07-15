import sqlite3
import hashlib

def estruturar_usuarios():
    conn = sqlite3.connect('questoes_estudos.db')
    cursor = conn.cursor()
    
    # 1. Cria a tabela de usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL
        )
    ''')
    
    # 2. Adiciona a coluna de usuario_id na tabela de historico para separar os graficos
    try:
        cursor.execute("ALTER TABLE historico ADD COLUMN usuario_id INTEGER")
    except sqlite3.OperationalError:
        pass # A coluna já existe
        
    conn.commit()
    conn.close()
    print("✅ Banco de dados preparado para receber usuários!")

estruturar_usuarios()
