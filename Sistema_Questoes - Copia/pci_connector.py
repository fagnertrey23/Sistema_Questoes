import requests
from bs4 import BeautifulSoup
import json
import sqlite3
import time
import re  # <-- IMPORTAÇÃO CORRIGIDA: Agora o Python reconhece essa ferramenta!
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
        return resultado[0] # Retorna o número puro do ID
    else:
        cursor.execute("INSERT INTO materias (nome) VALUES (?)", (nome_materia,))
        return cursor.lastrowid

def sugar_simulado_pci_via_link(url_simulado):
    """Acessa a URL do simulado do PCI, descobre o assunto real da página e importa todas as questões"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        resposta = requests.get(url_simulado, headers=headers, timeout=15)
        if resposta.status_code != 200:
            return f"❌ Erro ao acessar a página. (Código HTTP: {resposta.status_code})"
            
        soup = BeautifulSoup(resposta.text, 'html.parser')
        
        # --- CAPTURA AUTOMÁTICA DO TÍTULO DO PCI ---
        bloco_titulo = soup.find('div', class_='caminho') or soup.find('h1')
        materia_padrao = "Geral"
        assunto_padrao = "Geral"
        
        if bloco_titulo:
            texto_titulo = bloco_titulo.get_text()
            if "›" in texto_titulo:
                partes = texto_titulo.split("›")
                materia_padrao = partes[0].strip().title()
                assunto_padrao = partes[1].strip().title()
                # Remove contadores de questões do título se houver (Ex: "30 Questões")
                assunto_padrao = re.sub(r'\d+\s*[qQ]uestões.*', '', assunto_padrao).strip()
            else:
                materia_padrao = texto_titulo.strip().title()

        corpo_simulado = soup.find('div', id='conteudo') or soup.find('main') or soup.body
        if not corpo_simulado:
            return "❌ Não foi possível mapear o texto deste simulado."
            
        texto_bruto = corpo_simulado.get_text(separator="\n")
        linhas_limpas = [l.strip() for l in texto_bruto.split('\n') if len(l.strip()) > 10]
        
        # LIMITES AMPLIADOS: Garante que cadernos de 30 questões caibam por completo
        texto_final = "\n".join(linhas_limpas)[:80000]

        if len(texto_final) < 200:
            return "❌ O texto extraído do link veio muito curto."

        client = genai.Client(api_key=API_KEY)
        
         # 1. Atualize o Prompt dentro do seu pci_connector.py para capturar a banca:
        prompt = """
        Você é um robô de extração de dados. Analise o texto extraído de um simulado da internet.
        Sua missão é ler e extrair TODAS as questões de múltipla escolha presentes no texto, sem ignorar nenhuma.
        
        Sua saída DEVE ser estritamente uma lista JSON de objetos, contendo exatamente estas chaves:
        - banca: O nome da banca organizadora identificada no cabeçalho ou texto da questão (Ex: 'FGV', 'Cebraspe', 'ADM&TEC', 'FCC'). Se não houver, coloque 'Não identificada'.
        - enunciado: O enunciado/pergunta completo da questão.
        - alt_a: Alternativa A.
        - alt_b: Alternativa B.
        - alt_c: Alternativa C.
        - alt_d: Alternativa D.
        - alt_e: Alternativa E (use null se a questão só tiver 4 opções).
        - correta: O gabarito oficial ('A', 'B', 'C', 'D' ou 'E').
        
        Gere a lista completa com todas as questões identificadas no texto. Não resuma e não pare na metade.
        """

        
        response = None
        for tentativa in range(3):
            try:
                response = client.models.generate_content(
                    model='gemini-3.5-flash',
                    contents=[prompt, texto_final],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1 # Mantém a IA focada e precisa na cópia
                    ),
                )
                break
            except Exception as error_api:
                if "503" in str(error_api) and tentativa < 2:
                    time.sleep(3)
                    continue
                else:
                    raise error_api
        
        if not response:
            return "❌ O servidor do Google falhou em responder."

        texto_json = response.text.strip()
        inicio = texto_json.find('[')
        fim = texto_json.rfind(']') + 1
        dados_questoes = json.loads(texto_json[inicio:fim])
        
        conn = conectar_db()
        cursor = conn.cursor()
        
        importadas = 0
        materia_id = obtener_ou_criar_materia(cursor, materia_padrao)
        
        # 2. Atualize o laço de gravação para incluir a banca:
        for q in dados_questoes:
            banca_nome = str(q.get('banca', 'Geral')).strip().upper()
            if banca_nome.lower() in ["none", "nan", "", "null"]:
                banca_nome = "Não identificada"

            cursor.execute('''
                INSERT INTO questoes (materia_id, assunto, banca, enunciado, alt_a, alt_b, alt_c, alt_d, alt_e, alternativa_correta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                materia_id, 
                assunto_padrao,
                banca_nome, # <-- Nova coluna de banca salva aqui
                q.get('enunciado'), 
                q.get('alt_a', 'Alternativa A não lida'), 
                q.get('alt_b', 'Alternativa B não lida'), 
                q.get('alt_c', None), 
                q.get('alt_d', None), 
                q.get('alt_e', None), 
                str(q.get('correta', 'A')).upper()
            ))
            importadas += 1

            
        conn.commit()
        conn.close()
        return f"🚀 Sucesso! O link foi processado e {importadas} questões foram catalogadas na Matéria '{materia_padrao}' sob o Assunto Unificado '{assunto_padrao}'!"
        
    except Exception as e:
        return f"❌ Falha no processador de links: {str(e)}"
