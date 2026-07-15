import sqlite3
import json
import re
import os
import time
import streamlit as st
from google import genai
from google.genai import types

from gerador_ia import API_KEY

def conectar_db():
    return sqlite3.connect('questoes_estudos.db')

def obtener_ou_criar_materia(cursor, nome_materia):
    nome_materia = nome_materia.strip().title()
    cursor.execute("SELECT id FROM materias WHERE nome = ?", (nome_materia,))
    resultado = cursor.fetchone()
    if resultado:
        return resultado[0] # Retorna o ID puro extraído da tupla
    else:
        cursor.execute("INSERT INTO materias (nome) VALUES (?)", (nome_materia,))
        return cursor.lastrowid

def processar_prova_pdf_com_ia(arquivo_streamlit):
    caminho_temporario = "temp_prova.pdf"
    with open(caminho_temporario, "wb") as f:
        f.write(arquivo_streamlit.getbuffer())

    client = genai.Client(api_key=API_KEY)
    
    try:
        arquivo_google = client.files.upload(file=caminho_temporario)
        
        prompt = """
        Você é um especialista em estruturação de dados educacionais com visão computacional. 
        Analise visualmente as imagens deste PDF escaneado e extraia as questões de múltipla escolha.
        
        Estruture estritamente em formato JSON contendo uma lista de objetos com as chaves:
        materia, assunto, enunciado, alt_a, alt_b, alt_c, alt_d, alt_e, correta.
        """
        
        # SISTEMA ANTI-CONGESTIONAMENTO (Dribla o erro 503)
        response = None
        for tentativa in range(3):
            try:
                response = client.models.generate_content(
                    model='gemini-3.5-flash',
                    contents=[arquivo_google, prompt],
                    config=types.GenerateContentConfig(response_mime_type="application/json"),
                )
                break # Se funcionar, sai do loop de tentativas
            except Exception as error_api:
                if "503" in str(error_api) and tentativa < 2:
                    time.sleep(2) # Espera 2 segundos antes de tentar de novo
                    continue
                else:
                    raise error_api

        client.files.delete(name=arquivo_google.name)
        if os.path.exists(caminho_temporario):
            os.remove(caminho_temporario)
            
        if not response:
            return "❌ Servidor do Google indisponível no momento. Tente novamente."

        texto_limpo = response.text.strip()
        inicio_json = texto_limpo.find('[')
        fim_json = texto_limpo.rfind(']') + 1
        if inicio_json != -1 and fim_json != -1:
            texto_limpo = texto_limpo[inicio_json:fim_json]
            
        dados_questoes = json.loads(texto_limpo)
        
        conn = conectar_db()
        cursor = conn.cursor()
        
        importadas = 0
        for q in dados_questoes:
            materia_id = obtener_ou_criar_materia(cursor, q.get('materia', 'Geral'))
            assunto_nome = q.get('assunto', 'Geral').strip().title()
            
            cursor.execute('''
                INSERT INTO questoes (materia_id, assunto, enunciado, alt_a, alt_b, alt_c, alt_d, alt_e, alternativa_correta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (materia_id, assunto_nome, q.get('enunciado'), q.get('alt_a'), q.get('alt_b'), q.get('alt_c'), q.get('alt_d'), q.get('alt_e', None), str(q.get('correta', 'A')).upper()))
            importadas += 1
            
        conn.commit()
        conn.close()
        return f"🎉 Sucesso! A IA processou visualmente o seu PDF e importou {importadas} questões!"
        
    except Exception as e:
        if os.path.exists(caminho_temporario):
            os.remove(caminho_temporario)
        return f"❌ Erro no processamento: {str(e)}"

def processar_texto_em_massa_com_ia(texto_colado):
    """Processa o texto de uma prova colada pelo usuário tratando cortes abruptos"""
    client = genai.Client(api_key=API_KEY)
    
    prompt = """
    Você é um especialista em estruturação de dados de concursos públicos. 
    Analise o texto a seguir, que contém questões de simulados e provas. 
    Sua missão é extrair TODAS as questões de múltipla escolha completas.
    
    ATENÇÃO: Se o texto for cortado abruptamente no final do arquivo, IGNORE a última questão incompleta e processe apenas as anteriores que estão 100% visíveis.
    
    Para cada questão completa, extraia estruturado em JSON:
    - materia: A matéria geral da questão (Ex: 'Contabilidade', 'Auditoria').
    - assunto: O assunto específico (Ex: 'Procedimentos de Auditoria', 'Evidências'). Máximo 3 palavras.
    - enunciado: O texto da pergunta completo.
    - alt_a até alt_e: As alternativas correspondentes (use null para alt_e se houver apenas 4 opções).
    - correta: A letra da resposta correta ('A', 'B', 'C', 'D' ou 'E') se souber, ou uma estimativa com base no contexto.
    
    Forneça APENAS a lista JSON crua.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=[prompt, texto_colado],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        
        texto_limpo = response.text.strip()
        
        # Isolar estritamente a lista JSON [ ]
        inicio_json = texto_limpo.find('[')
        fim_json = texto_limpo.rfind(']') + 1
        if inicio_json != -1 and fim_json != -1:
            texto_limpo = texto_limpo[inicio_json:fim_json]
            
        dados_questoes = json.loads(texto_limpo)
        
        conn = conectar_db()
        cursor = conn.cursor()
        
        importadas = 0
        for q in dados_questoes:
            materia_id = obtener_ou_criar_materia(cursor, q.get('materia', 'Geral'))
            assunto_nome = q.get('assunto', 'Geral').strip().title()
            
            cursor.execute('''
                INSERT INTO questoes (materia_id, assunto, enunciado, alt_a, alt_b, alt_c, alt_d, alt_e, alternativa_correta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                materia_id, 
                assunto_nome, 
                q.get('enunciado'), 
                q.get('alt_a'), 
                q.get('alt_b'), 
                q.get('alt_c'), 
                q.get('alt_d'), 
                q.get('alt_e', None), 
                str(q.get('correta', 'A')).upper()
            ))
            importadas += 1
            
        conn.commit()
        conn.close()
        return f"🎉 Sucesso absoluto! O sistema interpretou o texto e importou {importadas} questões do PCI divididas automaticamente por Matéria e Assunto!"
        
    except Exception as e:
        return f"❌ Erro ao processar: {str(e)} | Resposta da IA: {response.text[:150] if 'response' in locals() else 'Sem resposta'}"
