import sqlite3
import json
from google import genai
from google.genai import types

# COLE A SUA CHAVE DA API DO GOOGLE BEM AQUI DENTRO DAS ASPAS
API_KEY = "AQ.Ab8RN6JVlsZLb1Xm90-1pGdpcaOTQmsmI3McJb3sedRAni3sZg"

def conectar_db():
    return sqlite3.connect('questoes_estudos.db')

def obtener_ou_criar_materia(cursor, nome_materia):
    nome_materia = nome_materia.strip().title()
    cursor.execute("SELECT id FROM materias WHERE nome = ?", (nome_materia,))
    resultado = cursor.fetchone()
    if resultado:
        return resultado
    else:
        cursor.execute("INSERT INTO materias (nome) VALUES (?)", (nome_materia,))
        return cursor.lastrowid

def gerar_questoes_ia(materia, assunto_principal, banca, quantidade=3):
    client = genai.Client(api_key=API_KEY)
    
    # 1. Atualizamos o prompt para exigir que a IA retorne a chave "assunto" no JSON
    prompt = f"""
    Gere exatamente {quantidade} questões de concurso público sobre a matéria '{materia}' (focando no assunto '{assunto_principal}') no estilo rigoroso da banca '{banca}'.
    Forneça a resposta estritamente no formato JSON, como uma lista de objetos. Cada objeto DEVE ter exatamente estas chaves:
    - assunto: O subassunto específico da questão (Ex: se o assunto principal for Crase, o subassunto pode ser 'Casos Obrigatórios' ou 'Casos Proibidos'). Use no máximo 3 palavras.
    - enunciado: O texto completo da questão.
    - alt_a: Alternativa A.
    - alt_b: Alternativa B.
    - alt_c: Alternativa C.
    - alt_d: Alternativa D.
    - alt_e: Alternativa E (coloque null se for banca de 4 alternativas).
    - correta: Apenas a letra correspondente à alternativa correta ('A', 'B', 'C', 'D' ou 'E').
    Não adicione nenhuma introdução, explicação ou formatação markdown (como ```json) fora do JSON bruto.
    """
    
    try:
        # Mude exatamente para esta linha no gerador_ia.py:
        response = client.models.generate_content(
            model='gemini-3.5-flash', # <-- Altere aqui também
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

        
        dados_questoes = json.loads(response.text)
        
        conn = conectar_db()
        cursor = conn.cursor()
        materia_id = obtener_ou_criar_materia(cursor, materia)
        
        for q in dados_questoes:
            # Pega o assunto gerado pela IA ou usa o assunto principal digitado na tela como padrão de segurança
            assunto_questao = q.get('assunto', assunto_principal).strip().title()
            
            # 2. Atualizamos o comando INSERT incluindo a coluna 'assunto' e o ponto de interrogação correspondente
            cursor.execute('''
                INSERT INTO questoes (materia_id, assunto, enunciado, alt_a, alt_b, alt_c, alt_d, alt_e, alternativa_correta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                materia_id, 
                assunto_questao, # Novo campo injetado aqui
                q['enunciado'], 
                q['alt_a'], 
                q['alt_b'], 
                q['alt_c'], 
                q['alt_d'], 
                q['alt_e'], 
                q['correta'].upper()
            ))
            
        conn.commit()
        conn.close()
        return f"🎉 Sucesso! {len(dados_questoes)} questões geradas pela IA da banca {banca} foram salvas com subdivisão de assunto."
    except Exception as e:
        return f"❌ Erro ao gerar questões: {str(e)}"
