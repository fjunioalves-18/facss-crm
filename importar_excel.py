import sqlite3
import pandas as pd
import math

def conectar_db():
    return sqlite3.connect('facss_crm.db')

def limpa_nan(valor):
    if pd.isna(valor) or valor == '-' or valor == 'NaN':
        return None
    if isinstance(valor, float) and math.isnan(valor):
        return None
    return str(valor).strip()

print("⚡ Iniciando a Injeção Completa de Dados do Excel...")
arquivo_excel = 'FACSS - CRM Otimizado.xlsx'

try:
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS tb_os")
    cursor.execute("""
    CREATE TABLE tb_os (
        id_os INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_os TEXT NOT NULL,
        id_cliente INTEGER,
        solicitante TEXT,
        data_abertura TEXT,
        criticidade TEXT,
        analista TEXT,
        descricao_demanda TEXT,
        sla_objetivo TEXT,
        status_os TEXT,
        solucao_comentario TEXT,
        FOREIGN KEY (id_cliente) REFERENCES tb_clientes(id_cliente)
    );
    """)

    cursor.execute("DROP TABLE IF EXISTS tb_modulos")
    cursor.execute("""
    CREATE TABLE tb_modulos (
        id_modulo INTEGER PRIMARY KEY AUTOINCREMENT,
        placa TEXT NOT NULL,
        marca TEXT,
        modelo TEXT,
        id_modulo_equip TEXT,
        id_cliente INTEGER,
        chip TEXT,
        num_chip TEXT,
        data_instalacao TEXT,
        data_desativacao TEXT,
        situacao TEXT DEFAULT 'ATIVO',
        observacao TEXT,
        FOREIGN KEY (id_cliente) REFERENCES tb_clientes(id_cliente)
    );
    """)

    print("📖 Lendo as abas: Clientes, Pipeline, Controle de OS e Módulos...")
    df_clientes = pd.read_excel(arquivo_excel, sheet_name='Clientes')
    df_pipeline = pd.read_excel(arquivo_excel, sheet_name='Pipeline')
    df_os = pd.read_excel(arquivo_excel, sheet_name='Controle de OS')
    df_modulos = pd.read_excel(arquivo_excel, sheet_name='Módulos')

    cursor.execute("DELETE FROM tb_pipeline")
    cursor.execute("DELETE FROM tb_clientes")

    # 1. Injetando Clientes
    print("👥 Injetando Clientes na base de dados...")
    for index, row in df_clientes.iterrows():
        nome = limpa_nan(row.get('Cliente'))
        if not nome: continue
        
        cursor.execute("""
            INSERT INTO tb_clientes (
                nome_empresa, cnpj, contato_nome, telefone, email, 
                status, faturamento, responsavel, health_score, nivel_acesso
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nome,
            limpa_nan(row.get('CNPJ')),
            limpa_nan(row.get('Contato')),
            limpa_nan(row.get('Telefone')),
            limpa_nan(row.get('E-mail')),
            limpa_nan(row.get('Status')),
            limpa_nan(row.get('Faturamento')),
            limpa_nan(row.get('Resp.')),
            limpa_nan(row.get('Health')),
            limpa_nan(row.get('Nível de acesso'))
        ))

    # 2. Injetando Pipeline
    print("🎯 Injetando Pipeline (Leads)...")
    for index, row in df_pipeline.iterrows():
        empresa = limpa_nan(row.get('Empresa'))
        if not empresa: continue
        
        cursor.execute("""
            INSERT INTO tb_pipeline (
                prioridade, empresa, segmento, uf_regiao, decisor, 
                canal_aquisicao, estagio, proxima_acao, dor_gancho
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            limpa_nan(row.get('Prioridade')),
            empresa,
            limpa_nan(row.get('Segmento')),
            limpa_nan(row.get('UF/Região')),
            limpa_nan(row.get('Decisor-alvo')),
            limpa_nan(row.get('Canal')),
            limpa_nan(row.get('Estágio')),
            limpa_nan(row.get('Próxima ação')),
            limpa_nan(row.get('Dor / Gancho'))
        ))

    # 3. Injetando Ordens de Serviço
    print("🛠️ Injetando Ordens de Serviço...")
    for index, row in df_os.iterrows():
        numero_os = limpa_nan(row.get('Nº DA OS'))
        if not numero_os: continue
        
        empresa_os = limpa_nan(row.get('EMPRESA'))
        id_cli = None
        if empresa_os:
            cursor.execute("SELECT id_cliente FROM tb_clientes WHERE nome_empresa LIKE ?", ('%'+empresa_os+'%',))
            res = cursor.fetchone()
            if res: id_cli = res[0]

        cursor.execute("""
            INSERT INTO tb_os (
                numero_os, id_cliente, solicitante, data_abertura, 
                criticidade, analista, descricao_demanda, status_os, solucao_comentario
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            numero_os,
            id_cli,
            limpa_nan(row.get('SOLICITANTE')),
            limpa_nan(row.get('DATA')),
            limpa_nan(row.get('CRITICIDADE')),
            limpa_nan(row.get('ANALISTA')),
            limpa_nan(row.get('DESCRIÇÃO DA DEMANDA')),
            limpa_nan(row.get('STATUS')),
            limpa_nan(row.get('SOLUÇÃO/COMENTÁRIOS/EVOLUÇÃO'))
        ))

    # 4. Injetando Módulos / Frota
    print("🚛 Injetando Módulos e Equipamentos da Frota...")
    for index, row in df_modulos.iterrows():
        placa = limpa_nan(row.get('PLACA'))
        if not placa: continue
        
        empresa_mod = limpa_nan(row.get('EMPRESA'))
        id_cli = None
        if empresa_mod:
            cursor.execute("SELECT id_cliente FROM tb_clientes WHERE nome_empresa LIKE ?", ('%'+empresa_mod+'%',))
            res = cursor.fetchone()
            if res: id_cli = res[0]

        data_inst = limpa_nan(row.get('Data Instalação'))
        if data_inst and ' ' in str(data_inst):
            data_inst = str(data_inst).split(' ')[0]

        cursor.execute("""
            INSERT INTO tb_modulos (
                placa, marca, modelo, id_modulo_equip, id_cliente, 
                chip, data_instalacao, situacao
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            placa,
            limpa_nan(row.get('Marca')),
            limpa_nan(row.get('Modelo')),
            limpa_nan(row.get('ID Módulo Atual')),
            id_cli,
            limpa_nan(row.get('Chip')),
            data_inst,
            limpa_nan(row.get('Situação')) or 'ATIVO'
        ))

    conn.commit()
    conn.close()
    print("\n✅ MÁGICA COMPLETA CONCLUÍDA! Clientes, Leads, OSs e a Frota foram importados!")

except Exception as e:
    print(f"\n🚨 ERRO: Não foi possível importar. Detalhe: {e}")