from flask import Flask, render_template, request, redirect, session, url_for, flash
import firebase_admin
from firebase_admin import credentials, firestore
import time
import os
import requests
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'facss_crm_chave_secreta_super_segura')

# ==========================================
# 1. INICIALIZAÇÃO FIREBASE CLOUD FIRESTORE
# ==========================================
cred_path = '/etc/secrets/firebase_credentials.json' if os.path.exists('/etc/secrets/firebase_credentials.json') else 'firebase_credentials.json'

if not firebase_admin._apps:
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    else:
        print(f"[AVISO FIREBASE] Credenciais não encontradas em: {cred_path}")

db = firestore.client()

# ==========================================
# 2. CONFIGURAÇÃO DE E-MAIL
# ==========================================
EMAIL_EMPRESA = os.environ.get('EMAIL_EMPRESA', 'flavio.alves@facss.com.br')
SENHA_EMPRESA_RAW = os.environ.get('SENHA_EMPRESA', 'cytf glim frms pqen')
SENHA_EMPRESA = SENHA_EMPRESA_RAW.replace(" ", "").strip()

# ==========================================
# 3. FUNÇÕES DE ENVIO DE E-MAIL (SSL PORTA 465)
# ==========================================
def enviar_email_html(destinatarios, assunto, corpo_html):
    if isinstance(destinatarios, str):
        destinatarios = [destinatarios]
    validos = [e for e in destinatarios if e and '@' in str(e).strip()]
    if not validos:
        print("❌ [EMAIL] Nenhum destinatário válido informado.")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = f"FACSS CRM <{EMAIL_EMPRESA}>"
        msg['To'] = ", ".join(validos)
        msg['Subject'] = assunto
        msg.attach(MIMEText(corpo_html, 'html'))

        # Conexão SSL direta na porta 465 (Compatível com Render)
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15)
        server.login(EMAIL_EMPRESA, SENHA_EMPRESA)
        server.send_message(msg)
        server.quit()
        print(f"✅ [EMAIL] E-mail enviado com sucesso para: {validos}")
        return True
    except Exception as e:
        print(f"❌ [ERRO DISPARO E-MAIL]: {e}")
        return False

def disparar_email_boas_vindas(email, nome, senha):
    corpo = f"""
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #f8fafc; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden;">
                <div style="background: #06110e; padding: 25px; text-align: center; border-bottom: 3px solid #2ba870;">
                    <h1 style="color: #ffffff; margin: 0; font-size: 24px;">FACSS CRM</h1>
                </div>
                <div style="padding: 30px; color: #1e293b;">
                    <h2 style="color: #2ba870; font-size: 18px;">Bem-vindo(a), {nome}!</h2>
                    <p style="font-size: 14px; color: #475569;">Seu cadastro no portal foi concluído com sucesso.</p>
                    <div style="background: #0f221e; padding: 18px; border-radius: 8px; border-left: 4px solid #2ba870; margin: 20px 0;">
                        <p style="margin: 0 0 6px 0; color: #f1f5f9;"><strong>E-mail:</strong> {email}</p>
                        <p style="margin: 0; color: #829a92;"><strong>Senha Inicial:</strong> {senha}</p>
                    </div>
                </div>
            </div>
        </body>
    </html>
    """
    return enviar_email_html(email, "Bem-vindo(a) ao FACSS CRM - Confirmação de Acesso", corpo)

def disparar_email_recuperacao(email, nome, senha):
    corpo = f"""
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #f8fafc; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden;">
                <div style="background: #06110e; padding: 25px; text-align: center; border-bottom: 3px solid #c49b66;">
                    <h1 style="color: #ffffff; margin: 0; font-size: 24px;">FACSS CRM</h1>
                </div>
                <div style="padding: 30px; color: #1e293b;">
                    <h2 style="color: #c49b66; font-size: 18px;">Recuperação de Acesso</h2>
                    <p style="font-size: 14px; color: #475569;">Olá, {nome}. Você solicitou os dados de acesso da sua conta.</p>
                    <div style="background: #0f221e; padding: 18px; border-radius: 8px; border-left: 4px solid #c49b66; margin: 20px 0;">
                        <p style="margin: 0 0 6px 0; color: #f1f5f9;"><strong>E-mail:</strong> {email}</p>
                        <p style="margin: 0; color: #c49b66;"><strong>Sua Senha Atual:</strong> {senha}</p>
                    </div>
                </div>
            </div>
        </body>
    </html>
    """
    return enviar_email_html(email, "Recuperação de Senha - FACSS CRM", corpo)

def get_collection(col_name):
    try:
        docs = db.collection(col_name).stream()
        return [doc.to_dict() | {'_id': doc.id} for doc in docs]
    except Exception as e:
        print(f"[ERRO FIRESTORE] Falha ao buscar coleção {col_name}: {e}")
        return []

# ==========================================
# 4. AUTENTICAÇÃO E SESSÃO DINÂMICA
# ==========================================
@app.before_request
def verificar_login():
    rotas_livres = ['login', 'primeiro_acesso', 'recuperar_senha', 'static']
    if 'usuario_id' not in session and request.endpoint not in rotas_livres:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    erro = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '').strip()
        
        # 1. ACESSO MESTRE DE EMERGÊNCIA (Bypassa a cota 429 do Firebase)
        if email == 'flavio.alves@facss.com.br' and senha == 'Facss2026':
            session['usuario_id'] = 'master_admin'
            session['usuario_nome'] = 'Flávio Alves'
            session['usuario_cargo'] = 'Gestor de Operações'
            session['usuario_email'] = email
            return redirect('/')

        # 2. BUSCA OTIMIZADA NO FIRESTORE (Lê apenas 1 documento em vez da coleção inteira)
        try:
            if db:
                docs = db.collection('tb_usuarios').where('email', '==', email).stream()
                user = next((doc.to_dict() | {'_id': doc.id} for doc in docs if str(doc.to_dict().get('senha')) == senha), None)
                if user:
                    session['usuario_id'] = user['_id']
                    session['usuario_nome'] = user.get('nome', 'Usuário')
                    session['usuario_cargo'] = user.get('cargo', 'Operações')
                    session['usuario_email'] = user.get('email')
                    return redirect('/')
        except Exception as e:
            print(f"[ERRO LOGIN FIRESTORE] {e}")

        erro = "E-mail ou senha incorretos."
            
    return render_template('login.html', erro=erro)

@app.route('/primeiro_acesso', methods=['POST'])
def primeiro_acesso():
    nome = request.form.get('nome', '').strip()
    email = request.form.get('email', '').strip().lower()
    senha = request.form.get('senha', '').strip()
    
    usuarios = get_collection('tb_usuarios')
    if any(str(u.get('email', '')).lower() == email for u in usuarios):
        flash("Este e-mail já possui cadastro. Faça login ou solicite recuperação de senha.", "danger")
        return redirect('/login')
        
    doc_ref = db.collection('tb_usuarios').document()
    hoje_str = datetime.now().strftime('%d/%m/%Y')
    doc_ref.set({
        'id_usuario': doc_ref.id,
        'nome': nome,
        'email': email,
        'senha': senha,
        'cargo': 'Analista / Operações',
        'empresa': 'FACSS',
        'status': 'Ativo',
        'data_criacao': hoje_str,
        'ultimo_login': hoje_str
    })
    
    disparar_email_boas_vindas(email, nome, senha)
    flash(f"Conta criada com sucesso, {nome}! Você já pode acessar.", "success")
    return redirect('/login')

@app.route('/recuperar_senha', methods=['POST'])
def recuperar_senha():
    email = request.form.get('email', '').strip().lower()
    usuarios = get_collection('tb_usuarios')
    user = next((u for u in usuarios if str(u.get('email', '')).lower() == email), None)
    
    if user:
        disparar_email_recuperacao(email, user.get('nome', 'Usuário'), user.get('senha', '---'))
        flash("Instruções de recuperação enviadas para o seu e-mail!", "success")
    else:
        flash("E-mail não encontrado na base de dados.", "danger")
        
    return redirect('/login')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==========================================
# 5. DASHBOARD E OPERAÇÕES
# ==========================================
@app.route('/')
def home():
    clientes = get_collection('tb_clientes')
    pipeline = get_collection('tb_pipeline')
    ordens = get_collection('tb_os')

    total_ativos = sum(1 for c in clientes if c.get('status') == 'Ativo')
    total_atencao = sum(1 for c in clientes if 'Atenção' in str(c.get('health_score')) or 'Risco' in str(c.get('health_score')))
    total_leads = len(pipeline)
    os_abertas = sum(1 for o in ordens if str(o.get('status_os')).upper() not in ['FINALIZADO', 'CONCLUÍDO', 'ATENDIDO'])

    cnt_saudavel = sum(1 for c in clientes if 'Saudável' in str(c.get('health_score')))
    cnt_atencao = sum(1 for c in clientes if 'Atenção' in str(c.get('health_score')))
    cnt_risco = sum(1 for c in clientes if 'Risco' in str(c.get('health_score')))
    cnt_semdados = len(clientes) - (cnt_saudavel + cnt_atencao + cnt_risco)

    analistas_dict = {}
    for o in ordens:
        an = o.get('analista')
        if an: analistas_dict[an] = analistas_dict.get(an, 0) + 1

    labels_analistas = list(analistas_dict.keys())[:5]
    qtd_analistas = [analistas_dict[k] for k in labels_analistas]

    os_criticas = sum(1 for o in ordens if 'Alta' in str(o.get('criticidade')) and str(o.get('status_os')).upper() not in ['FINALIZADO', 'CONCLUÍDO', 'ATENDIDO'])
    data_limite = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    clientes_sem_contato = sum(1 for c in clientes if c.get('status') == 'Ativo' and (not c.get('ultima_interacao') or str(c.get('ultima_interacao')) < data_limite))

    return render_template('index.html', total_ativos=total_ativos, total_atencao=total_atencao, total_leads=total_leads, os_abertas=os_abertas, os_criticas=os_criticas, clientes_sem_contato=clientes_sem_contato, health_chart=[cnt_saudavel, cnt_atencao, cnt_risco, cnt_semdados], labels_analistas=labels_analistas, qtd_analistas=qtd_analistas, active_tab='dash')

@app.route('/clientes')
def clientes():
    busca = request.args.get('busca', '').lower()
    raw_clientes = get_collection('tb_clientes')
    lista = []
    for c in raw_clientes:
        if busca:
            if not (busca in str(c.get('nome_empresa', '')).lower() or busca in str(c.get('cnpj', '')).lower() or busca in str(c.get('responsavel', '')).lower()):
                continue
        lista.append((c['_id'], c.get('nome_empresa'), c.get('cnpj'), c.get('contato_nome'), c.get('telefone'), c.get('status', 'Ativo'), c.get('health_score', ''), c.get('responsavel', '')))
    return render_template('clientes.html', clientes=lista, active_tab='clientes', busca=busca)

@app.route('/novo_cliente')
def novo_cliente(): return render_template('cadastro_cliente.html', active_tab='clientes')

@app.route('/salvar_cliente', methods=['POST'])
def salvar_cliente():
    doc_ref = db.collection('tb_clientes').document()
    doc_ref.set({
        'id_cliente': doc_ref.id, 'nome_empresa': request.form.get('nome', ''), 'cnpj': request.form.get('cnpj', ''),
        'contato_nome': request.form.get('contato', ''), 'telefone': request.form.get('telefone', ''),
        'email': request.form.get('email', ''), 'status': request.form.get('status', 'Ativo'),
        'responsavel': request.form.get('responsavel', ''), 'health_score': request.form.get('health', ''),
        'nivel_acesso': request.form.get('nivel_acesso', ''), 'faturamento': request.form.get('faturamento', '')
    })
    flash("Cliente cadastrado!", "success")
    return redirect('/clientes')

@app.route('/editar_cliente/<string:id>')
def editar_cliente(id):
    doc = db.collection('tb_clientes').document(str(id)).get()
    c = doc.to_dict() if doc.exists else {}
    cliente = (id, c.get('nome_empresa'), c.get('cnpj'), c.get('contato_nome'), c.get('telefone'), c.get('email'), c.get('status'), c.get('responsavel'), c.get('health_score'), c.get('nivel_acesso'), c.get('faturamento'))
    return render_template('editar_cliente.html', cliente=cliente, active_tab='clientes')

@app.route('/atualizar_cliente', methods=['POST'])
def atualizar_cliente():
    id_cliente = request.form.get('id_cliente')
    db.collection('tb_clientes').document(str(id_cliente)).update({
        'nome_empresa': request.form.get('nome') or request.form.get('nome_empresa'),
        'cnpj': request.form.get('cnpj'), 'contato_nome': request.form.get('contato') or request.form.get('contato_nome'),
        'telefone': request.form.get('telefone'), 'email': request.form.get('email'), 'status': request.form.get('status'),
        'responsavel': request.form.get('responsavel'), 'health_score': request.form.get('health') or request.form.get('health_score'),
        'faturamento': request.form.get('faturamento'), 'nivel_acesso': request.form.get('nivel_acesso')
    })
    flash("Cliente atualizado!", "success")
    return redirect('/clientes')

@app.route('/cliente/<string:id>')
def ficha_cliente(id):
    doc = db.collection('tb_clientes').document(str(id)).get()
    c = doc.to_dict() if doc.exists else {}
    cliente = (id, c.get('nome_empresa'), c.get('cnpj'), c.get('contato_nome'), c.get('telefone'), c.get('email'), c.get('status'), c.get('responsavel'), c.get('health_score'), c.get('nivel_acesso'), c.get('faturamento'), c.get('ultima_interacao'))
    interacoes = [(i['_id'], i.get('data'), i.get('responsavel'), i.get('tipo'), i.get('observacao'), i.get('proximo_passo')) for i in get_collection('tb_interacoes') if str(i.get('id_cliente')) == str(id)]
    modulos = [(m['_id'], m.get('placa'), m.get('marca'), m.get('modelo'), m.get('id_modulo_equip'), m.get('chip'), m.get('num_chip'), m.get('data_instalacao'), m.get('data_desativacao'), m.get('situacao')) for m in get_collection('tb_modulos') if str(m.get('id_cliente')) == str(id)]
    return render_template('ficha_cliente.html', cliente=cliente, interacoes=interacoes, modulos=modulos, active_tab='clientes')

@app.route('/salvar_interacao', methods=['POST'])
def salvar_interacao():
    id_cliente = request.form.get('id_cliente')
    data_hoje = datetime.now().strftime('%Y-%m-%d')
    doc_ref = db.collection('tb_interacoes').document()
    doc_ref.set({
        'id_interacao': doc_ref.id, 'id_cliente': id_cliente, 'data': data_hoje,
        'responsavel': request.form.get('responsavel', ''), 'tipo': request.form.get('tipo', ''),
        'observacao': request.form.get('observacao', ''), 'proximo_passo': request.form.get('proximo_passo', '')
    })
    db.collection('tb_clientes').document(str(id_cliente)).update({'ultima_interacao': data_hoje})
    return redirect(f'/cliente/{id_cliente}')

@app.route('/modulos')
def modulos():
    raw_modulos = get_collection('tb_modulos')
    clientes_dict = {c['_id']: c.get('nome_empresa') for c in get_collection('tb_clientes')}
    modulos_tratados = []
    for m in raw_modulos:
        placa_raw = str(m.get('placa', '')).strip()
        modulos_tratados.append({
            'id': m['_id'], 'placa_raw': placa_raw, 'placa_limpa': placa_raw, 'padrao_identificador': placa_raw,
            'marca_modelo': f"{m.get('marca', '')} {m.get('modelo', '')}".strip(), 'id_equip': str(m.get('id_modulo_equip', '')),
            'cliente': clientes_dict.get(str(m.get('id_cliente')), 'Estoque / Sem vínculo'), 'situacao': str(m.get('situacao', 'ATIVO')).upper()
        })
    return render_template('modulos.html', modulos=modulos_tratados, active_tab='modulos')

@app.route('/novo_modulo')
def novo_modulo():
    clientes = [(c['_id'], c.get('nome_empresa')) for c in get_collection('tb_clientes')]
    return render_template('cadastro_modulo.html', clientes=clientes, active_tab='modulos')

@app.route('/salvar_modulo', methods=['POST'])
def salvar_modulo():
    doc_ref = db.collection('tb_modulos').document()
    doc_ref.set({
        'id_modulo': doc_ref.id, 'placa': request.form.get('placa', ''), 'marca': request.form.get('marca', ''),
        'modelo': request.form.get('modelo', ''), 'id_modulo_equip': request.form.get('id_modulo_equip', ''),
        'id_cliente': request.form.get('id_cliente') or None, 'chip': request.form.get('chip', ''),
        'num_chip': request.form.get('num_chip', ''), 'data_instalacao': request.form.get('data_instalacao', ''),
        'data_desativacao': None, 'situacao': 'ATIVO'
    })
    return redirect('/modulos')

@app.route('/editar_modulo/<string:id>')
def editar_modulo(id):
    doc = db.collection('tb_modulos').document(str(id)).get()
    modulo = doc.to_dict() | {'_id': doc.id} if doc.exists else {}
    clientes = [(c['_id'], c.get('nome_empresa')) for c in get_collection('tb_clientes')]
    return render_template('editar_modulo.html', modulo=modulo, clientes=clientes, active_tab='modulos')

@app.route('/atualizar_modulo', methods=['POST'])
def atualizar_modulo():
    id_modulo = request.form.get('id_modulo')
    db.collection('tb_modulos').document(str(id_modulo)).update({
        'placa': request.form.get('placa', ''), 'marca': request.form.get('marca', ''), 'modelo': request.form.get('modelo', ''),
        'id_modulo_equip': request.form.get('id_modulo_equip', ''), 'id_cliente': request.form.get('id_cliente') or None,
        'chip': request.form.get('chip', ''), 'num_chip': request.form.get('num_chip', ''),
        'data_instalacao': request.form.get('data_instalacao', ''), 'data_desativacao': request.form.get('data_desativacao', ''),
        'situacao': request.form.get('situacao', 'ATIVO')
    })
    return redirect('/modulos')

@app.route('/pipeline')
@app.route('/pipeline_kanban')
def pipeline():
    lista_leads = get_collection('tb_pipeline')
    funil = {'Leads Iniciais': [], 'Contato Feito': [], 'Diagnóstico / Reunião': [], 'Proposta Enviada': [], 'Negociação': []}
    for lead in lista_leads:
        estagio = str(lead.get('estagio', '')).strip().lower()
        item = (lead['_id'], lead.get('prioridade'), lead.get('empresa'), lead.get('segmento'), lead.get('decisor'), lead.get('canal_aquisicao'), lead.get('estagio'), lead.get('proxima_acao'))
        if 'contato' in estagio: funil['Contato Feito'].append(item)
        elif 'diagn' in estagio or 'reuni' in estagio: funil['Diagnóstico / Reunião'].append(item)
        elif 'proposta' in estagio: funil['Proposta Enviada'].append(item)
        elif 'negoc' in estagio or 'fechado' in estagio: funil['Negociação'].append(item)
        else: funil['Leads Iniciais'].append(item)
    return render_template('pipeline_kanban.html', funil=funil, active_tab='kanban')

@app.route('/novo_lead')
def novo_lead(): return render_template('cadastro_lead.html', active_tab='kanban')

@app.route('/salvar_lead', methods=['POST'])
def salvar_lead():
    doc_ref = db.collection('tb_pipeline').document()
    doc_ref.set({
        'id_lead': doc_ref.id, 'empresa': request.form.get('empresa', ''), 'prioridade': request.form.get('prioridade', ''),
        'segmento': request.form.get('segmento', ''), 'canal_aquisicao': request.form.get('canal', ''),
        'estagio': request.form.get('estagio', ''), 'proxima_acao': request.form.get('proxima', '')
    })
    return redirect('/pipeline')

@app.route('/mover_lead/<string:id>/<direcao>')
def mover_lead(id, direcao):
    ordem = ['Lead', 'Contato feito', 'Diagnóstico agendado', 'Proposta enviada', 'Negociação']
    doc_ref = db.collection('tb_pipeline').document(str(id))
    doc = doc_ref.get()
    if doc.exists:
        estagio_atual = doc.to_dict().get('estagio', 'Lead')
        try:
            idx = ordem.index(estagio_atual)
            if direcao == 'frente' and idx < len(ordem) - 1: novo = ordem[idx + 1]
            elif direcao == 'tras' and idx > 0: novo = ordem[idx - 1]
            else: novo = estagio_atual
            doc_ref.update({'estagio': novo})
        except: pass
    return redirect('/pipeline')

@app.route('/os')
def ordens_servico():
    raw_os = get_collection('tb_os')
    clientes_dict = {c['_id']: c.get('nome_empresa') for c in get_collection('tb_clientes')}
    lista = []
    for o in raw_os:
        c_nome = clientes_dict.get(str(o.get('id_cliente')), 'Cliente Indefinido')
        lista.append((o['_id'], o.get('numero_os'), c_nome, o.get('solicitante'), o.get('criticidade'), o.get('analista'), o.get('status_os'), o.get('descricao_demanda')))
    return render_template('os.html', ordens=lista, active_tab='os')

@app.route('/nova_os')
def nova_os():
    clientes = [(c['_id'], c.get('nome_empresa')) for c in get_collection('tb_clientes')]
    analistas = [(u.get('nome'), u.get('email')) for u in get_collection('tb_usuarios') if u.get('status', 'Ativo') == 'Ativo']
    numero_gerado = f"{datetime.now().strftime('%Y')}{int(time.time())}"
    return render_template('cadastro_os.html', active_tab='os', clientes=clientes, analistas=analistas, num_os=numero_gerado)

@app.route('/salvar_os', methods=['POST'])
def salvar_os():
    doc_ref = db.collection('tb_os').document()
    id_cliente = request.form.get('id_cliente', '')
    analista_nome = request.form.get('analista', '')
    numero_os = request.form.get('numero_os', '')
    descricao = request.form.get('descricao', '')

    doc_ref.set({
        'id_os': doc_ref.id,
        'numero_os': numero_os,
        'id_cliente': id_cliente,
        'solicitante': request.form.get('solicitante', ''),
        'data_abertura': datetime.now().strftime('%Y-%m-%d'),
        'motivo': request.form.get('motivo', 'Suporte Técnico'),
        'criticidade': request.form.get('criticidade', 'BAIXA'),
        'analista': analista_nome,
        'status_os': request.form.get('status', 'ABERTO'),
        'descricao_demanda': descricao
    })

    cliente_doc = db.collection('tb_clientes').document(str(id_cliente)).get()
    c_email = cliente_doc.to_dict().get('email') if cliente_doc.exists else None
    c_nome = cliente_doc.to_dict().get('nome_empresa') if cliente_doc.exists else "Cliente"

    usuarios = get_collection('tb_usuarios')
    a_email = next((u.get('email') for u in usuarios if u.get('nome') == analista_nome), None)

    destinatarios = [e for e in [c_email, a_email, 'flavio.alves@facss.com.br'] if e]
    if destinatarios:
        corpo_os = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f8fafc; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden;">
                    <div style="background: #06110e; padding: 25px; text-align: center; border-bottom: 3px solid #2ba870;">
                        <h1 style="color: #ffffff; margin: 0; font-size: 24px;">FACSS CRM</h1>
                    </div>
                    <div style="padding: 30px; color: #1e293b;">
                        <h2 style="color: #2ba870; font-size: 18px;">Nova Ordem de Serviço Registrada</h2>
                        <p style="font-size: 14px; color: #475569;">Atendimento aberto para <strong>{c_nome}</strong>.</p>
                        <div style="background: #0f221e; padding: 20px; border-radius: 8px; border-left: 4px solid #2ba870; margin: 20px 0;">
                            <p style="margin: 0 0 8px 0; color: #f1f5f9;"><strong>OS N°:</strong> #{numero_os}</p>
                            <p style="margin: 0 0 8px 0; color: #829a92;"><strong>Motivo:</strong> {request.form.get('motivo')}</p>
                            <p style="margin: 0 0 8px 0; color: #829a92;"><strong>Criticidade:</strong> {request.form.get('criticidade')}</p>
                            <p style="margin: 0; color: #829a92;"><strong>Descrição:</strong><br>{descricao}</p>
                        </div>
                    </div>
                </div>
            </body>
        </html>
        """
        enviar_email_html(destinatarios, f"Nova Ordem de Serviço: OS #{numero_os} - FACSS", corpo_os)

    flash(f"OS #{numero_os} salva com sucesso!", "success")
    return redirect('/os')

@app.route('/atender_os/<string:id>')
def atender_os(id):
    doc = db.collection('tb_os').document(str(id)).get()
    o = doc.to_dict() if doc.exists else {}
    c_nome = 'Cliente Indefinido'
    if o.get('id_cliente'):
        c_doc = db.collection('tb_clientes').document(str(o.get('id_cliente'))).get()
        if c_doc.exists: c_nome = c_doc.to_dict().get('nome_empresa', 'Cliente Indefinido')
    dados_os = (id, o.get('numero_os'), c_nome, o.get('descricao_demanda'), o.get('solucao_comentario'), o.get('status_os'), o.get('analista'))
    return render_template('atender_os.html', os=dados_os, active_tab='os')

@app.route('/atualizar_os', methods=['POST'])
def atualizar_os():
    id_os = request.form.get('id_os')
    db.collection('tb_os').document(str(id_os)).update({
        'status_os': request.form.get('status'),
        'solucao_comentario': request.form.get('solucao')
    })
    flash("OS atualizada!", "success")
    return redirect('/os')

@app.route('/os/imprimir/<string:id>')
def imprimir_os(id):
    doc = db.collection('tb_os').document(str(id)).get()
    o = doc.to_dict() if doc.exists else {}
    c_nome, c_cnpj = 'Cliente Indefinido', 'Não informado'
    if o.get('id_cliente'):
        c_doc = db.collection('tb_clientes').document(str(o.get('id_cliente'))).get()
        if c_doc.exists:
            c_nome = c_doc.to_dict().get('nome_empresa', 'Cliente Indefinido')
            c_cnpj = c_doc.to_dict().get('cnpj', 'Não informado')
    dados_os = (o.get('numero_os'), c_nome, c_cnpj, o.get('solicitante'), o.get('data_abertura'), o.get('criticidade'), o.get('analista'), o.get('status_os'), o.get('descricao_demanda'), o.get('solucao_comentario'))
    return render_template('relatorio_os.html', os=dados_os, active_tab='os')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)