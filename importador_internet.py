import sqlite3
import json
import os

def conectar_db():
    return sqlite3.connect('questoes_estudos.db')

def obter_ou_criar_materia(cursor, nome_materia):
    if not nome_materia:
        nome_materia = "Geral"
    cursor.execute("SELECT id FROM materias WHERE nome = ?", (str(nome_materia).strip(),))
    resultado = cursor.fetchone()
    if resultado:
        return resultado[0]
    else:
        cursor.execute("INSERT INTO materias (nome) VALUES (?)", (str(nome_materia).strip(),))
        return cursor.lastrowid

def importar_banco_json_flexivel(caminho_arquivo, col_materia, col_enunciado, col_a, col_b, col_c, col_d, col_e, col_correta):
    if not os.path.exists(caminho_arquivo):
        return f"❌ Arquivo {caminho_arquivo} não encontrado na pasta do projeto."
        
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            dados = json.load(f)
    except Exception as e:
        return f"❌ Erro ao ler o arquivo JSON (pode estar mal formatado): {str(e)}"
        
    conn = conectar_db()
    cursor = conn.cursor()
    importadas = 0
    
    # Se o JSON baixado for um dicionário em vez de lista, tenta pegar a lista interna
    if isinstance(dados, dict):
        for chave, valor in dados.items():
            if isinstance(valor, list):
                dados = valor
                break

    for item in dados:
        try:
            # Extrai os dados baseando-se no mapeamento que o usuário informou
            materia_nome = item.get(col_materia, "Geral")
            materia_id = obter_ou_criar_materia(cursor, materia_nome)
            
            enunciado = item.get(col_enunciado)
            alt_a = item.get(col_a)
            alt_b = item.get(col_b)
            alt_c = item.get(col_c)
            alt_d = item.get(col_d)
            alt_e = item.get(col_e, None)
            correta = str(item.get(col_correta, '')).upper().strip()
            
            # Limpa caso venha algo como "Alternativa A" para salvar apenas "A"
            if len(correta) > 1:
                correta = correta[0] 

            if enunciado and alt_a and alt_b and correta:
                cursor.execute('''
                    INSERT INTO questoes (materia_id, enunciado, alt_a, alt_b, alt_c, alt_d, alt_e, alternativa_correta)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (materia_id, enunciado, alt_a, alt_b, alt_c, alt_d, alt_e, correta))
                importadas += 1
        except Exception:
            continue
            
    conn.commit()
    conn.close()
    return f"🚀 Sucesso! {importadas} questões processadas e injetadas no seu banco de dados."
