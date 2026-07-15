import sqlite3

def adicionar_coluna_banca():
    conn = sqlite3.connect('questoes_estudos.db')
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE questoes ADD COLUMN banca TEXT")
        conn.commit()
        print("✅ Coluna 'banca' adicionada com sucesso no banco de dados!")
    except sqlite3.OperationalError:
        print("ℹ️ A coluna 'banca' já existe.")
    conn.close()

adicionar_coluna_banca()
