import streamlit as st
import sqlite3
import pandas as pd
import os

# 1. Configuração inicial obrigatória (DEVE ser a primeira linha)
st.set_page_config(page_title="Meu Sistema de Questões Elite", layout="wide")

# Importando as funções que criamos nos outros arquivos
from gerador_ia import gerar_questoes_ia
from leitor_pdf import processar_prova_pdf_com_ia
from leitor_pdf import processar_texto_em_massa_com_ia
from auth import verificar_login, cadastrar_usuario

def conectar_db():
    return sqlite3.connect('questoes_estudos.db')

# --- SISTEMA DE ARQUIVO SEGURO CONTRA QUEDA DE F5 ---
ARQUIVO_SESSAO = "sessao_usuario.txt"

# Funções auxiliares locais (não gastam internet, nem IA, nem navegador)
def salvar_sessao_local(uid, username):
    with open(ARQUIVO_SESSAO, "w", encoding="utf-8") as f:
        f.write(f"{uid}\n{username}")

def ler_sessao_local():
    if os.path.exists(ARQUIVO_SESSAO):
        with open(ARQUIVO_SESSAO, "r", encoding="utf-8") as f:
            linhas = f.read().splitlines()
            if len(linhas) == 2:
                return int(linhas[0]), linhas[1]
    return None, None

def apagar_sessao_local():
    if os.path.exists(ARQUIVO_SESSAO):
        os.remove(ARQUIVO_SESSAO)

# Tenta ler o arquivo de login persistente assim que a página atualiza
local_uid, local_uname = ler_sessao_local()

if 'usuario_id' not in st.session_state:
    st.session_state.usuario_id = local_uid
if 'username' not in st.session_state:
    st.session_state.username = local_uname

# Força a restauração caso a memória do Streamlit limpe no F5
if st.session_state.usuario_id is None and local_uid is not None:
    st.session_state.usuario_id = local_uid
    st.session_state.username = local_uname

# =========================================================
# BLOCO A: SE NÃO ESTIVER LOGADO -> TELA DE LOGIN
# =========================================================
if st.session_state.usuario_id is None:
    st.sidebar.info("🔑 Por favor, faça login ou crie uma conta para acessar seu painel personalizado.")
    
    st.title("🔐 Acesso ao Sistema de Questões")
    aba_login, aba_cadastro_user = st.tabs(["🔑 Entrar", "📝 Criar Conta Grátis"])
    
    with aba_login:
        u_login = st.text_input("Usuário:", key="u_login")
        s_login = st.text_input("Senha:", type="password", key="s_login")
        if st.button("Entrar no Painel"):
            uid = verificar_login(u_login, s_login)
            if uid:
                uid_puro = uid[0] if isinstance(uid, (tuple, list)) else uid
                
                # Grava na sessão em tempo real
                st.session_state.usuario_id = int(uid_puro)
                st.session_state.username = u_login
                
                # Salva o arquivo de login no seu HD
                salvar_sessao_local(int(uid_puro), u_login)
                
                st.success(f"Bem-vindo de volta, {u_login}!")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos (Sistema Sensível a Maiúsculas!).")
                
    with aba_cadastro_user:
        u_cad = st.text_input("Escolha um Usuário:", key="u_cad")
        s_cad = st.text_input("Escolha uma Senha:", type="password", key="s_cad")
        if st.button("Cadastrar Minha Conta"):
            msg = cadastrar_usuario(u_cad, s_cad)
            st.info(msg)

# =========================================================
# BLOCO B: SE ESTIVER LOGADO -> LIBERA TODO O SISTEMA
# =========================================================
else:
    # --- BOTÃO SAIR DELETA O ARQUIVO LOCAL ---
    if st.sidebar.button("🚪 Sair / Desconectar"):
        st.session_state.usuario_id = None
        st.session_state.username = None
        apagar_sessao_local()
        st.rerun()

    st.sidebar.markdown("---")
    
    # ... A partir daqui continua o restante do seu bloco ELSE igual (filtros de tempo, matérias, etc.) ...


    # Menu de Filtro por Período de Tempo
    filtro_tempo = st.sidebar.selectbox(
        "Filtrar Estatísticas por:",
        ["Todo o Período", "Hoje", "Últimos 7 dias", "Últimos 30 dias"]
    )

    # Criar a lógica SQL baseando-se no tempo E travando no ID do usuário logado
    if filtro_tempo == "Hoje":
        condicao_tempo = f"WHERE h.usuario_id = {st.session_state.usuario_id} AND h.data_resolucao >= date('now', 'start of day', 'localtime')"
    elif filtro_tempo == "Últimos 7 dias":
        condicao_tempo = f"WHERE h.usuario_id = {st.session_state.usuario_id} AND h.data_resolucao >= date('now', '-7 days', 'localtime')"
    elif filtro_tempo == "Últimos 30 dias":
        condicao_tempo = f"WHERE h.usuario_id = {st.session_state.usuario_id} AND h.data_resolucao >= date('now', '-30 days', 'localtime')"
    else:
        condicao_tempo = f"WHERE h.usuario_id = {st.session_state.usuario_id}"

    # Buscar histórico e matérias filtrando com total segurança pelo Usuário Logado
    conn = conectar_db()
    query_historico = f"""
        SELECT m.nome as Materia, h.acertou 
        FROM historico h
        JOIN questoes q ON h.questao_id = q.id
        JOIN materias m ON q.materia_id = m.id
        {condicao_tempo}
    """
    historico_df = pd.read_sql_query(query_historico, conn)
    materias_df = pd.read_sql_query("SELECT * FROM materias", conn)
    conn.close()

    # Renderizar os gráficos na Barra Lateral se houver histórico
    if not historico_df.empty:
        historico_df['Resultado'] = historico_df['acertou'].map({1: 'Acertos', 0: 'Erros'})
        pivot = historico_df.groupby(['Materia', 'Resultado']).size().unstack(fill_value=0)
        
        if 'Acertos' not in pivot.columns: pivot['Acertos'] = 0
        if 'Erros' not in pivot.columns: pivot['Erros'] = 0
        
        pivot['Total'] = pivot['Acertos'] + pivot['Erros']
        pivot['% Acerto'] = ((pivot['Acertos'] / pivot['Total']) * 100).round(1)
        
        st.sidebar.subheader(f"📈 Rendimento ({filtro_tempo})")
        st.sidebar.dataframe(pivot[['Acertos', 'Erros', 'Total', '% Acerto']])
        st.sidebar.bar_chart(pivot['% Acerto'])
    else:
        st.sidebar.info(f"Nenhum histórico registrado para {st.session_state.username} neste período.")

    # Botão reset exclusivo por usuário
    if st.sidebar.button("🗑️ Resetar Meu Histórico"):
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM historico WHERE usuario_id = {st.session_state.usuario_id}")
        conn.commit()
        conn.close()
        st.sidebar.success("Seu histórico foi zerado!")
        st.rerun()

        # --- CORPO PRINCIPAL DO PAINEL DE ABAS (DINÂMICO PARA ADMIN) ---
    st.title("📝 Central de Concursos Própria")
    
    # 1. Definição da lista padrão de abas para todos os concurseiros
    nomes_abas = [
        "📝 Responder Questões", "🤖 Gerar por IA", "🌐 Importar JSON", 
        "📄 Enviar PDF", "🔍 Buscar no PCI", "📥 Cadastrar Manualmente", "❌ Caderno de Erros"
    ]
    
    # 2. SE O USUÁRIO LOGADO FOR EXATAMENTE O "admin", INCLUI A OITAVA ABA
    if st.session_state.username == "admin":
        nomes_abas.append("🛠️ Painel do Administrador")
        
    # 3. Cria as abas na tela com base na lista que definimos acima
    abas = st.tabs(nomes_abas)
    
    # 4. Vincula as variáveis antigas às abas correspondentes (mantém a compatibilidade com o resto do código)
    aba_estudar, aba_ia, aba_internet, aba_pdf, aba_pci, aba_cadastro, aba_erros = abas[0], abas[1], abas[2], abas[3], abas[4], abas[5], abas[6]

    # ABA 1: ÁREA DE ESTUDOS (FILTRO DUPLO MATÉRIA + ASSUNTO)
    with aba_estudar:
        st.header("Área de Treinamento")
        if not materias_df.empty:
            # 1. Primeiro Filtro: Escolha da Matéria Geral
            materia_sel = st.selectbox("Selecione a Matéria:", materias_df['nome'].tolist(), key="estudo_mat")
            id_materia = materias_df[materias_df['nome'] == materia_sel]['id'].values[0]
            
            # Buscar no banco quais assuntos existem salvos para essa matéria
            conn = conectar_db()
            assuntos_df = pd.read_sql_query(f"SELECT DISTINCT assunto FROM questoes WHERE materia_id = {id_materia}", conn)
            conn.close()
            
            # Limpar termos nulos ou vazios
            assuntos_disponiveis = assuntos_df['assunto'].dropna().tolist()
            assuntos_disponiveis = [a.strip() for a in assuntos_disponiveis if a.strip() != ""]
            
            if not assuntos_disponiveis:
                assuntos_disponiveis = ["Geral"]
            else:
                assuntos_disponiveis.insert(0, "Todos os Assuntos")
                
            # 2. Segundo Filtro: Escolha do Assunto Específico
            assunto_sel = st.selectbox("Selecione o Assunto:", assuntos_disponiveis, key="estudo_assunto")
            
            # 3. Montar a busca condicional baseada nos filtros
            conn = conectar_db()
            if assunto_sel == "Todos os Assuntos":
                query_filtro = f"SELECT * FROM questoes WHERE materia_id = {id_materia}"
            elif assunto_sel == "Geral":
                query_filtro = f"SELECT * FROM questoes WHERE materia_id = {id_materia} AND (assunto = 'Geral' OR assunto IS NULL or assunto = 'None' or assunto = 'Nan')"
            else:
                query_filtro = f"SELECT * FROM questoes WHERE materia_id = {id_materia} AND assunto = '{assunto_sel}'"
                
            questoes = pd.read_sql_query(query_filtro, conn)
            conn.close()
            
            if not questoes.empty:
                # Criar chave de sessão única para rastrear a posição
                chave_sessao = f'idx_estudo_{id_materia}_{assunto_sel.replace(" ", "_")}'
                if chave_sessao not in st.session_state:
                    st.session_state[chave_sessao] = 0
                    
                idx = st.session_state[chave_sessao]
                if idx >= len(questoes): 
                    idx = 0
                    st.session_state[chave_sessao] = 0
                
                q_atual = questoes.iloc[idx]
                
                st.markdown(f"#### 📝 **Questão {idx + 1} de {len(questoes)}**")
                
                # Tratamento do rótulo do subassunto visual para não exibir NaN
                assunto_cru = str(q_atual['assunto']).strip()
                subassunto = "Geral" if not assunto_cru or assunto_cru.lower() in ["none", "nan", "", "null"] else q_atual['assunto']
                
                # NOVO: Tratamento do rótulo da Banca organizadora para não quebrar a tela
                banca_cru = str(q_atual['banca']).strip() if 'banca' in q_atual.index else "Não identificada"
                banca_tela = "Não identificada" if not banca_cru or banca_cru.lower() in ["none", "nan", "", "null"] else banca_cru
                
                # Exibe as duas informações juntas na tela de estudos, lado a lado!
                st.markdown(f"🏢 **Banca:** `{banca_tela}` | 📌 **Subassunto:** `{subassunto}`")
                
                st.info(q_atual['enunciado'])

                
                # Montar e formatar as opções de alternativas garantindo as letras visíveis
                opcoes_brutas = [q_atual['alt_a'], q_atual['alt_b'], q_atual['alt_c'], q_atual['alt_d']]
                if q_atual['alt_e']: 
                    opcoes_brutas.append(q_atual['alt_e'])
                
                letras = ["A) ", "B) ", "C) ", "D) ", "E) "]
                opcoes_formatadas = []
                for i, opcao in enumerate(opcoes_brutas):
                    if opcao:
                        txt_opt = str(opcao).strip()
                        if txt_opt.upper().startswith(letras[i].strip().upper()):
                            opcoes_formatadas.append(txt_opt)
                        else:
                            opcoes_formatadas.append(f"{letras[i]}{txt_opt}")
                
                resp = st.radio("Selecione sua resposta:", opcoes_formatadas, key=f"radio_{q_atual['id']}_{idx}")
                
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("🎯 Responder", key=f"btn_responder_{q_atual['id']}_{idx}"):
                        letra_usuario = resp.strip().upper()[0] # Força capturar estritamente a primeira letra
                        letra_gabarito = str(q_atual['alternativa_correta']).strip().upper()
                        
                        acertou = 1 if letra_usuario == letra_gabarito else 0
                        
                        conn = conectar_db()
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO historico (questao_id, resposta_usuario, acertou, usuario_id) VALUES (?, ?, ?, ?)",
                            (int(q_atual['id']), letra_usuario, acertou, int(st.session_state.usuario_id))
                        )
                        conn.commit()
                        conn.close()
                        
                        if acertou == 1: 
                            st.success(f"🎉 Correto! Gabarito oficial: {letra_gabarito}")
                        else: 
                            st.error(f"❌ Errado. Gabarito oficial: {letra_gabarito}")
                            
                with col_b2:
                    if st.button("Próxima Questão ➡️", key=f"btn_prox_{id_materia}_{idx}"):
                        st.session_state[chave_sessao] = (idx + 1) % len(questoes)
                        st.rerun()
            else:
                st.warning(f"Sem questões gravadas no assunto '{assunto_sel}'.")
        else:
            st.info("O seu banco de dados está vazio. Vá até as abas ao lado para importar seus primeiros simulados!")

    # ABA 2: GERADOR POR IA
    with aba_ia:
        st.header("🤖 Criar Simulados Avançados Inéditos")
        st.write("Use o poder da inteligência artificial para criar questões idênticas às das bancas tradicionais.")
        ia_materia = st.text_input("Matéria (Ex: Direito Administrativo, Português):")
        ia_assunto = st.text_input("Assunto Específico (Ex: Atos Administrativos, Crase):")
        ia_banca = st.selectbox("Estilo da Banca:", ["FGV", "Cebraspe (Certo/Errado)", "Cebraspe (Múltipla Escolha)", "FCC", "Vunesp"])
        ia_qtd = st.slider("Quantidade de Questões:", 1, 10, 3)
        
        if st.button("✨ Alimentar Banco com IA"):
            if ia_materia and ia_assunto:
                with st.spinner("A IA está gerando suas questões..."):
                    resultado = gerar_questoes_ia(ia_materia, ia_assunto, ia_banca, ia_qtd)
                    st.success(resultado)
            else:
                st.error("Por favor, preencha a matéria e o assunto.")

    # ABA 3: IMPORTADOR DA INTERNET (JSON)
    with aba_internet:
        st.header("🌐 Importador Inteligente de Grandes Bases de Dados")
        st.write("Mapeie e importe arquivos JSON baixados da internet de forma flexível.")
        nome_arquivo = st.text_input("Nome do arquivo (Ex: `banco.json`):", "questoes_internet.json")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            c_materia = st.text_input("Campo da Matéria:", "materia")
            c_enunciado = st.text_input("Campo do Enunciado:", "enunciado")
        with col2:
            c_a = st.text_input("Alternativa A:", "alt_a")
            c_b = st.text_input("Alternativa B:", "alt_b")
            c_c = st.text_input("Alternativa C:", "alt_c")
        with col3:
            c_d = st.text_input("Alternativa D:", "alt_d")
            c_e = st.text_input("Alternativa E (se houver):", "alt_e")
            c_correta = st.text_input("Gabarito (Letra da Correta):", "correta")
        
        if st.button("📥 Iniciar Importação em Massa"):
            with st.spinner("Processando linhas do arquivo..."):
                from importador_internet import importar_banco_json_flexivel
                status = importar_banco_json_flexivel(nome_arquivo, c_materia, c_enunciado, c_a, c_b, c_c, c_d, c_e, c_correta)
                st.info(status)

    # ABA 4: LEITOR DE CADERNOS EM PDF
    with aba_pdf:
        st.header("📄 Conversor de Cadernos de Prova (PDF Multimatérias)")
        st.write("Envie o PDF de uma prova física escaneada. A IA usará visão computacional para ler as fotos das questões!")
        arquivo_enviado = st.file_uploader("Selecione o PDF da prova mista:", type=["pdf"], key="uploader_multimodal")
        
        if st.button("🚀 Processar e Separar PDF"):
            if arquivo_enviado is not None:
                with st.spinner("Analisando visualmente as páginas do PDF..."):
                    resultado_pdf = processar_prova_pdf_com_ia(arquivo_enviado)
                    st.info(resultado_pdf)
            else:
                st.error("Por favor, selecione um arquivo PDF válido.")

    # ABA 5: CAPTURADOR VIA LINK DO PCI CONCURSOS
    with aba_pci:
        st.header("🔍 Capturador Automático de Simulados PCI")
        st.write("Navegue no site do PCI, entre na página de um simulado, copie a URL do navegador e cole abaixo!")
        from pci_connector import sugar_simulado_pci_via_link
        url_digitada = st.text_input("Cole aqui a URL da página do simulado do PCI:", key="url_pci_input")
        
        if st.button("⚡ Sugar Simulado Inteiro para o Meu Sistema", key="btn_sugar_pci"):
            if url_digitada.strip():
                if "pciconcursos.com.br" in url_digitada:
                    with st.spinner("Extraindo os textos das questões do link e cadastrando com IA..."):
                        resultado_captura = sugar_simulado_pci_via_link(url_digitada)
                        st.success(resultado_captura)
                else:
                    st.error("⚠️ Insira uma URL válida do portal oficial do PCI Concursos.")

    # ABA 6: CADASTRO MANUAL OU COLAR TEXTO EM LOTE
    with aba_cadastro:
        st.header("📥 Importador de Provas por Texto (Massa)")
        st.write("Copie o texto completo de um bloco de questões de qualquer site e jogue na caixa abaixo para a IA catalogar de uma vez.")
        texto_lote = st.text_area("📋 Cole o texto do caderno de questões aqui:", height=300, placeholder="Cole as perguntas misturadas aqui...")
        
        if st.button("🚀 Processar e Separar Texto em Lote"):
            if texto_lote.strip():
                with st.spinner("Quebrando o bloco de texto e estruturando matérias..."):
                    resultado_massa = processar_texto_em_massa_com_ia(texto_lote)
                    st.info(resultado_massa)
            else:
                st.error("⚠️ A caixa de texto está vazia.")

    # ABA 7: CADERNO ELETRÔNICO DE ERROS
    with aba_erros:
        st.header("❌ Meu Caderno Eletrônico de Erros")
        st.write("Abaixo estão listadas automaticamente as questões onde a sua última tentativa de resposta foi um Erro.")
        
        conn = conectar_db()
        # Query refinada e travada para capturar erros apenas do usuário logado
        query_erros = f"""
            SELECT q.*, m.nome as nome_materia FROM questoes q
            JOIN materias m ON q.materia_id = m.id
            WHERE q.id IN (
                SELECT questao_id FROM historico 
                WHERE usuario_id = {st.session_state.usuario_id}
                GROUP BY questao_id 
                HAVING id = MAX(id) AND acertou = 0
            )
        """
        questoes_erradas = pd.read_sql_query(query_erros, conn)
        conn.close()
        
        if not questoes_erradas.empty:
            st.warning(f"Você possui atualmente {len(questoes_erradas)} questões pendentes de revisão.")
            
            if 'idx_caderno_erros' not in st.session_state:
                st.session_state.idx_caderno_erros = 0
                
            idx_e = st.session_state.idx_caderno_erros
            if idx_e >= len(questoes_erradas):
                idx_e = 0
                st.session_state.idx_caderno_erros = 0
                
            q_errada = questoes_erradas.iloc[idx_e]
            
            st.markdown(f"### 🔄 **Revisão: Questão {idx_e + 1} de {len(questoes_erradas)}**")
            
            assunto_err_cru = str(q_errada['assunto']).strip()
            sub_err = "Geral" if not assunto_err_cru or assunto_err_cru.lower() in ["none", "nan", "", "null"] else q_errada['assunto']
            
            # NOVO: Tratamento do rótulo da Banca no Caderno de Erros
            banca_err_cru = str(q_errada['banca']).strip() if 'banca' in q_errada.index else "Não identificada"
            banca_err_tela = "Não identificada" if not banca_err_cru or banca_err_cru.lower() in ["none", "nan", "", "null"] else banca_err_cru
            
            # Exibe na tela do caderno de erros reunindo a matéria, a banca e o assunto
            st.markdown(f"📚 **Matéria:** `{q_errada['nome_materia']}` | 🏢 **Banca:** `{banca_err_tela}` | 📌 **Assunto:** `{sub_err}`")

            
            st.info(q_errada['enunciado'])
            
            opcoes_b_e = [q_errada['alt_a'], q_errada['alt_b'], q_errada['alt_c'], q_errada['alt_d']]
            if q_errada['alt_e']: 
                opcoes_b_e.append(q_errada['alt_e'])
            
            letras_e = ["A) ", "B) ", "C) ", "D) ", "E) "]
            opcoes_f_e = []
            for i, opt in enumerate(opcoes_b_e):
                if opt:
                    txt = str(opt).strip()
                    if txt.upper().startswith(letras_e[i].strip().upper()):
                        opcoes_f_e.append(txt)
                    else:
                        opcoes_f_e.append(f"{letras_e[i]}{txt}")
                        
            resp_e = st.radio("Escolha a alternativa correta:", opcoes_f_e, key=f"radio_erro_{q_errada['id']}")
            
            col_er1, col_er2 = st.columns(2)
            with col_er1:
                if st.button("🎯 Responder Revanche", key=f"btn_err_{q_errada['id']}"):
                    letra_u_e = resp_e.strip().upper()
                    letra_g_e = str(q_errada['alternativa_correta']).strip().upper()
                    
                    acertou_e = 1 if letra_u_e == letra_g_e else 0
                    
                    conn = conectar_db()
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO historico (questao_id, resposta_usuario, acertou, usuario_id) VALUES (?, ?, ?, ?)",
                        (int(q_errada['id']), letra_u_e, acertou_e, int(st.session_state.usuario_id))
                    )
                    conn.commit()
                    conn.close()
                    
                    if acertou_e == 1:
                        st.success("🎉 Sensacional! Você superou o erro. A questão sairá deste caderno na próxima atualização!")
                    else:
                        st.error(f"❌ Resposta incorreta. O gabarito continua sendo: {letra_g_e}. Tente revisar a matéria.")
                        
            with col_er2:
                if st.button("Pular Questão ➡️", key="btn_pular_erro"):
                    st.session_state.idx_caderno_erros = (idx_e + 1) % len(questoes_erradas)
                    st.rerun()
        else:
            st.success("😎 Parabéns! Seu Caderno de Erros está totalmente zerado. Você está voando nos estudos!")

    # BLOCO EXCLUSIVO DA ABA 8 (SÓ CARREGA SE O USUÁRIO FOR O ADMIN)
    if st.session_state.username == "admin":
        aba_admin = abas[7] # Pega a oitava aba criada na lista dinâmica
        
        with aba_admin:
            st.header("🛠️ Painel de Controle do Administrador")
            st.write("Área restrita para manutenção do sistema. Cuidado: exclusões são permanentes!")
            
            # --- SEÇÃO 1: EXCLUSÃO DE MATÉRIAS ---
            st.subheader("📚 Gerenciar Matérias Cadastradas")
            
            # Busca as matérias atualizadas para o Admin escolher
            conn = conectar_db()
            df_mats_admin = pd.read_sql_query("SELECT * FROM materias", conn)
            conn.close()
            
            if not df_mats_admin.empty:
                materia_para_excluir = st.selectbox(
                    "Selecione a matéria que deseja apagar do sistema:",
                    df_mats_admin['nome'].tolist(),
                    key="sb_excluir_materia"
                )
                
                # Exibe um aviso explicando o impacto em cascata
                st.caption("⚠️ Nota: Apagar uma matéria também excluirá TODAS as questões e históricos vinculados a ela.")
                
                if st.button("🔴 Excluir Matéria Permanentemente", key="btn_excluir_materia"):
                    id_mat_excluir = df_mats_admin[df_mats_admin['nome'] == materia_para_excluir]['id'].values[0]
                    
                    conn = conectar_db()
                    cursor = conn.cursor()
                    
                    # 1. Apaga os históricos das questões dessa matéria
                    cursor.execute(f"DELETE FROM historico WHERE questao_id IN (SELECT id FROM questoes WHERE materia_id = {id_mat_excluir})")
                    # 2. Apaga as questões da matéria
                    cursor.execute(f"DELETE FROM questoes WHERE materia_id = {id_mat_excluir}")
                    # 3. Apaga a matéria em si
                    cursor.execute(f"DELETE FROM materias WHERE id = {id_mat_excluir}")
                    
                    conn.commit()
                    conn.close()
                    st.success(f"Matéria '{materia_para_excluir}' e todos os seus vínculos foram apagados!")
                    st.rerun()
            else:
                st.info("Nenhuma matéria cadastrada no banco de dados.")
                
            st.markdown("---")
            
            # --- SEÇÃO 2: EXCLUSÃO DE USUÁRIOS ---
            st.subheader("👤 Gerenciar Usuários do Sistema")
            
            # Busca a lista de todos os usuários registrados, exceto o próprio admin
            conn = conectar_db()
            df_users_admin = pd.read_sql_query("SELECT id, username FROM usuarios WHERE username != 'admin'", conn)
            conn.close()
            
            if not df_users_admin.empty:
                user_para_excluir = st.selectbox(
                    "Selecione o usuário que deseja remover:",
                    df_users_admin['username'].tolist(),
                    key="sb_excluir_usuario"
                )
                
                st.caption("⚠️ Nota: Deletar o usuário apagará também todo o histórico de resoluções e o caderno de erros dele.")
                
                if st.button("🔴 Excluir Usuário Permanentemente", key="btn_excluir_usuario"):
                    id_user_excluir = df_users_admin[df_users_admin['username'] == user_para_excluir]['id'].values[0]
                    
                    conn = conectar_db()
                    cursor = conn.cursor()
                    
                    # 1. Apaga o histórico de desempenho desse usuário específico
                    cursor.execute(f"DELETE FROM historico WHERE usuario_id = {id_user_excluir}")
                    # 2. Apaga a conta do usuário da tabela de credenciais
                    cursor.execute(f"DELETE FROM usuarios WHERE id = {id_user_excluir}")
                    
                    conn.commit()
                    conn.close()
                    st.success(f"O usuário '{user_para_excluir}' foi removido com sucesso do sistema!")
                    st.rerun()
            else:
                st.info("Não há outros usuários comuns cadastrados além de você (admin).")
