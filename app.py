from flask import Flask, render_template, request, redirect, session, url_for, flash
import os
import socket

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'facss_crm_chave_secreta_super_segura')

# Força IPv4 no Render
old_getaddrinfo = socket.getaddrinfo
def getaddrinfo_ipv4(*args, **kwargs):
    responses = old_getaddrinfo(*args, **kwargs)
    return [r for r in responses if r[0] == socket.AF_INET]
socket.getaddrinfo = getaddrinfo_ipv4

# ==========================================
# AUTENTICAÇÃO E LOGIN (MODO DEMO)
# ==========================================
@app.before_request
def verificar_login():
    rotas_livres = ['login', 'static']
    if 'usuario_id' not in session and request.endpoint not in rotas_livres:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    erro = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '').strip()
        
        # Acesso Mestre de Emergência
        if email == 'flavio.alves@facss.com.br' and senha == 'Facss2026':
            session['usuario_id'] = 'master_admin'
            session['usuario_nome'] = 'Flávio Alves'
            session['usuario_cargo'] = 'Gestor de Operações'
            session['usuario_email'] = email
            return redirect('/')
        else:
            session['usuario_id'] = 'user_demo'
            session['usuario_nome'] = 'Flávio Alves'
            session['usuario_cargo'] = 'Gestor de Operações'
            session['usuario_email'] = email or 'flavio.alves@facss.com.br'
            return redirect('/')
            
    return render_template('login.html', erro=erro)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==========================================
# DASHBOARD E ROTAS OPERACIONAIS
# ==========================================
@app.route('/')
def home():
    return render_template(
        'index.html',
        total_ativos=14,
        total_atencao=3,
        total_leads=9,
        os_abertas=5,
        os_criticas=2,
        clientes_sem_contato=1,
        health_chart=[8, 3, 2, 1],
        labels_analistas=['Flávio Alves', 'Carlos Mendes', 'Ana Souza'],
        qtd_analistas=[6, 4, 2],
        active_tab='dash'
    )

@app.route('/clientes')
def clientes():
    busca = request.args.get('busca', '').lower()
    mock_clientes = [
        ('1', 'Mining Tech Solutions', '12.345.678/0001-90', 'Carlos Silva', '(31) 99887-1122', 'Ativo', 'Saudável', 'Flávio Alves'),
        ('2', 'Logística Brasil S/A', '98.765.432/0001-10', 'Roberto Mendes', '(11) 97123-4455', 'Ativo', 'Atenção', 'Flávio Alves'),
        ('3', 'Transportes Vale Verde', '45.678.912/0001-33', 'Ana Paula', '(31) 98456-7890', 'Ativo', 'Saudável', 'Flávio Alves'),
        ('4', 'AgroIndústria Sudeste', '33.111.222/0001-88', 'Fernando Costa', '(31) 99111-2233', 'Ativo', 'Risco', 'Flávio Alves')
    ]
    if busca:
        mock_clientes = [c for c in mock_clientes if busca in c[1].lower() or busca in c[2].lower() or busca in c[7].lower()]
    return render_template('clientes.html', clientes=mock_clientes, active_tab='clientes', busca=busca)

@app.route('/novo_cliente')
def novo_cliente(): return render_template('cadastro_cliente.html', active_tab='clientes')

@app.route('/salvar_cliente', methods=['POST'])
def salvar_cliente():
    flash("Cliente cadastrado!", "success")
    return redirect('/clientes')

@app.route('/editar_cliente/<string:id>')
def editar_cliente(id):
    cliente = (id, 'Mining Tech Solutions', '12.345.678/0001-90', 'Carlos Silva', '(31) 99887-1122', 'carlos@miningtech.com', 'Ativo', 'Flávio Alves', 'Saudável', 'Pleno', 'R$ 45.000,00')
    return render_template('editar_cliente.html', cliente=cliente, active_tab='clientes')

@app.route('/atualizar_cliente', methods=['POST'])
def atualizar_cliente():
    flash("Cliente atualizado!", "success")
    return redirect('/clientes')

@app.route('/cliente/<string:id>')
def ficha_cliente(id):
    cliente = (id, 'Mining Tech Solutions', '12.345.678/0001-90', 'Carlos Silva', '(31) 99887-1122', 'carlos@miningtech.com', 'Ativo', 'Flávio Alves', 'Saudável', 'Pleno', 'R$ 45.000,00', '28/08/2026')
    interacoes = [('1', '28/08/2026', 'Flávio Alves', 'Reunião', 'Apresentação de alinhamento trimestral realizada com sucesso.', 'Enviar proposta estendida')]
    modulos = [('1', 'FAC-9981', 'Tracker', 'Pro v2', 'MOD-101', 'Vivo', '(31) 99911-2233', '10/01/2026', None, 'ATIVO')]
    return render_template('ficha_cliente.html', cliente=cliente, interacoes=interacoes, modulos=modulos, active_tab='clientes')

@app.route('/salvar_interacao', methods=['POST'])
def salvar_interacao():
    id_cliente = request.form.get('id_cliente')
    return redirect(f'/cliente/{id_cliente}')

@app.route('/modulos')
def modulos():
    modulos_tratados = [
        {'id': '1', 'placa_raw': 'FAC-9981', 'placa_limpa': 'FAC-9981', 'padrao_identificador': 'FAC-9981', 'marca_modelo': 'Tracker Pro v2', 'id_equip': 'MOD-101', 'cliente': 'Mining Tech Solutions', 'situacao': 'ATIVO'},
        {'id': '2', 'placa_raw': 'FAC-9982', 'placa_limpa': 'FAC-9982', 'padrao_identificador': 'FAC-9982', 'marca_modelo': 'Tracker Pro v2', 'id_equip': 'MOD-102', 'cliente': 'Logística Brasil S/A', 'situacao': 'ATIVO'}
    ]
    return render_template('modulos.html', modulos=modulos_tratados, active_tab='modulos')

@app.route('/novo_modulo')
def novo_modulo():
    return render_template('cadastro_modulo.html', clientes=[('1', 'Mining Tech Solutions')], active_tab='modulos')

@app.route('/salvar_modulo', methods=['POST'])
def salvar_modulo(): return redirect('/modulos')

@app.route('/editar_modulo/<string:id>')
def editar_modulo(id):
    modulo = {'_id': id, 'placa': 'FAC-9981', 'marca': 'Tracker', 'modelo': 'Pro v2', 'id_modulo_equip': 'MOD-101', 'id_cliente': '1', 'chip': 'Vivo', 'num_chip': '(31) 99911-2233', 'data_instalacao': '2026-01-10', 'situacao': 'ATIVO'}
    return render_template('editar_modulo.html', modulo=modulo, clientes=[('1', 'Mining Tech Solutions')], active_tab='modulos')

@app.route('/atualizar_modulo', methods=['POST'])
def atualizar_modulo(): return redirect('/modulos')

@app.route('/pipeline')
@app.route('/pipeline_kanban')
def pipeline():
    funil = {
        'Leads Iniciais': [('1', 'Alta', 'Grupo Horizonte', 'Mineração', 'Marcos Viana', 'Indicação', 'Leads Iniciais', 'Agendar ligação')],
        'Contato Feito': [('2', 'Média', 'Auto Peças Leste', 'Varejo', 'Juliana Lima', 'Inbound', 'Contato Feito', 'Enviar apresentação')],
        'Diagnóstico / Reunião': [('3', 'Alta', 'Siderúrgica Vale', 'Indústria', 'André Costa', 'Outbound', 'Diagnóstico / Reunião', 'Elaborar proposta')],
        'Proposta Enviada': [('4', 'Alta', 'Distribuidora Central', 'Logística', 'Renata Souza', 'Feira B2B', 'Proposta Enviada', 'Aguardando aprovação')],
        'Negociação': [('5', 'Média', 'Frota Express', 'Transporte', 'Lucas Ferreira', 'Indicação', 'Negociação', 'Assinatura de contrato')]
    }
    return render_template('pipeline_kanban.html', funil=funil, active_tab='kanban')

@app.route('/novo_lead')
def novo_lead(): return render_template('cadastro_lead.html', active_tab='kanban')

@app.route('/salvar_lead', methods=['POST'])
def salvar_lead(): return redirect('/pipeline')

@app.route('/mover_lead/<string:id>/<direcao>')
def mover_lead(id, direcao): return redirect('/pipeline')

@app.route('/os')
def ordens_servico():
    lista = [
        ('101', '2026101', 'Mining Tech Solutions', 'Carlos Silva', 'ALTA', 'Flávio Alves', 'EM ANDAMENTO', 'Instalação de módulo de telemetria avançada'),
        ('102', '2026102', 'Logística Brasil S/A', 'Roberto Mendes', 'MÉDIA', 'Carlos Mendes', 'ABERTO', 'Troca de SIM Card e validação de sinal')
    ]
    return render_template('os.html', ordens=lista, active_tab='os')

@app.route('/nova_os')
def nova_os():
    return render_template('cadastro_os.html', active_tab='os', clientes=[('1', 'Mining Tech Solutions')], analistas=[('Flávio Alves', 'flavio.alves@facss.com.br')], num_os='2026103')

@app.route('/salvar_os', methods=['POST'])
def salvar_os():
    flash("OS salva com sucesso!", "success")
    return redirect('/os')

@app.route('/atender_os/<string:id>')
def atender_os(id):
    dados_os = (id, '2026101', 'Mining Tech Solutions', 'Instalação de módulo de telemetria', 'Em andamento técnico', 'EM ANDAMENTO', 'Flávio Alves')
    return render_template('atender_os.html', os=dados_os, active_tab='os')

@app.route('/atualizar_os', methods=['POST'])
def atualizar_os():
    flash("OS atualizada!", "success")
    return redirect('/os')

@app.route('/os/imprimir/<string:id>')
def imprimir_os(id):
    dados_os = ('2026101', 'Mining Tech Solutions', '12.345.678/0001-90', 'Carlos Silva', '28/08/2026', 'ALTA', 'Flávio Alves', 'EM ANDAMENTO', 'Instalação de módulo de telemetria avançada', 'Equipamento instalado e validado via testes.')
    return render_template('relatorio_os.html', os=dados_os, active_tab='os')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)