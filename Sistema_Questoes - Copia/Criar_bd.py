import sqlite3

def criar_banco():
    # Conecta ao arquivo do banco (ele será criado na mesma pasta do script)
    conn = sqlite3.connect('questoes_estudos.db')
    cursor = conn.cursor()

    # 1. Tabela de Matérias (Ex: Português, Direito Constitucional)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS materias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE
        )
    ''')

    # 2. Tabela de Questões
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            materia_id INTEGER,
            enunciado TEXT NOT NULL,
            alt_a TEXT NOT NULL,
            alt_b TEXT NOT NULL,
            alt_c TEXT NOT NULL,
            alt_d TEXT NOT NULL,
            alt_e TEXT,
            alternativa_correta TEXT NOT NULL, -- Armazena 'A', 'B', 'C', 'D' ou 'E'
            FOREIGN KEY (materia_id) REFERENCES materias (id)
        )
    ''')

    # 3. Tabela de Histórico (Registra cada tentativa sua)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            questao_id INTEGER,
            resposta_usuario TEXT NOT NULL,
            acertou INTEGER, -- 1 para Correto, 0 para Errado
            data_resolucao DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (questao_id) REFERENCES questoes (id)
        )
    ''')

    conn.commit()
    conn.close()
    print("Banco de dados e tabelas criados com sucesso!")

# Executar a função
criar_banco()
