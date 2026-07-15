import sqlite3
import re

def conectar_db():
    return sqlite3.connect('questoes_estudos.db')

def obter_ou_criar_materia(cursor, nome_materia):
    nome_materia = nome_materia.strip()
    cursor.execute("SELECT id FROM materias WHERE nome = ?", (nome_materia,))
    resultado = cursor.fetchone()
    
    if resultado:
        return resultado[0]
    else:
        cursor.execute("INSERT INTO materias (nome) VALUES (?)", (nome_materia,))
        return cursor.lastrowid

def importar_questoes(caminho_arquivo):
    conn = conectar_db()
    cursor = conn.cursor()
    
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        conteudo = f.read()
    
    # Separar as questões pelo delimitador '---'
    blocos_questoes = conteudo.split('---')
    questoes_importadas = 0
    
    for bloco in blocos_questoes:
        if not bloco.strip():
            continue
            
        # Inicializar variáveis da questão
        materia = None
        enunciado = None
        alt_a = None
        alt_b = None
        alt_c = None
        alt_d = None
        alt_e = None
        correta = None
        
        # Processar linha por linha do bloco
        linhas = bloco.strip().split('\n')
        for linha in linhas:
            linha = linha.strip()
            if linha.startswith('MATERIA:'):
                materia = linha.replace('MATERIA:', '').strip()
            elif linha.startswith('ENUNCIADO:'):
                enunciado = linha.replace('ENUNCIADO:', '').strip()
            elif linha.startswith('A)'):
                alt_a = linha
            elif linha.startswith('B)'):
                alt_b = linha
            elif linha.startswith('C)'):
                alt_c = linha
            elif linha.startswith('D)'):
                alt_d = linha
            elif linha.startswith('E)'):
                alt_e = linha
            elif linha.startswith('CORRETA:'):
                correta = linha.replace('CORRETA:', '').strip().upper()
        
        # Validar se os campos obrigatórios existem antes de salvar
        if materia and enunciado and alt_a and alt_b and correta:
            materia_id = obter_ou_criar_materia(cursor, materia)
            
            cursor.execute('''
                INSERT INTO questoes (materia_id, enunciado, alt_a, alt_b, alt_c, alt_d, alt_e, alternativa_correta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (materia_id, enunciado, alt_a, alt_b, alt_c, alt_d, alt_e, correta))
            
            questoes_importadas += 1
            
    conn.commit()
    conn.close()
    print(f"🎉 Sucesso! {questoes_importadas} novas questões foram importadas para o seu sistema.")

# Executar o importador buscando o arquivo de texto
importar_questoes('questoes.txt')
