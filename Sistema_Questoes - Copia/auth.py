import sqlite3
import hashlib

def conectar_db():
    return sqlite3.connect('questoes_estudos.db')

def criar_hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def cadastrar_usuario(username, senha):
    # REMOVIDO .lower(): Agora mantém maiúsculas e minúsculas exatamente como digitado
    username = username.strip() 
    if not username or not senha:
        return "⚠️ Usuário e senha não podem ser vazios."
        
    conn = conectar_db()
    cursor = conn.cursor()
    
    try:
        senha_hash = criar_hash_senha(senha)
        cursor.execute("INSERT INTO usuarios (username, senha_hash) VALUES (?, ?)", (username, senha_hash))
        conn.commit()
        retorno = "🎉 Usuário cadastrado com sucesso! Faça o login acima."
    except sqlite3.IntegrityError:
        retorno = "❌ Este nome de usuário já está em uso."
        
    conn.close()
    return retorno

def verificar_login(username, senha):
    username = username.strip() 
    conn = conectar_db()
    cursor = conn.cursor()
    
    senha_hash = criar_hash_senha(senha)
    # CORREÇÃO DA SINTAXE SQL: Força a comparação binária caractere por caractere
    cursor.execute("SELECT id FROM usuarios WHERE username COLLATE BINARY = ? AND senha_hash = ?", (username, senha_hash))
    usuario = cursor.fetchone()
    
    conn.close()
        # Altere a última linha da função verificar_login no seu auth.py para:
    if usuario:
        return usuario[0]  # <-- EXTRAI APENAS O NÚMERO PURO (Ex: 3), removendo a tupla (3,)
    return None

