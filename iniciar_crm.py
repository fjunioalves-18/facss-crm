import sqlite3

def conectar_db():
    return sqlite3.connect('facss_crm.db')

print("⚡ Iniciando a criação do banco de dados FACSS CRM...")

conn = conectar_db()
cursor = conn.cursor()

# 1. TABELA DE CLIENTES (Baseada na sua planilha)
cursor.execute("""
CREATE TABLE IF NOT EXISTS tb_clientes (
    id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_empresa TEXT NOT NULL,
    cnpj TEXT UNIQUE,
    contato_nome TEXT,
    telefone TEXT,
    email TEXT,
    status TEXT,           -- Ex: Ativo, Churn, POC Sem Evolução
    faturamento TEXT,      -- Ex: Faturando, Inativo
    responsavel TEXT,      -- Ex: Diego, etc.
    health_score TEXT,     -- Ex: 🟢 Saudável, 🟡 Atenção, 🔴 Crítico
    nivel_acesso TEXT,
    data_inicio TEXT,
    ultima_interacao TEXT
);
""")

# 2. TABELA DE PIPELINE (Funil de Vendas)
cursor.execute("""
CREATE TABLE IF NOT EXISTS tb_pipeline (
    id_lead INTEGER PRIMARY KEY AUTOINCREMENT,
    prioridade TEXT,       -- Ex: A, B, C
    empresa TEXT NOT NULL,
    segmento TEXT,
    uf_regiao TEXT,
    decisor TEXT,
    canal_aquisicao TEXT,
    estagio TEXT,          -- Ex: Lead, Reunião Agendada, Negociação, Fechado
    proxima_acao TEXT,
    data_proxima_acao TEXT,
    dor_gancho TEXT
);
""")

# 3. TABELA DE ORDENS DE SERVIÇO (Controle de OS / Chamados)
cursor.execute("""
CREATE TABLE IF NOT EXISTS tb_os (
    id_os INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_os TEXT UNIQUE NOT NULL,
    id_cliente INTEGER,
    solicitante TEXT,
    data_abertura TEXT,
    criticidade TEXT,      -- Ex: Alta, Média, Baixa
    analista TEXT,
    descricao_demanda TEXT,
    sla_objetivo TEXT,
    status_os TEXT,        -- Ex: Aberto, Em Andamento, Finalizado
    solucao_comentario TEXT,
    FOREIGN KEY (id_cliente) REFERENCES tb_clientes(id_cliente)
);
""")

conn.commit()
conn.close()

print("✅ SUCESSO! Estrutura do FACSS CRM criada. Bem-vindo à sua nova Software House!")