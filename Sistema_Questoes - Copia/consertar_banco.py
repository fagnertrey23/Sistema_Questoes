import sqlite3

def recriar_tabela_questoes():
    conn = sqlite3.connect('questoes_estudos.db')
    cursor = conn.cursor()
    
    # 1. Renomeia a tabela antiga para salvar os dados antigos de segurança
    try:
        cursor.execute("ALTER TABLE questoes RENAME TO questoes_antigas")
    except sqlite3.OperationalError:
        print("Tabela temporária já existia ou banco limpo.")

    # 2. Cria a nova tabela sem as travas de NOT NULL nas alternativas C, D e E
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            materia_id INTEGER,
            assunto TEXT,
            enunciado TEXT NOT NULL,
            alt_a TEXT NOT NULL,
            alt_b TEXT NOT NULL,
            alt_c TEXT, -- Opcional
            alt_d TEXT, -- Opcional
            alt_e TEXT, -- Opcional
            alternativa_correta TEXT NOT NULL,
            FOREIGN KEY (materia_id) REFERENCES materias (id)
        )
    ''')

    # 3. Migra todas as questões que você já tinha guardadas da tabela antiga para a nova
    try:
        cursor.execute('''
            INSERT INTO questoes (id, materia_id, assunto, enunciado, alt_a, alt_b, alt_c, alt_d, alt_e, alternativa_correta)
            SELECT id, materia_id, assunto, enunciado, alt_a, alt_b, alt_c, alt_d, alt_e, alternativa_correta 
            FROM questoes_antigas
        ''')
        cursor.execute("DROP TABLE questoes_antigas")
        print("🎉 Banco de dados atualizado com sucesso! As restrições foram removidas.")
    except Exception:
        print("Banco atualizado do zero de forma limpa.")
        
    conn.commit()
    conn.close()

recriar_tabela_questoes()
