# app.py - VERSÃO CORRIGIDA SEM APSCHEDULER

import os
import secrets
from datetime import datetime, date, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import func, or_

# ======================================================
# CONFIGURAÇÃO
# ======================================================

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# Configuração do banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///volei_draft.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Configurações de upload
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Inicialização das extensões
db = SQLAlchemy(app)
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins='*')

# Configuração do Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Constantes do sistema (serão configuráveis por semana)
TEMPO_ESCOLHA = 30  # segundos

# Variável global para controlar a última verificação de mensalidades
ultima_verificacao_mensalidades = datetime.min

# ======================================================
# MODELOS (atualizados com campos de mensalidade)
# ======================================================

class ConfiguracaoSemana(db.Model):
    """Configurações específicas para cada semana"""
    id = db.Column(db.Integer, primary_key=True)
    semana_id = db.Column(db.Integer, db.ForeignKey('semana.id'), nullable=False, unique=True)
    max_times = db.Column(db.Integer, default=2)
    max_jogadores_por_time = db.Column(db.Integer, default=6)
    tempo_por_escolha = db.Column(db.Integer, default=30)
    modo_draft = db.Column(db.String(20), default='snake')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamento
    semana = db.relationship('Semana', backref='configuracao', uselist=False)

class Recado(db.Model):
    """Mural de recados"""
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    autor = db.Column(db.String(100), default='Admin')
    importante = db.Column(db.Boolean, default=False)
    data_publicacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_expiracao = db.Column(db.Date)
    ativo = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<Recado {self.titulo}>'

class PixInfo(db.Model):
    """Informações de PIX"""
    id = db.Column(db.Integer, primary_key=True)
    chave_pix = db.Column(db.String(100), nullable=False)
    tipo_chave = db.Column(db.String(50), default='cpf')  # cpf, email, telefone, aleatoria
    nome_recebedor = db.Column(db.String(100), nullable=False)
    cidade_recebedor = db.Column(db.String(100))
    descricao = db.Column(db.String(200))
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<PixInfo {self.chave_pix}>'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    role = db.Column(db.String(20), nullable=False, default='jogador')
    jogador_id = db.Column(db.Integer, db.ForeignKey('jogador.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    foto_perfil = db.Column(db.String(200))
    
    # Relacionamento
    jogador = db.relationship('Jogador', back_populates='user', uselist=False)

class Jogador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    apelido = db.Column(db.String(50))
    posicao = db.Column(db.String(50))
    nivel = db.Column(db.String(20), default='intermediario')
    telefone = db.Column(db.String(20))
    mensalista = db.Column(db.Boolean, default=False)
    mensalidade_paga = db.Column(db.Boolean, default=False)  # NOVO CAMPO
    data_inicio_mensalidade = db.Column(db.Date)  # NOVO CAMPO
    data_fim_mensalidade = db.Column(db.Date)  # NOVO CAMPO
    capitao = db.Column(db.Boolean, default=False)
    ordem_capitao = db.Column(db.Integer, default=0)
    ativo = db.Column(db.Boolean, default=True)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    rating = db.Column(db.Integer, default=1000)
    foto_perfil = db.Column(db.String(200))
    altura = db.Column(db.String(10))
    data_nascimento = db.Column(db.Date)
    cidade = db.Column(db.String(100))
    
    # Relacionamento
    user = db.relationship('User', back_populates='jogador', uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Jogador {self.nome}>'

class Semana(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, unique=True)
    descricao = db.Column(db.String(200))
    lista_aberta = db.Column(db.Boolean, default=True)
    lista_encerrada = db.Column(db.Boolean, default=False)
    draft_em_andamento = db.Column(db.Boolean, default=False)
    draft_finalizado = db.Column(db.Boolean, default=False)
    max_times = db.Column(db.Integer, default=2)
    max_jogadores_por_time = db.Column(db.Integer, default=6)
    tempo_escolha = db.Column(db.Integer, default=30)
    modo_draft = db.Column(db.String(20), default='snake')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    encerrada_em = db.Column(db.DateTime)
    
    # Relacionamentos
    times = db.relationship('Time', backref='semana', lazy='dynamic')
    confirmacoes = db.relationship('Confirmacao', backref='semana', lazy='dynamic')
    lista_espera = db.relationship('ListaEspera', backref='semana', lazy='dynamic')
    
    def __repr__(self):
        return f'<Semana {self.data}>'

class Confirmacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jogador_id = db.Column(db.Integer, db.ForeignKey('jogador.id'), nullable=False)
    semana_id = db.Column(db.Integer, db.ForeignKey('semana.id'), nullable=False)
    confirmado = db.Column(db.Boolean, default=False)
    confirmado_em = db.Column(db.DateTime)
    presente = db.Column(db.Boolean, default=False)
    prioridade = db.Column(db.Integer, default=0)
    
    # Relacionamento
    jogador = db.relationship('Jogador', backref='confirmacoes')
    
    def __repr__(self):
        return f'<Confirmacao {self.jogador_id} - Semana {self.semana_id}>'

class ListaEspera(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    semana_id = db.Column(db.Integer, db.ForeignKey('semana.id'), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20))
    posicao_preferida = db.Column(db.String(50))
    adicionado_em = db.Column(db.DateTime, default=datetime.utcnow)
    promovido = db.Column(db.Boolean, default=False)
    promovido_em = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<ListaEspera {self.nome}>'

class Time(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    semana_id = db.Column(db.Integer, db.ForeignKey('semana.id'), nullable=False)
    nome = db.Column(db.String(50))
    capitao_id = db.Column(db.Integer, db.ForeignKey('jogador.id'))
    ordem_escolha = db.Column(db.Integer)
    cor = db.Column(db.String(20), default='#3498db')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    capitao = db.relationship('Jogador', backref='times_como_capitao')
    escolhas = db.relationship('EscolhaDraft', backref='time', lazy='dynamic')
    
    def __repr__(self):
        return f'<Time {self.nome}>'

class EscolhaDraft(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    semana_id = db.Column(db.Integer, db.ForeignKey('semana.id'), nullable=False)
    jogador_id = db.Column(db.Integer, db.ForeignKey('jogador.id'), nullable=False)
    time_id = db.Column(db.Integer, db.ForeignKey('time.id'), nullable=False)
    ordem_escolha = db.Column(db.Integer)
    round_num = db.Column(db.Integer, default=1)
    escolhido_em = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    jogador = db.relationship('Jogador', backref='escolhas_draft')
    
    def __repr__(self):
        return f'<EscolhaDraft {self.jogador_id} -> Time {self.time_id}>'

class DraftStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    semana_id = db.Column(db.Integer, db.ForeignKey('semana.id'), nullable=False, unique=True)
    vez_capitao_id = db.Column(db.Integer, db.ForeignKey('jogador.id'))
    rodada_atual = db.Column(db.Integer, default=1)
    escolha_atual = db.Column(db.Integer, default=1)
    tempo_restante = db.Column(db.Integer, default=TEMPO_ESCOLHA)
    finalizado = db.Column(db.Boolean, default=False)
    modo_snake = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    semana = db.relationship('Semana', backref='draft_status', uselist=False)
    vez_capitao = db.relationship('Jogador', backref='vez_capitao_status')
    
    def __repr__(self):
        return f'<DraftStatus Semana {self.semana_id}>'

class HistoricoDraft(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    semana_id = db.Column(db.Integer, db.ForeignKey('semana.id'), nullable=False)
    jogador_id = db.Column(db.Integer, db.ForeignKey('jogador.id'), nullable=False)
    time_id = db.Column(db.Integer, db.ForeignKey('time.id'), nullable=False)
    acao = db.Column(db.String(50))
    detalhes = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    jogador = db.relationship('Jogador')
    time = db.relationship('Time')
    
    def __repr__(self):
        return f'<HistoricoDraft {self.acao}>'

# ======================================================
# FUNÇÕES AUXILIARES
# ======================================================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Acesso restrito a administradores!', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def capitao_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Faça login para acessar!', 'danger')
            return redirect(url_for('login'))
        
        # Verifica se é capitão ou admin
        if current_user.role not in ['capitao', 'admin']:
            flash('Acesso restrito a capitães!', 'danger')
            return redirect(url_for('index'))
        
        # Verifica se tem jogador vinculado e é capitão
        if not current_user.jogador or not current_user.jogador.capitao:
            flash('Você não está configurado como capitão!', 'danger')
            return redirect(url_for('index'))
            
        return f(*args, **kwargs)
    return decorated_function

def jogador_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Faça login para acessar!', 'danger')
            return redirect(url_for('login'))
        
        if current_user.role not in ['jogador', 'capitao', 'admin']:
            flash('Acesso restrito!', 'danger')
            return redirect(url_for('index'))
            
        return f(*args, **kwargs)
    return decorated_function

def get_semana_atual():
    hoje = date.today()
    semana = Semana.query.filter_by(data=hoje).first()
    
    if not semana:
        try:
            semana = Semana(
                data=hoje,
                descricao=f'Jogo de Vôlei - {hoje.strftime("%d/%m/%Y")}',
                lista_aberta=True
            )
            db.session.add(semana)
            db.session.commit()
        except:
            db.session.rollback()
            semana = Semana.query.filter_by(data=hoje).first()
    
    return semana

def atualizar_lista_espera_automaticamente(semana):
    mensalistas = Jogador.query.filter_by(mensalista=True, ativo=True).all()
    
    for mensalista in mensalistas:
        confirmacao = Confirmacao.query.filter_by(
            jogador_id=mensalista.id,
            semana_id=semana.id
        ).first()
        
        if not confirmacao or not confirmacao.confirmado:
            espera_existente = ListaEspera.query.filter_by(
                semana_id=semana.id,
                nome=mensalista.nome,
                promovido=False
            ).first()
            
            if not espera_existente:
                nova_espera = ListaEspera(
                    semana_id=semana.id,
                    nome=mensalista.nome,
                    telefone=mensalista.telefone,
                    posicao_preferida=mensalista.posicao,
                    adicionado_em=datetime.utcnow()
                )
                db.session.add(nova_espera)
    
    db.session.commit()

def verificar_mensalidades_vencidas():
    """Verifica e atualiza status de mensalistas vencidos"""
    hoje = date.today()
    mensalistas = Jogador.query.filter_by(mensalista=True, ativo=True).all()
    
    jogadores_atualizados = []
    
    for jogador in mensalistas:
        if jogador.data_fim_mensalidade and jogador.data_fim_mensalidade < hoje:
            # Se a mensalidade está vencida e não foi paga, remove de mensalista
            if not jogador.mensalidade_paga:
                jogador.mensalista = False
                jogador.mensalidade_paga = False
                jogadores_atualizados.append(jogador.nome)
    
    if jogadores_atualizados:
        db.session.commit()
        print(f"⚠️ {len(jogadores_atualizados)} jogadores removidos de mensalista: {', '.join(jogadores_atualizados)}")
    elif mensalistas:
        print(f"✅ Todas as {len(mensalistas)} mensalidades estão em dia")
    
    return jogadores_atualizados

@app.before_request
def verificar_mensalidades_periodicamente():
    """Verifica mensalidades vencidas a cada hora"""
    global ultima_verificacao_mensalidades
    
    agora = datetime.utcnow()
    # Verifica a cada hora (3600 segundos)
    if (agora - ultima_verificacao_mensalidades).total_seconds() > 3600:
        ultima_verificacao_mensalidades = agora
        verificar_mensalidades_vencidas()

def inicializar_draft(semana, tempo_por_escolha=None, modo_draft=None, max_times=None, max_jogadores_por_time=None):
    """Inicializa o draft com os times e status"""
    # Remove dados anteriores do draft
    Time.query.filter_by(semana_id=semana.id).delete()
    EscolhaDraft.query.filter_by(semana_id=semana.id).delete()
    DraftStatus.query.filter_by(semana_id=semana.id).delete()
    HistoricoDraft.query.filter_by(semana_id=semana.id).delete()
    
    # Usa configurações da semana ou os parâmetros fornecidos
    if max_times:
        semana.max_times = max_times
    if max_jogadores_por_time:
        semana.max_jogadores_por_time = max_jogadores_por_time
    if tempo_por_escolha is not None:  # Aceita 0
        semana.tempo_escolha = tempo_por_escolha
    if modo_draft:
        semana.modo_draft = modo_draft
    
    # Busca capitães confirmados
    confirmacoes_capitaes = db.session.query(Confirmacao).join(Jogador).filter(
        Confirmacao.semana_id == semana.id,
        Confirmacao.confirmado == True,
        Jogador.capitao == True
    ).order_by(Jogador.ordem_capitao).all()
    
    capitaes = [c.jogador for c in confirmacoes_capitaes[:semana.max_times]]
    
    if len(capitaes) < 2:
        raise ValueError(f'É necessário pelo menos 2 capitães confirmados (encontrados: {len(capitaes)})')
    
    # Verifica número total de jogadores necessários
    total_jogadores_necessarios = semana.max_times * semana.max_jogadores_por_time
    total_confirmados = Confirmacao.query.filter_by(
        semana_id=semana.id,
        confirmado=True
    ).count()
    
    if total_confirmados < total_jogadores_necessarios:
        raise ValueError(f'É necessário pelo menos {total_jogadores_necessarios} jogadores confirmados! Confirmados: {total_confirmados}')
    
    # Cria times
    cores = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c']
    times = []
    
    for i, capitao in enumerate(capitaes):
        time = Time(
            semana_id=semana.id,
            nome=f'Time {i+1}',
            capitao_id=capitao.id,
            ordem_escolha=i+1,
            cor=cores[i % len(cores)]
        )
        db.session.add(time)
        times.append(time)
    
    db.session.commit()
    
    # Adiciona capitães automaticamente aos times
    for i, time in enumerate(times):
        capitao = Jogador.query.get(time.capitao_id)
        
        # Adiciona o capitão ao time como primeira escolha
        escolha_capitao = EscolhaDraft(
            semana_id=semana.id,
            jogador_id=capitao.id,
            time_id=time.id,
            ordem_escolha=i + 1,
            round_num=0,
            escolhido_em=datetime.utcnow()
        )
        db.session.add(escolha_capitao)
        
        # Registra no histórico
        historico = HistoricoDraft(
            semana_id=semana.id,
            jogador_id=capitao.id,
            time_id=time.id,
            acao='capitao_auto',
            detalhes=f'Capitão adicionado automaticamente ao time'
        )
        db.session.add(historico)
    
    # Inicializa status do draft
    # Se tempo_por_escolha for 0, não inicia contador
    tempo_inicial = semana.tempo_escolha if semana.tempo_escolha > 0 else None
    
    draft_status = DraftStatus(
        semana_id=semana.id,
        vez_capitao_id=capitaes[0].id,
        rodada_atual=1,
        escolha_atual=len(times) + 1,
        tempo_restante=tempo_inicial,  # Pode ser None se tempo for 0
        finalizado=False,
        modo_snake=(semana.modo_draft == 'snake')
    )
    db.session.add(draft_status)
    
    # Atualiza status da semana
    semana.draft_em_andamento = True
    semana.lista_aberta = False
    semana.lista_encerrada = True
    
    db.session.commit()
    
    return times, draft_status

def get_jogadores_disponiveis_draft(semana):
    """Retorna jogadores disponíveis para draft (excluindo capitães já em times)"""
    # Jogadores confirmados
    confirmados = Confirmacao.query.filter_by(
        semana_id=semana.id,
        confirmado=True
    ).all()
    
    jogadores_confirmados_ids = [c.jogador_id for c in confirmados]
    
    # Jogadores já escolhidos
    escolhidos = EscolhaDraft.query.filter_by(semana_id=semana.id).all()
    jogadores_escolhidos_ids = [e.jogador_id for e in escolhidos]
    
    # Jogadores disponíveis
    disponiveis = Jogador.query.filter(
        Jogador.id.in_(jogadores_confirmados_ids),
        ~Jogador.id.in_(jogadores_escolhidos_ids),
        Jogador.ativo == True
    ).order_by(Jogador.nome).all()
    
    return disponiveis

def criar_username_jogador(jogador):
    """Cria username único para jogador"""
    base_username = jogador.nome.lower().replace(' ', '_').replace("'", "").replace('"', '')
    username = base_username
    
    counter = 1
    while User.query.filter_by(username=username).first():
        username = f"{base_username}{counter}"
        counter += 1
    
    return username

def criar_usuario_para_jogador(jogador, role='jogador'):
    """Cria usuário para jogador se não existir"""
    if not jogador.user:
        username = criar_username_jogador(jogador)
        password = secrets.token_hex(6)  # Senha mais segura
        
        user = User(
            username=username,
            password=generate_password_hash(password),
            role=role,
            jogador_id=jogador.id
        )
        db.session.add(user)
        db.session.commit()
        
        return username, password
    return jogador.user.username, None

def verificar_permissoes_capitao(jogador_id):
    """Verifica se um jogador tem permissões de capitão"""
    jogador = Jogador.query.get(jogador_id)
    if not jogador:
        return False
    
    # Verifica se é capitão
    if not jogador.capitao:
        return False
    
    # Verifica se está ativo
    if not jogador.ativo:
        return False
    
    # Verifica se tem usuário associado
    if not jogador.user:
        return False
    
    # Verifica se usuário tem role correto
    if jogador.user.role not in ['capitao', 'admin']:
        return False
    
    return True

# ======================================================
# NOVAS ROTAS PARA MENSALIDADES
# ======================================================

@app.route('/admin/jogador/<int:id>/gerenciar_mensalidade', methods=['GET', 'POST'])
@admin_required
def gerenciar_mensalidade(id):
    jogador = Jogador.query.get_or_404(id)
    
    if request.method == 'POST':
        mensalista = 'mensalista' in request.form
        mensalidade_paga = 'mensalidade_paga' in request.form
        
        # Atualizar status
        jogador.mensalista = mensalista
        jogador.mensalidade_paga = mensalidade_paga
        
        # Datas da mensalidade
        data_inicio_str = request.form.get('data_inicio_mensalidade')
        data_fim_str = request.form.get('data_fim_mensalidade')
        
        if data_inicio_str:
            try:
                jogador.data_inicio_mensalidade = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            except ValueError:
                jogador.data_inicio_mensalidade = None
        
        if data_fim_str:
            try:
                jogador.data_fim_mensalidade = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
            except ValueError:
                jogador.data_fim_mensalidade = None
        
        # Se marcou como mensalidade paga, seta como mensalista
        if mensalidade_paga:
            jogador.mensalista = True
            # Se não tem data de início, seta como hoje
            if not jogador.data_inicio_mensalidade:
                jogador.data_inicio_mensalidade = date.today()
            # Se não tem data de fim, seta para 30 dias
            if not jogador.data_fim_mensalidade:
                jogador.data_fim_mensalidade = date.today() + timedelta(days=30)
        
        db.session.commit()
        
        flash('Mensalidade atualizada com sucesso!', 'success')
        return redirect(url_for('admin_jogadores'))
    
    return render_template('admin/gerenciar_mensalidade.html', jogador=jogador)

@app.route('/admin/jogador/<int:id>/renovar_mensalidade')
@admin_required
def renovar_mensalidade(id):
    jogador = Jogador.query.get_or_404(id)
    
    # Renova mensalidade por 30 dias
    jogador.mensalista = True
    jogador.mensalidade_paga = True
    jogador.data_inicio_mensalidade = date.today()
    jogador.data_fim_mensalidade = date.today() + timedelta(days=30)
    
    db.session.commit()
    
    flash(f'Mensalidade de {jogador.nome} renovada por 30 dias!', 'success')
    return redirect(url_for('admin_jogadores'))

@app.route('/admin/jogador/<int:id>/remover_mensalista')
@admin_required
def remover_mensalista(id):
    """Remove jogador da lista de mensalistas sem excluir o cadastro"""
    jogador = Jogador.query.get_or_404(id)
    
    jogador.mensalista = False
    jogador.mensalidade_paga = False
    jogador.data_fim_mensalidade = None
    
    db.session.commit()
    
    flash(f'{jogador.nome} removido da lista de mensalistas!', 'success')
    return redirect(url_for('admin_jogadores'))

@app.route('/admin/jogador/reativar/<int:id>')
@admin_required
def reativar_jogador(id):
    jogador = Jogador.query.get_or_404(id)
    jogador.ativo = True
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Jogador {jogador.nome} reativado com sucesso!'
    })

# ======================================================
# ROTA PARA VER PERFIL DE JOGADOR (PÚBLICA)
# ======================================================

@app.route('/jogador/<int:id>')
def ver_jogador(id):
    jogador = Jogador.query.get_or_404(id)
    
    if not jogador.ativo:
        flash('Jogador não está ativo no sistema.', 'warning')
        return redirect(url_for('index'))
    
    # Histórico de presenças
    historico = []
    confirmacoes = Confirmacao.query.filter_by(jogador_id=jogador.id).order_by(
        Confirmacao.semana.has(Semana.data).desc()
    ).limit(10).all()
    
    for conf in confirmacoes:
        historico.append({
            'data': conf.semana.data,
            'confirmado': conf.confirmado,
            'presente': conf.presente
        })
    
    return render_template('ver_jogador.html', jogador=jogador, historico=historico)

# ======================================================
# NOVAS ROTAS ADMIN (mantidas do código original)
# ======================================================

@app.route('/admin/recados')
@admin_required
def admin_recados():
    """Gerenciar recados/mural"""
    recados = Recado.query.order_by(Recado.data_publicacao.desc()).all()
    return render_template('admin/recados.html', recados=recados)

@app.route('/admin/recado/novo', methods=['GET', 'POST'])
@admin_required
def novo_recado():
    """Criar novo recado"""
    if request.method == 'POST':
        titulo = request.form['titulo']
        conteudo = request.form['conteudo']
        autor = request.form.get('autor', 'Admin')
        importante = 'importante' in request.form
        
        data_expiracao_str = request.form.get('data_expiracao', '')
        data_expiracao = None
        if data_expiracao_str:
            try:
                data_expiracao = datetime.strptime(data_expiracao_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        recado = Recado(
            titulo=titulo,
            conteudo=conteudo,
            autor=autor,
            importante=importante,
            data_expiracao=data_expiracao
        )
        db.session.add(recado)
        db.session.commit()
        
        flash('Recado publicado com sucesso!', 'success')
        return redirect(url_for('admin_recados'))
    
    return render_template('admin/novo_recado.html')

@app.route('/admin/recado/<int:id>/editar', methods=['GET', 'POST'])
@admin_required
def editar_recado(id):
    """Editar recado existente"""
    recado = Recado.query.get_or_404(id)
    
    if request.method == 'POST':
        recado.titulo = request.form['titulo']
        recado.conteudo = request.form['conteudo']
        recado.autor = request.form.get('autor', 'Admin')
        recado.importante = 'importante' in request.form
        recado.ativo = 'ativo' in request.form
        
        data_expiracao_str = request.form.get('data_expiracao', '')
        if data_expiracao_str:
            try:
                recado.data_expiracao = datetime.strptime(data_expiracao_str, '%Y-%m-%d').date()
            except ValueError:
                recado.data_expiracao = None
        else:
            recado.data_expiracao = None
        
        db.session.commit()
        flash('Recado atualizado com sucesso!', 'success')
        return redirect(url_for('admin_recados'))
    
    return render_template('admin/editar_recado.html', recado=recado)

@app.route('/admin/recado/<int:id>/excluir')
@admin_required
def excluir_recado(id):
    """Excluir recado"""
    recado = Recado.query.get_or_404(id)
    db.session.delete(recado)
    db.session.commit()
    flash('Recado excluído com sucesso!', 'success')
    return redirect(url_for('admin_recados'))

@app.route('/admin/pix')
@admin_required
def admin_pix():
    """Gerenciar informações de PIX"""
    pix_infos = PixInfo.query.order_by(PixInfo.created_at.desc()).all()
    return render_template('admin/pix.html', pix_infos=pix_infos)

@app.route('/admin/pix/novo', methods=['GET', 'POST'])
@admin_required
def novo_pix():
    """Adicionar nova chave PIX"""
    if request.method == 'POST':
        chave_pix = request.form['chave_pix']
        tipo_chave = request.form['tipo_chave']
        nome_recebedor = request.form['nome_recebedor']
        cidade_recebedor = request.form.get('cidade_recebedor', '')
        descricao = request.form.get('descricao', '')
        
        pix = PixInfo(
            chave_pix=chave_pix,
            tipo_chave=tipo_chave,
            nome_recebedor=nome_recebedor,
            cidade_recebedor=cidade_recebedor,
            descricao=descricao
        )
        db.session.add(pix)
        db.session.commit()
        
        flash('Chave PIX adicionada com sucesso!', 'success')
        return redirect(url_for('admin_pix'))
    
    return render_template('admin/novo_pix.html')

@app.route('/admin/pix/<int:id>/editar', methods=['GET', 'POST'])
@admin_required
def editar_pix(id):
    """Editar chave PIX"""
    pix = PixInfo.query.get_or_404(id)
    
    if request.method == 'POST':
        pix.chave_pix = request.form['chave_pix']
        pix.tipo_chave = request.form['tipo_chave']
        pix.nome_recebedor = request.form['nome_recebedor']
        pix.cidade_recebedor = request.form.get('cidade_recebedor', '')
        pix.descricao = request.form.get('descricao', '')
        pix.ativo = 'ativo' in request.form
        
        db.session.commit()
        flash('Chave PIX atualizada com sucesso!', 'success')
        return redirect(url_for('admin_pix'))
    
    return render_template('admin/editar_pix.html', pix=pix)

@app.route('/admin/pix/<int:id>/excluir')
@admin_required
def excluir_pix(id):
    """Excluir chave PIX"""
    pix = PixInfo.query.get_or_404(id)
    db.session.delete(pix)
    db.session.commit()
    flash('Chave PIX excluída com sucesso!', 'success')
    return redirect(url_for('admin_pix'))

@app.route('/admin/jogador/<int:id>/mudar_senha', methods=['GET', 'POST'])
@admin_required
def mudar_senha_jogador(id):
    """Alterar senha manualmente de um jogador"""
    jogador = Jogador.query.get_or_404(id)
    
    if not jogador.user:
        flash('Jogador não possui usuário!', 'danger')
        return redirect(url_for('admin_jogadores'))
    
    if request.method == 'POST':
        nova_senha = request.form['nova_senha']
        confirmar_senha = request.form['confirmar_senha']
        
        if nova_senha != confirmar_senha:
            flash('As senhas não coincidem!', 'danger')
            return redirect(url_for('mudar_senha_jogador', id=id))
        
        if len(nova_senha) < 6:
            flash('A senha deve ter pelo menos 6 caracteres!', 'danger')
            return redirect(url_for('mudar_senha_jogador', id=id))
        
        jogador.user.password = generate_password_hash(nova_senha)
        db.session.commit()
        
        flash(f'Senha alterada com sucesso para {jogador.nome}!', 'success')
        return redirect(url_for('admin_jogadores'))
    
    return render_template('admin/mudar_senha.html', jogador=jogador)

@app.route('/admin/configurar_semana/<int:id>', methods=['GET', 'POST'])
@admin_required
def configurar_semana(id):
    """Configurar parâmetros específicos da semana"""
    semana = Semana.query.get_or_404(id)
    
    # Busca confirmações da semana
    confirmados = Confirmacao.query.filter_by(
        semana_id=semana.id,
        confirmado=True
    ).count()
    
    if request.method == 'POST':
        semana.max_times = request.form.get('max_times', type=int, default=2)
        semana.max_jogadores_por_time = request.form.get('max_jogadores_por_time', type=int, default=6)
        semana.tempo_escolha = request.form.get('tempo_escolha', type=int, default=30)
        semana.modo_draft = request.form.get('modo_draft', 'snake')
        
        db.session.commit()
        flash('Configurações da semana atualizadas com sucesso!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/configurar_semana.html', semana=semana, confirmados=confirmados)

# ======================================================
# ROTAS PÚBLICAS
# ======================================================

@app.route('/')
def index():
    semana = get_semana_atual()
    
    # Busca recados ativos
    recados = Recado.query.filter_by(ativo=True).filter(
        or_(
            Recado.data_expiracao.is_(None),
            Recado.data_expiracao >= date.today()
        )
    ).order_by(Recado.importante.desc(), Recado.data_publicacao.desc()).all()
    
    # Busca informações PIX ativas
    pix_infos = PixInfo.query.filter_by(ativo=True).all()
    
    # Busca jogadores ativos
    jogadores = Jogador.query.filter_by(ativo=True).order_by(Jogador.nome).all()
    
    # Busca confirmações para esta semana
    confirmacoes_dict = {}
    confirmacoes = Confirmacao.query.filter_by(semana_id=semana.id).all()
    for conf in confirmacoes:
        confirmacoes_dict[conf.jogador_id] = {
            'confirmado': conf.confirmado,
            'prioridade': conf.prioridade,
            'presente': conf.presente
        }
    
    # Estatísticas
    total_confirmados = Confirmacao.query.filter_by(
        semana_id=semana.id,
        confirmado=True
    ).count()
    
    mensalistas_confirmados = db.session.query(func.count(Confirmacao.id)).join(Jogador).filter(
        Confirmacao.semana_id == semana.id,
        Confirmacao.confirmado == True,
        Jogador.mensalista == True
    ).scalar() or 0
    
    # Lista de espera
    lista_espera = ListaEspera.query.filter_by(
        semana_id=semana.id,
        promovido=False
    ).order_by(ListaEspera.adicionado_em).all()
    
    # Times do draft (se houver)
    times = []
    if semana.draft_em_andamento or semana.draft_finalizado:
        times = Time.query.filter_by(semana_id=semana.id).order_by(Time.ordem_escolha).all()
    
    return render_template('index.html',
                         semana=semana,
                         jogadores=jogadores,
                         confirmacoes=confirmacoes_dict,
                         lista_espera=lista_espera,
                         times=times,
                         recados=recados,
                         pix_infos=pix_infos,
                         total_confirmados=total_confirmados,
                         mensalistas_confirmados=mensalistas_confirmados)

@app.route('/copiar_pix/<int:id>')
def copiar_pix(id):
    """API para copiar chave PIX"""
    pix = PixInfo.query.get_or_404(id)
    return jsonify({'success': True, 'chave': pix.chave_pix})

# ======================================================
# ROTA DE REGISTRO APRIMORADA
# ======================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        email = request.form.get('email', '').strip()
        nome_completo = request.form.get('nome_completo', '').strip()
        telefone = request.form.get('telefone', '').strip()
        posicao = request.form.get('posicao', '')
        nivel = request.form.get('nivel', 'intermediario')
        
        # Validações básicas
        if password != confirm_password:
            flash('As senhas não coincidem!', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Nome de usuário já está em uso!', 'danger')
            return redirect(url_for('register'))
        
        if email and User.query.filter_by(email=email).first():
            flash('E-mail já está em uso!', 'danger')
            return redirect(url_for('register'))
        
        # VERSÃO SIMPLIFICADA: Cria novo jogador sem verificação complexa
        jogador_id = None
        if nome_completo:
            # Verifica apenas se não há jogador IDÊNTICO (mesmo nome exato)
            jogador_existente = Jogador.query.filter(
                func.lower(func.trim(Jogador.nome)) == nome_completo.strip().lower(),
                Jogador.ativo == True
            ).first()
            
            if jogador_existente:
                if jogador_existente.user:
                    flash('Já existe um jogador com este nome e já possui conta. Escolha outro nome ou contate o administrador.', 'danger')
                    return redirect(url_for('register'))
                else:
                    # Usa o jogador existente sem conta
                    jogador_id = jogador_existente.id
                    
                    # Atualiza dados se fornecidos
                    atualizar = False
                    if telefone and not jogador_existente.telefone:
                        jogador_existente.telefone = telefone
                        atualizar = True
                    if posicao and not jogador_existente.posicao:
                        jogador_existente.posicao = posicao
                        atualizar = True
                    if nivel and jogador_existente.nivel == 'intermediario':
                        jogador_existente.nivel = nivel
                        atualizar = True
                    
                    if atualizar:
                        db.session.commit()
                    
                    flash(f'Conta vinculada ao jogador existente: {nome_completo}', 'info')
            else:
                # Cria novo jogador
                jogador = Jogador(
                    nome=nome_completo,
                    telefone=telefone,
                    posicao=posicao,
                    nivel=nivel,
                    ativo=True
                )
                db.session.add(jogador)
                try:
                    db.session.flush()
                    jogador_id = jogador.id
                except Exception as e:
                    db.session.rollback()
                    flash('Erro ao criar jogador. Tente novamente.', 'danger')
                    return redirect(url_for('register'))
        
        # Cria usuário
        try:
            # Define role baseado no jogador (se for capitão)
            role = 'jogador'
            if jogador_id:
                jogador = Jogador.query.get(jogador_id)
                if jogador and jogador.capitao:
                    role = 'capitao'
            
            user = User(
                username=username,
                password=generate_password_hash(password),
                email=email if email else None,
                role=role,
                jogador_id=jogador_id
            )
            db.session.add(user)
            db.session.commit()
            
            flash('Conta criada com sucesso! Faça login para continuar.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar conta: {str(e)}', 'danger')
            return redirect(url_for('register'))
    
    return render_template('register.html')

# ======================================================
# ROTAS EXISTENTES (mantidas do código original)
# ======================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            flash('Login realizado com sucesso!', 'success')
            
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'capitao':
                return redirect(url_for('capitao_dashboard'))
            else:
                return redirect(url_for('perfil'))
        else:
            flash('Usuário ou senha incorretos!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout realizado com sucesso!', 'info')
    return redirect(url_for('index'))

# ======================================================
# ROTAS PARA JOGADORES
# ======================================================

@app.route('/perfil')
@login_required
def perfil():
    jogador = None
    if current_user.jogador_id:
        jogador = Jogador.query.get(current_user.jogador_id)
    
    # Se usuário não tem jogador vinculado, sugere criar
    if not jogador and current_user.role == 'jogador':
        flash('Complete seu perfil de jogador para ter acesso a todas as funcionalidades.', 'info')
        return redirect(url_for('completar_perfil'))
    
    # Histórico de presenças
    historico = []
    if jogador:
        confirmacoes = Confirmacao.query.filter_by(jogador_id=jogador.id).order_by(
            Confirmacao.semana.has(Semana.data).desc()
        ).limit(10).all()
        
        for conf in confirmacoes:
            historico.append({
                'data': conf.semana.data,
                'confirmado': conf.confirmado,
                'presente': conf.presente
            })
    
    return render_template('perfil.html', jogador=jogador, historico=historico)

@app.route('/completar_perfil', methods=['GET', 'POST'])
@login_required
def completar_perfil():
    if request.method == 'POST':
        nome = request.form['nome']
        telefone = request.form.get('telefone', '')
        posicao = request.form.get('posicao', '')
        nivel = request.form.get('nivel', 'intermediario')
        
        # Cria jogador
        jogador = Jogador(
            nome=nome,
            telefone=telefone,
            posicao=posicao,
            nivel=nivel,
            ativo=True
        )
        
        db.session.add(jogador)
        db.session.flush()
        
        # Vincula ao usuário
        current_user.jogador_id = jogador.id
        db.session.commit()
        
        flash('Perfil de jogador criado com sucesso!', 'success')
        return redirect(url_for('perfil'))
    
    return render_template('completar_perfil.html')

@app.route('/perfil/editar', methods=['GET', 'POST'])
@login_required
def editar_perfil():
    if not current_user.jogador_id:
        flash('Você não tem um perfil de jogador.', 'danger')
        return redirect(url_for('completar_perfil'))
    
    jogador = Jogador.query.get(current_user.jogador_id)
    
    if request.method == 'POST':
        jogador.nome = request.form['nome']
        jogador.apelido = request.form.get('apelido', '')
        jogador.posicao = request.form.get('posicao', '')
        jogador.nivel = request.form.get('nivel', 'intermediario')
        jogador.telefone = request.form.get('telefone', '')
        jogador.altura = request.form.get('altura', '')
        jogador.cidade = request.form.get('cidade', '')
        
        # Data de nascimento
        data_nascimento_str = request.form.get('data_nascimento', '')
        if data_nascimento_str:
            try:
                jogador.data_nascimento = datetime.strptime(data_nascimento_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        db.session.commit()
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('perfil'))
    
    return render_template('editar_perfil.html', jogador=jogador)

@app.route('/upload_foto_jogador', methods=['POST'])
@login_required
def upload_foto_jogador():
    if not current_user.jogador_id:
        return jsonify({'success': False, 'message': 'Sem permissão!'})
    
    # Verifica se é para remover a foto
    if request.is_json:
        data = request.get_json()
        if data.get('remover'):
            jogador = Jogador.query.get(current_user.jogador_id)
            if jogador.foto_perfil:
                old_path = os.path.join(app.static_folder, jogador.foto_perfil.lstrip('/'))
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except:
                        pass
                jogador.foto_perfil = None
                db.session.commit()
                return jsonify({'success': True, 'message': 'Foto removida!'})
    
    if 'foto' not in request.files:
        return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado!'})
    
    file = request.files['foto']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado!'})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(f"jogador_{current_user.jogador_id}_{datetime.now().timestamp()}.{file.filename.rsplit('.', 1)[1].lower()}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Garante que a pasta existe
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        file.save(filepath)
        
        # Atualiza foto do jogador
        jogador = Jogador.query.get(current_user.jogador_id)
        
        # Remove foto anterior se existir
        if jogador.foto_perfil:
            old_path = os.path.join(app.static_folder, jogador.foto_perfil.lstrip('/'))
            if os.path.exists(old_path) and os.path.basename(old_path) != filename:
                try:
                    os.remove(old_path)
                except:
                    pass
        
        jogador.foto_perfil = f"/static/uploads/{filename}"
        db.session.commit()
        
        return jsonify({'success': True, 'foto_url': jogador.foto_perfil})
    
    return jsonify({'success': False, 'message': 'Tipo de arquivo não permitido!'})

@app.route('/confirmar_presenca', methods=['POST'])
def confirmar_presenca():
    """Confirmar presença sem necessidade de login"""
    semana = get_semana_atual()
    
    if not semana.lista_aberta:
        return jsonify({'success': False, 'message': 'Lista de presença está fechada!'})
    
    jogador_id = request.form.get('jogador_id', type=int)
    confirmar = request.form.get('confirmar') == 'true'
    
    # Verifica código de segurança
    codigo_seguranca = request.form.get('codigo', '')
    
    # Lista de códigos permitidos
    codigos_permitidos = ['volei123', 'confirmar', 'presenca', 'volei', 'confirmar123']
    
    if not codigo_seguranca or codigo_seguranca not in codigos_permitidos:
        return jsonify({'success': False, 'message': 'Código de segurança inválido! Use: volei123'})
    
    jogador = Jogador.query.get(jogador_id)
    if not jogador or not jogador.ativo:
        return jsonify({'success': False, 'message': 'Jogador não encontrado ou inativo!'})
    
    # Busca ou cria confirmação
    confirmacao = Confirmacao.query.filter_by(
        jogador_id=jogador_id,
        semana_id=semana.id
    ).first()
    
    if not confirmacao:
        confirmacao = Confirmacao(
            jogador_id=jogador_id,
            semana_id=semana.id,
            confirmado=confirmar,
            confirmado_em=datetime.utcnow() if confirmar else None,
            prioridade=2 if jogador.capitao else (1 if jogador.mensalista else 0)
        )
        db.session.add(confirmacao)
    else:
        confirmacao.confirmado = confirmar
        confirmacao.confirmado_em = datetime.utcnow() if confirmar else None
    
    # Se o jogador está confirmando presença, remove da lista de espera
    if confirmar:
        # Remove o jogador da lista de espera se estiver lá
        lista_espera = ListaEspera.query.filter_by(
            semana_id=semana.id,
            nome=jogador.nome,
            promovido=False
        ).first()
        
        if lista_espera:
            db.session.delete(lista_espera)
    
    # NÃO adiciona mensalista à lista de espera se marcou "Não"
    # Conforme solicitado
    
    db.session.commit()
    
    mensagem = 'Presença confirmada!' if confirmar else 'Presença removida!'
    return jsonify({'success': True, 'message': mensagem})

@app.route('/entrar_lista_espera', methods=['POST'])
def entrar_lista_espera():
    semana = get_semana_atual()
    
    if not semana.lista_aberta:
        flash('Lista de presença está fechada!', 'danger')
        return redirect(url_for('index'))
    
    nome = request.form.get('nome')
    telefone = request.form.get('telefone', '')
    posicao = request.form.get('posicao', '')
    
    if not nome:
        flash('Por favor, informe seu nome!', 'danger')
        return redirect(url_for('index'))
    
    # Verifica se já está na lista de espera
    existente = ListaEspera.query.filter_by(
        semana_id=semana.id,
        nome=nome,
        promovido=False
    ).first()
    
    if existente:
        flash('Você já está na lista de espera!', 'warning')
    else:
        lista_espera = ListaEspera(
            semana_id=semana.id,
            nome=nome,
            telefone=telefone,
            posicao_preferida=posicao,
            adicionado_em=datetime.utcnow()
        )
        db.session.add(lista_espera)
        db.session.commit()
        flash('Você foi adicionado à lista de espera!', 'success')
    
    return redirect(url_for('index'))

# ======================================================
# ROTAS DO ADMIN
# ======================================================

@app.route('/admin')
@admin_required
def admin_dashboard():
    semana = get_semana_atual()
    
    # Estatísticas
    total_jogadores = Jogador.query.filter_by(ativo=True).count()
    total_mensalistas = Jogador.query.filter_by(mensalista=True, ativo=True).count()
    total_capitaes = Jogador.query.filter_by(capitao=True, ativo=True).count()
    
    # Confirmações da semana
    confirmacoes = Confirmacao.query.filter_by(semana_id=semana.id).all()
    confirmados = [c for c in confirmacoes if c.confirmado]
    nao_confirmados = [c for c in confirmacoes if not c.confirmado]
    
    # Lista de espera
    lista_espera = ListaEspera.query.filter_by(
        semana_id=semana.id,
        promovido=False
    ).order_by(ListaEspera.adicionado_em).all()
    
    # Times (se draft em andamento ou finalizado)
    times = []
    if semana.draft_em_andamento or semana.draft_finalizado:
        times = Time.query.filter_by(semana_id=semana.id).order_by(Time.ordem_escolha).all()
    
    return render_template('admin/dashboard.html',
                         semana=semana,
                         total_jogadores=total_jogadores,
                         total_mensalistas=total_mensalistas,
                         total_capitaes=total_capitaes,
                         confirmados=len(confirmados),
                         nao_confirmados=len(nao_confirmados),
                         lista_espera=lista_espera,
                         times=times)

@app.route('/admin/jogadores')
@admin_required
def admin_jogadores():
    # Jogadores mensalistas ativos (com mensalidade válida ou paga)
    mensalistas_ativos = Jogador.query.filter_by(mensalista=True, ativo=True).order_by(Jogador.nome).all()
    
    # Jogadores não mensalistas (ativos)
    nao_mensalistas = Jogador.query.filter_by(mensalista=False, ativo=True).order_by(Jogador.nome).all()
    
    # Jogadores inativos
    inativos = Jogador.query.filter_by(ativo=False).order_by(Jogador.nome).all()
    
    return render_template('admin/jogadores.html', 
                         mensalistas_ativos=mensalistas_ativos,
                         nao_mensalistas=nao_mensalistas,
                         inativos=inativos)

@app.route('/admin/jogador/novo', methods=['GET', 'POST'])
@admin_required
def novo_jogador():
    if request.method == 'POST':
        nome = request.form['nome']
        apelido = request.form.get('apelido', '')
        posicao = request.form.get('posicao', '')
        nivel = request.form.get('nivel', 'intermediario')
        telefone = request.form.get('telefone', '')
        altura = request.form.get('altura', '')
        cidade = request.form.get('cidade', '')
        mensalista = 'mensalista' in request.form
        capitao = 'capitao' in request.form
        ordem_capitao = request.form.get('ordem_capitao', 0, type=int)
        criar_usuario = 'criar_usuario' in request.form
        
        # Verifica se já existe jogador com este nome
        if Jogador.query.filter_by(nome=nome, ativo=True).first():
            flash(f'Já existe um jogador com o nome "{nome}"!', 'danger')
            return redirect(url_for('novo_jogador'))
        
        # Data de nascimento
        data_nascimento_str = request.form.get('data_nascimento', '')
        data_nascimento = None
        if data_nascimento_str:
            try:
                data_nascimento = datetime.strptime(data_nascimento_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        jogador = Jogador(
            nome=nome,
            apelido=apelido,
            posicao=posicao,
            nivel=nivel,
            telefone=telefone,
            altura=altura,
            cidade=cidade,
            data_nascimento=data_nascimento,
            mensalista=mensalista,
            capitao=capitao,
            ordem_capitao=ordem_capitao if capitao else 0
        )
        
        db.session.add(jogador)
        db.session.commit()
        
        # Cria usuário se solicitado
        if criar_usuario:
            username, password = criar_usuario_para_jogador(jogador, 'capitao' if capitao else 'jogador')
            flash(f'Usuário criado: {username} / Senha: {password}', 'info')
        
        flash('Jogador cadastrado com sucesso!', 'success')
        return redirect(url_for('admin_jogadores'))
    
    return render_template('admin/novo_jogador.html')

@app.route('/admin/jogador/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_jogador(id):
    jogador = Jogador.query.get_or_404(id)
    
    if request.method == 'POST':
        jogador.nome = request.form['nome']
        jogador.apelido = request.form.get('apelido', '')
        jogador.posicao = request.form.get('posicao', '')
        jogador.nivel = request.form.get('nivel', 'intermediario')
        jogador.telefone = request.form.get('telefone', '')
        jogador.altura = request.form.get('altura', '')
        jogador.cidade = request.form.get('cidade', '')
        jogador.mensalista = 'mensalista' in request.form
        capitao_antigo = jogador.capitao
        jogador.capitao = 'capitao' in request.form
        
        # Data de nascimento
        data_nascimento_str = request.form.get('data_nascimento', '')
        if data_nascimento_str:
            try:
                jogador.data_nascimento = datetime.strptime(data_nascimento_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        if jogador.capitao:
            jogador.ordem_capitao = request.form.get('ordem_capitao', 0, type=int)
        else:
            jogador.ordem_capitao = 0
        
        # Cria ou atualiza usuário para capitão
        if jogador.capitao and not jogador.user:
            username, password = criar_usuario_para_jogador(jogador, 'capitao')
            flash(f'Usuário criado para capitão: {username} / Senha: {password}', 'info')
        elif not jogador.capitao and jogador.user and capitao_antigo:
            # Se era capitão e deixou de ser, mantém o usuário mas muda o role
            jogador.user.role = 'jogador'
            flash('Jogador deixou de ser capitão. Usuário mantido com role "jogador".', 'info')
        
        # Criar usuário se solicitado
        if 'criar_usuario' in request.form and not jogador.user:
            username, password = criar_usuario_para_jogador(jogador, 'jogador')
            flash(f'Usuário criado: {username} / Senha: {password}', 'info')
        
        db.session.commit()
        flash('Jogador atualizado com sucesso!', 'success')
        return redirect(url_for('admin_jogadores'))
    
    return render_template('admin/editar_jogador.html', jogador=jogador)

@app.route('/admin/jogador/<int:id>/upload_foto', methods=['POST'])
@admin_required
def upload_foto_jogador_admin(id):
    jogador = Jogador.query.get_or_404(id)
    
    if 'foto' not in request.files:
        return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado!'})
    
    file = request.files['foto']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado!'})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(f"jogador_{jogador.id}_{datetime.now().timestamp()}.{file.filename.rsplit('.', 1)[1].lower()}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Garante que a pasta existe
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        file.save(filepath)
        
        # Remove foto anterior se existir
        if jogador.foto_perfil:
            old_path = os.path.join(app.static_folder, jogador.foto_perfil.lstrip('/'))
            if os.path.exists(old_path) and os.path.basename(old_path) != filename:
                try:
                    os.remove(old_path)
                except:
                    pass
        
        jogador.foto_perfil = f"/static/uploads/{filename}"
        db.session.commit()
        
        return jsonify({'success': True, 'foto_url': jogador.foto_perfil})
    
    return jsonify({'success': False, 'message': 'Tipo de arquivo não permitido!'})

@app.route('/admin/jogador/<int:id>/reset_password')
@admin_required
def reset_password_capitao(id):
    jogador = Jogador.query.get_or_404(id)
    
    if not jogador.user:
        return jsonify({'success': False, 'message': 'Jogador não possui usuário!'})
    
    # Gera nova senha
    password = secrets.token_hex(6)
    jogador.user.password = generate_password_hash(password)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'password': password,
        'message': 'Senha redefinida com sucesso!'
    })

@app.route('/admin/jogador/excluir/<int:id>')
@admin_required
def excluir_jogador(id):
    jogador = Jogador.query.get_or_404(id)
    jogador.ativo = False
    
    # Remove foto se existir
    if jogador.foto_perfil:
        old_path = os.path.join(app.static_folder, jogador.foto_perfil.lstrip('/'))
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except:
                pass
    
    # NÃO remove usuário associado, apenas desativa o jogador
    db.session.commit()
    flash('Jogador desativado com sucesso!', 'success')
    return redirect(url_for('admin_jogadores'))

# ======================================================
# ROTAS DO DRAFT (mantidas)
# ======================================================

@app.route('/admin/iniciar_draft', methods=['POST'])
@admin_required
def iniciar_draft():
    semana = get_semana_atual()
    
    # Obtém configurações do formulário
    tempo_por_escolha = request.form.get('tempo_por_escolha', type=int, default=30)
    modo_draft = request.form.get('modo_draft', 'snake')
    max_times = request.form.get('max_times', type=int, default=2)
    max_jogadores_por_time = request.form.get('max_jogadores_por_time', type=int, default=6)
    
    # Validações
    total_confirmados = Confirmacao.query.filter_by(
        semana_id=semana.id,
        confirmado=True
    ).count()
    
    capitaes_confirmados = db.session.query(Confirmacao).join(Jogador).filter(
        Confirmacao.semana_id == semana.id,
        Confirmacao.confirmado == True,
        Jogador.capitao == True
    ).count()
    
    if capitaes_confirmados < max_times:
        flash(f'É necessário pelo menos {max_times} capitães confirmados! Confirmados: {capitaes_confirmados}', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    total_vagas = max_times * max_jogadores_por_time
    if total_confirmados < total_vagas:
        flash(f'É necessário pelo menos {total_vagas} jogadores confirmados! Confirmados: {total_confirmados}', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    # Inicializa draft com configurações
    try:
        inicializar_draft(semana, tempo_por_escolha, modo_draft, max_times, max_jogadores_por_time)
        flash(f'Draft iniciado com {max_times} times e {max_jogadores_por_time} jogadores por time!', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/fechar_lista')
@admin_required
def fechar_lista():
    semana = get_semana_atual()
    semana.lista_aberta = False
    semana.lista_encerrada = True
    
    # Atualiza lista de espera automaticamente
    atualizar_lista_espera_automaticamente(semana)
    
    db.session.commit()
    flash('Lista de presença fechada! Lista de espera atualizada.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/abrir_lista')
@admin_required
def abrir_lista():
    semana = get_semana_atual()
    semana.lista_aberta = True
    semana.lista_encerrada = False
    db.session.commit()
    flash('Lista de presença aberta!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/finalizar_draft')
@admin_required
def finalizar_draft():
    semana = get_semana_atual()
    if semana.draft_em_andamento:
        semana.draft_em_andamento = False
        semana.draft_finalizado = True
        
        # Finaliza status do draft
        draft_status = DraftStatus.query.filter_by(semana_id=semana.id).first()
        if draft_status:
            draft_status.finalizado = True
        
        db.session.commit()
        flash('Draft finalizado!', 'success')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/gerenciar_times')
@admin_required
def gerenciar_times():
    semana = get_semana_atual()
    
    if not semana.draft_finalizado:
        flash('Draft ainda não finalizado!', 'warning')
        return redirect(url_for('admin_dashboard'))
    
    times = Time.query.filter_by(semana_id=semana.id).order_by(Time.ordem_escolha).all()
    
    # Busca jogadores disponíveis (não escolhidos)
    confirmados = Confirmacao.query.filter_by(semana_id=semana.id, confirmado=True).all()
    jogadores_confirmados_ids = [c.jogador_id for c in confirmados]
    
    escolhidos = EscolhaDraft.query.filter_by(semana_id=semana.id).all()
    jogadores_escolhidos_ids = [e.jogador_id for e in escolhidos]
    
    jogadores_disponiveis = Jogador.query.filter(
        Jogador.id.in_(jogadores_confirmados_ids),
        ~Jogador.id.in_(jogadores_escolhidos_ids),
        Jogador.ativo == True
    ).order_by(Jogador.nome).all()
    
    return render_template('admin/gerenciar_times.html',
                         semana=semana,
                         times=times,
                         jogadores_disponiveis=jogadores_disponiveis)

@app.route('/admin/reiniciar_semana')
@admin_required
def reiniciar_semana():
    semana = get_semana_atual()
    
    # Log da ação
    print(f"Admin {current_user.username} reiniciando semana {semana.id}")
    
    try:
        # Remove todos os dados do draft desta semana
        EscolhaDraft.query.filter_by(semana_id=semana.id).delete()
        Time.query.filter_by(semana_id=semana.id).delete()
        DraftStatus.query.filter_by(semana_id=semana.id).delete()
        HistoricoDraft.query.filter_by(semana_id=semana.id).delete()
        
        # Reseta status da semana
        semana.draft_em_andamento = False
        semana.draft_finalizado = False
        semana.lista_encerrada = False
        semana.lista_aberta = True
        
        # Remove confirmações
        Confirmacao.query.filter_by(semana_id=semana.id).delete()
        
        # Remove lista de espera
        ListaEspera.query.filter_by(semana_id=semana.id).delete()
        
        db.session.commit()
        
        flash('✅ Semana reiniciada com sucesso! Lista aberta para novas confirmações.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erro ao reiniciar semana: {str(e)}', 'danger')
        print(f"Erro ao reiniciar semana: {e}")
    
    return redirect(url_for('admin_dashboard'))

# ======================================================
# ROTAS DO CAPITÃO
# ======================================================

@app.route('/capitao')
@capitao_required
def capitao_dashboard():
    semana = get_semana_atual()
    
    # Busca time do capitão (se houver draft)
    time = None
    draft_status = None
    minha_vez = False
    jogadores_disponiveis = []
    minhas_escolhas = []
    times = []
    
    if semana.draft_em_andamento or semana.draft_finalizado:
        # Busca time do capitão
        time = Time.query.filter_by(
            semana_id=semana.id,
            capitao_id=current_user.jogador_id
        ).first()
        
        if not time:
            flash('Você não é capitão no draft desta semana!', 'warning')
            # Permite acesso mesmo assim, mas mostra mensagem
            time = Time(semana_id=semana.id, capitao_id=current_user.jogador_id, nome=f"Time {current_user.jogador.nome}")
        else:
            # Busca status do draft
            draft_status = DraftStatus.query.filter_by(semana_id=semana.id).first()
            
            # Verifica se é a vez deste capitão
            if draft_status and draft_status.vez_capitao_id:
                minha_vez = draft_status.vez_capitao_id == current_user.jogador_id
            
            # Busca jogadores disponíveis (apenas se draft em andamento)
            if semana.draft_em_andamento:
                jogadores_disponiveis = get_jogadores_disponiveis_draft(semana)
            
            # Busca escolhas do time
            minhas_escolhas = EscolhaDraft.query.filter_by(
                semana_id=semana.id,
                time_id=time.id
            ).order_by(EscolhaDraft.ordem_escolha).all()
            
            # Busca todos os times
            times = Time.query.filter_by(semana_id=semana.id).order_by(Time.ordem_escolha).all()
    
    return render_template('capitao/dashboard.html',
                         semana=semana,
                         time=time,
                         draft_status=draft_status,
                         minha_vez=minha_vez,
                         jogadores_disponiveis=jogadores_disponiveis,
                         minhas_escolhas=minhas_escolhas,
                         times=times,
                         TEMPO_ESCOLHA=TEMPO_ESCOLHA)

@app.route('/capitao/escolher', methods=['POST'])
@capitao_required
def capitao_escolher():
    semana = get_semana_atual()
    
    if not semana.draft_em_andamento:
        return jsonify({'success': False, 'message': 'Draft não está em andamento!'})
    
    # Verifica se é a vez deste capitão
    draft_status = DraftStatus.query.filter_by(semana_id=semana.id).first()
    if not draft_status or draft_status.vez_capitao_id != current_user.jogador_id:
        return jsonify({'success': False, 'message': 'Não é a sua vez de escolher!'})
    
    # Busca time do capitão
    time = Time.query.filter_by(
        semana_id=semana.id,
        capitao_id=current_user.jogador_id
    ).first()
    
    if not time:
        return jsonify({'success': False, 'message': 'Time não encontrado!'})
    
    jogador_id = request.form.get('jogador_id', type=int)
    
    # Verifica jogador
    jogador = Jogador.query.get(jogador_id)
    if not jogador or not jogador.ativo:
        return jsonify({'success': False, 'message': 'Jogador não encontrado!'})
    
    # Verifica se jogador está confirmado
    confirmacao = Confirmacao.query.filter_by(
        semana_id=semana.id,
        jogador_id=jogador_id,
        confirmado=True
    ).first()
    
    if not confirmacao:
        return jsonify({'success': False, 'message': 'Jogador não confirmou presença!'})
    
    # Verifica se já foi escolhido
    escolha_existente = EscolhaDraft.query.filter_by(
        semana_id=semana.id,
        jogador_id=jogador_id
    ).first()
    
    if escolha_existente:
        return jsonify({'success': False, 'message': 'Jogador já foi escolhido!'})
    
    # Faz a escolha
    escolha = EscolhaDraft(
        semana_id=semana.id,
        jogador_id=jogador_id,
        time_id=time.id,
        ordem_escolha=draft_status.escolha_atual,
        round_num=draft_status.rodada_atual,
        escolhido_em=datetime.utcnow()
    )
    db.session.add(escolha)
    
    # Registra no histórico
    historico = HistoricoDraft(
        semana_id=semana.id,
        jogador_id=jogador_id,
        time_id=time.id,
        acao='escolhido',
        detalhes=f'Escolhido por {current_user.jogador.nome} na rodada {draft_status.rodada_atual}'
    )
    db.session.add(historico)
    
    # Atualiza status do draft
    draft_status.escolha_atual += 1
    # Só reinicia tempo se tempo for > 0
    if semana.tempo_escolha > 0:
        draft_status.tempo_restante = semana.tempo_escolha
    
    # Calcula próximo capitão (snake draft)
    times = Time.query.filter_by(semana_id=semana.id).order_by(Time.ordem_escolha).all()
    times_ids = [t.id for t in times]
    times_capitaes_ids = [t.capitao_id for t in times]
    
    # Lógica snake draft
    if draft_status.modo_snake:
        if draft_status.rodada_atual % 2 == 1:
            time_atual_index = times_ids.index(time.id)
            proximo_index = (time_atual_index + 1) % len(times)
        else:
            time_atual_index = times_ids.index(time.id)
            proximo_index = (time_atual_index - 1) % len(times)
    else:
        time_atual_index = times_ids.index(time.id)
        proximo_index = (time_atual_index + 1) % len(times)
    
    # Verifica se mudou de rodada
    if proximo_index == 0 and time_atual_index == len(times) - 1:
        draft_status.rodada_atual += 1
    
    draft_status.vez_capitao_id = times_capitaes_ids[proximo_index]
    
    # Verifica se draft acabou
    escolhas_por_time = {}
    for t in times:
        num_escolhas = EscolhaDraft.query.filter_by(
            semana_id=semana.id,
            time_id=t.id
        ).count()
        escolhas_por_time[t.id] = num_escolhas
    
    # Verifica se todos os times têm jogadores suficientes
    draft_completo = all(num >= semana.max_jogadores_por_time for num in escolhas_por_time.values())
    
    if draft_completo:
        draft_status.finalizado = True
        semana.draft_em_andamento = False
        semana.draft_finalizado = True
    
    db.session.commit()
    
    # Emite evento via SocketIO
    socketio.emit('draft_update', {
        'semana_id': semana.id,
        'jogador_id': jogador_id,
        'jogador_nome': jogador.nome,
        'time_id': time.id,
        'time_nome': time.nome,
        'capitao_nome': current_user.jogador.nome,
        'escolha_atual': draft_status.escolha_atual - 1,
        'rodada_atual': draft_status.rodada_atual,
        'vez_capitao_id': draft_status.vez_capitao_id,
        'finalizado': draft_status.finalizado
    }, room=f'draft_{semana.id}')
    
    return jsonify({
        'success': True,
        'message': f'{jogador.nome} escolhido para o {time.nome}!',
        'draft_finalizado': draft_status.finalizado
    })

# ======================================================
# ROTAS DO DRAFT (VISUALIZAÇÃO PÚBLICA)
# ======================================================

@app.route('/draft')
def visualizar_draft():
    semana = get_semana_atual()
    
    if not (semana.draft_em_andamento or semana.draft_finalizado):
        flash('Não há draft em andamento ou finalizado!', 'info')
        return redirect(url_for('index'))
    
    # Busca times
    times = Time.query.filter_by(semana_id=semana.id).order_by(Time.ordem_escolha).all()
    
    # Busca escolhas
    escolhas_por_time = {}
    for time in times:
        escolhas = EscolhaDraft.query.filter_by(
            semana_id=semana.id,
            time_id=time.id
        ).order_by(EscolhaDraft.ordem_escolha).all()
        escolhas_por_time[time.id] = escolhas
    
    # Busca status do draft
    draft_status = DraftStatus.query.filter_by(semana_id=semana.id).first()
    
    # Jogadores disponíveis (se draft em andamento)
    jogadores_disponiveis = []
    if semana.draft_em_andamento:
        jogadores_disponiveis = get_jogadores_disponiveis_draft(semana)
    
    # Próxima escolha
    proxima_escolha_num = draft_status.escolha_atual if draft_status else 1
    
    return render_template('draft/publico.html',
                         semana=semana,
                         times=times,
                         escolhas_por_time=escolhas_por_time,
                         draft_status=draft_status,
                         jogadores_disponiveis=jogadores_disponiveis,
                         proxima_escolha_num=proxima_escolha_num,
                         MAX_JOGADORES_POR_TIME=semana.max_jogadores_por_time)

# ======================================================
# SOCKET.IO - COMUNICAÇÃO EM TEMPO REAL
# ======================================================

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        join_room(f'user_{current_user.id}')
        emit('connected', {'user_id': current_user.id})

@socketio.on('join_draft')
def handle_join_draft(data):
    semana_id = data.get('semana_id')
    if semana_id:
        join_room(f'draft_{semana_id}')
        emit('joined_draft', {'semana_id': semana_id})

@socketio.on('leave_draft')
def handle_leave_draft(data):
    semana_id = data.get('semana_id')
    if semana_id:
        leave_room(f'draft_{semana_id}')

@socketio.on('request_draft_status')
def handle_request_draft_status(data):
    semana_id = data.get('semana_id')
    if semana_id:
        semana = Semana.query.get(semana_id)
        if semana:
            draft_status = DraftStatus.query.filter_by(semana_id=semana.id).first()
            times = Time.query.filter_by(semana_id=semana.id).order_by(Time.ordem_escolha).all()
            
            # Não decrementa tempo se for 0 ou None
            if draft_status and draft_status.tempo_restante is not None and draft_status.tempo_restante > 0:
                # Decrementa tempo apenas se > 0
                draft_status.tempo_restante -= 1
                
                # Se tempo acabou, passa para próximo capitão (opcional)
                if draft_status.tempo_restante <= 0 and not draft_status.finalizado:
                    # Aqui você poderia implementar lógica para passar automaticamente
                    pass
                
                db.session.commit()
            
            times_info = []
            for time in times:
                capitao = Jogador.query.get(time.capitao_id)
                escolhas = EscolhaDraft.query.filter_by(
                    semana_id=semana.id,
                    time_id=time.id
                ).order_by(EscolhaDraft.ordem_escolha).all()
                
                jogadores = []
                for escolha in escolhas:
                    jogador = Jogador.query.get(escolha.jogador_id)
                    jogadores.append({
                        'id': jogador.id,
                        'nome': jogador.nome,
                        'apelido': jogador.apelido,
                        'posicao': jogador.posicao,
                        'nivel': jogador.nivel
                    })
                
                times_info.append({
                    'id': time.id,
                    'nome': time.nome,
                    'cor': time.cor,
                    'capitao': capitao.nome if capitao else 'Desconhecido',
                    'jogadores': jogadores,
                    'total_jogadores': len(jogadores)
                })
            
            emit('draft_status_update', {
                'draft_em_andamento': semana.draft_em_andamento,
                'finalizado': draft_status.finalizado if draft_status else False,
                'rodada_atual': draft_status.rodada_atual if draft_status else 1,
                'escolha_atual': draft_status.escolha_atual if draft_status else 1,
                'tempo_restante': draft_status.tempo_restante if draft_status else None,
                'tempo_configurado': semana.tempo_escolha,
                'vez_capitao_id': draft_status.vez_capitao_id if draft_status else None,
                'times': times_info
            })

# ======================================================
# APIs
# ======================================================

@app.route('/api/draft/status')
def api_draft_status():
    semana = get_semana_atual()
    draft_status = DraftStatus.query.filter_by(semana_id=semana.id).first()
    
    if not draft_status:
        return jsonify({'draft_em_andamento': semana.draft_em_andamento})
    
    times = Time.query.filter_by(semana_id=semana.id).order_by(Time.ordem_escolha).all()
    
    times_info = []
    for time in times:
        capitao = Jogador.query.get(time.capitao_id)
        escolhas = EscolhaDraft.query.filter_by(
            semana_id=semana.id,
            time_id=time.id
        ).order_by(EscolhaDraft.ordem_escolha).all()
        
        jogadores = []
        for escolha in escolhas:
            jogador = Jogador.query.get(escolha.jogador_id)
            jogadores.append({
                'id': jogador.id,
                'nome': jogador.nome,
                'apelido': jogador.apelido,
                'posicao': jogador.posicao,
                'nivel': jogador.nivel
            })
        
        times_info.append({
            'id': time.id,
            'nome': time.nome,
            'cor': time.cor,
            'capitao': capitao.nome if capitao else 'Desconhecido',
            'jogadores': jogadores,
            'total_jogadores': len(jogadores)
        })
    
    proximo_capitao = None
    if draft_status.vez_capitao_id:
        capitao = Jogador.query.get(draft_status.vez_capitao_id)
        if capitao:
            proximo_capitao = capitao.nome
    
    return jsonify({
        'draft_em_andamento': semana.draft_em_andamento,
        'finalizado': draft_status.finalizado,
        'rodada_atual': draft_status.rodada_atual,
        'escolha_atual': draft_status.escolha_atual,
        'tempo_restante': draft_status.tempo_restante,
        'tempo_configurado': semana.tempo_escolha,
        'vez_capitao': proximo_capitao,
        'times': times_info
    })

@app.route('/api/jogadores/disponiveis')
def api_jogadores_disponiveis():
    semana = get_semana_atual()
    
    if not semana.draft_em_andamento:
        return jsonify({'disponiveis': []})
    
    disponiveis = get_jogadores_disponiveis_draft(semana)
    
    jogadores_info = []
    for jogador in disponiveis:
        jogadores_info.append({
            'id': jogador.id,
            'nome': jogador.nome,
            'apelido': jogador.apelido,
            'posicao': jogador.posicao,
            'nivel': jogador.nivel,
            'mensalista': jogador.mensalista,
            'capitao': jogador.capitao
        })
    
    return jsonify({'disponiveis': jogadores_info})

# ======================================================
# UTILIDADES PARA TEMPLATES
# ======================================================

def format_date_func(value, format='%d/%m/%Y'):
    if value:
        if isinstance(value, datetime):
            return value.strftime(format)
        elif isinstance(value, date):
            return value.strftime(format)
    return ''

def get_jogador_nome_func(jogador):
    """Recebe um objeto Jogador ou ID"""
    try:
        if jogador is None:
            return 'Desconhecido'
        
        # Se já tem atributo nome
        if hasattr(jogador, 'nome'):
            return jogador.nome
        
        # Tenta como ID
        try:
            jogador_id = int(jogador)
            jogador_obj = Jogador.query.get(jogador_id)
            return jogador_obj.nome if jogador_obj else 'Desconhecido'
        except (ValueError, TypeError):
            return str(jogador) if jogador else 'Desconhecido'
            
    except Exception:
        return 'Desconhecido'

def get_time_nome_func(time):
    """Recebe um objeto Time ou ID"""
    try:
        if time is None:
            return 'Desconhecido'
        
        # Se já tem atributo nome
        if hasattr(time, 'nome'):
            return time.nome
        
        # Tenta como ID
        try:
            time_id = int(time)
            time_obj = Time.query.get(time_id)
            return time_obj.nome if time_obj else 'Desconhecido'
        except (ValueError, TypeError):
            return str(time) if time else 'Desconhecido'
            
    except Exception:
        return 'Desconhecido'

def get_posicao_display_func(posicao):
    if not posicao:
        return 'Não informada'
    
    posicoes = {
        'levantador': 'Levantador',
        'ponteiro': 'Ponteiro',
        'central': 'Central',
        'libero': 'Líbero',
        'oposto': 'Oposto'
    }
    return posicoes.get(posicao, posicao)

def get_nivel_display_func(nivel):
    if not nivel:
        return 'Não informado'
    
    niveis = {
        'iniciante': 'Iniciante',
        'intermediario': 'Intermediário',
        'avancado': 'Avançado'
    }
    return niveis.get(nivel, nivel)

def calcular_idade_func(data_nascimento):
    if not data_nascimento:
        return None
    hoje = date.today()
    idade = hoje.year - data_nascimento.year
    if (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day):
        idade -= 1
    return idade

# Registra como filtros (para uso com | nos templates)
@app.template_filter('format_date')
def format_date_filter(value, format='%d/%m/%Y'):
    return format_date_func(value, format)

@app.template_filter('get_jogador_nome')
def get_jogador_nome_filter(jogador):
    return get_jogador_nome_func(jogador)

@app.template_filter('get_time_nome')
def get_time_nome_filter(time):
    return get_time_nome_func(time)

@app.template_filter('get_posicao_display')
def get_posicao_display_filter(posicao):
    return get_posicao_display_func(posicao)

@app.template_filter('get_nivel_display')
def get_nivel_display_filter(nivel):
    return get_nivel_display_func(nivel)

# Context processor - disponibiliza funções globais
@app.context_processor
def utility_processor():
    return {
        # Funções auxiliares
        'format_date': format_date_func,
        'get_jogador_nome': get_jogador_nome_func,
        'get_time_nome': get_time_nome_func,
        'get_posicao_display': get_posicao_display_func,
        'get_nivel_display': get_nivel_display_func,
        'calcular_idade': calcular_idade_func,
        
        # Outras utilidades
        'get_semana_atual': get_semana_atual,
        'datetime': datetime,
        'date': date
    }

# ======================================================
# INICIALIZAÇÃO DO SISTEMA
# ======================================================

def criar_admin_padrao():
    """Cria usuário admin padrão se não existir"""
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            password=generate_password_hash('admin123'),
            email='admin@volei.com',
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        print('✅ Usuário admin criado: admin / admin123')

with app.app_context():
    db.create_all()
    criar_admin_padrao()
    
    # Cria pasta de uploads se não existir
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Verifica se existe semana atual
    get_semana_atual()

# ======================================================
# EXECUÇÃO
# ======================================================

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)