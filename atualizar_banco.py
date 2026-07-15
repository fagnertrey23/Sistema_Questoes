import sqlite3

def atualizar_banco():
    conn = sqlite3.connect('questoes_estudos.db')
    cursor = conn.cursor()
    
    try:
        # Adiciona a nova coluna 'assunto' na tabela de questões
        cursor.execute("ALTER TABLE questoes ADD COLUMN assunto TEXT")
        conn.commit()
        print("✅ Banco de dados atualizado com sucesso! Coluna 'assunto' adicionada.")
    except sqlite3.OperationalError:
        print("ℹ️ A coluna 'assunto' já existia no banco de dados.")
    
    conn.close()

atualizar_banco()
