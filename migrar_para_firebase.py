import sqlite3
import firebase_admin
from firebase_admin import credentials, firestore

# Inicializa Firebase
cred = credentials.Certificate('firebase_credentials.json')
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

# Conecta ao SQLite transformando linhas em dicionários automáticos
conn = sqlite3.connect('facss_crm.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

tabelas = ['tb_clientes', 'tb_modulos', 'tb_os', 'tb_pipeline', 'tb_usuarios', 'tb_interacoes']

print("🚀 Iniciando migração para o Firebase Cloud...\n")

for tabela in tabelas:
    try:
        cursor.execute(f"SELECT * FROM {tabela}")
        rows = cursor.fetchall()
        
        if not rows:
            print(f"ℹ️ Tabela '{tabela}' está vazia. Pulando...")
            continue

        batch = db.batch()
        count = 0
        
        for row in rows:
            doc_data = dict(row)
            # Pega a chave primária (primeira coluna) como ID do documento
            doc_id = str(list(doc_data.values())[0])
            
            doc_ref = db.collection(tabela).document(doc_id)
            batch.set(doc_ref, doc_data)
            count += 1
            
            # Envia em lotes de 400 itens para não sobrecarregar
            if count % 400 == 0:
                batch.commit()
                batch = db.batch()

        # Envia o restante do lote
        batch.commit()
        print(f"✅ {len(rows)} registros de '{tabela}' migrados com sucesso!")

    except Exception as e:
        print(f"⚠️ Erro ao migrar a tabela '{tabela}': {e}")

conn.close()
print("\n🎉 Migração 100% concluída na nuvem!")