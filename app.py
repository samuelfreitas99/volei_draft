import os
import secrets
from datetime import datetime, date, timedelta, timezone
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, jsonify
)

from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user,
    login_required, logout_user, current_user
)

from flask_socketio import SocketIO, emit, join_room, leave_room

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import func, or_

# ======================================================
# CONFIGURAÇÃO
# ======================================================

app = Flask(__name__)

# SECRET KEY
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))

# Ambiente
FLASK_ENV = os.getenv("FLASK_ENV", "production")

# =========================
# BANCO DE DADOS
# =========================
# Sempre SQLite por enquanto (DEV e PROD)
# Seguro, simples e já em produção
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "instance", "volei_draft.db")

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL não definida")

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# =========================
# SESSÃO E TEMPLATES
# =========================
app.config["TEMPLATES_AUTO_RELOAD"] = FLASK_ENV == "development"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=31)
app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=31)
app.config["SESSION_REFRESH_EACH_REQUEST"] = True

# =========================
# UPLOADS
# =========================
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2MB

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# =========================
# EXTENSÕES
# =========================
db = SQLAlchemy(app)

socketio = SocketIO(
    app,
    async_mode="gevent",
    cors_allowed_origins="*"
)

# =========================
# LOGIN
# =========================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# =========================
# CONSTANTES DO SISTEMA
# =========================
TEMPO_ESCOLHA = 30  # segundos
VALOR_PADRAO_JOGO = 7.00


# ======================================================
# MODELOS (atualizados)
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

class PixInfo(db.Model):
    """Informações de PIX"""
    __table_args__ = {'extend_existing': True}  # ADICIONE ESTA LINHA
    id = db.Column(db.Integer, primary_key=True)
    chave_pix = db.Column(db.String(100), nullable=False)
    tipo_chave = db.Column(db.String(50), default='cpf')
    nome_recebedor = db.Column(db.String(100), nullable=False)
    cidade_recebedor = db.Column(db.String(100))
    descricao = db.Column(db.String(200))
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # NOVOS CAMPOS
    para_todas_semanas = db.Column(db.Boolean, default=True)
    semana_id = db.Column(db.Integer, db.ForeignKey('semana.id'), nullable=True)
    
    # RELACIONAMENTO
    semana = db.relationship('Semana', backref='pix_especificos', foreign_keys=[semana_id])
    
    def __repr__(self):
        return f'<PixInfo {self.chave_pix}>'

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
    
    # NOVOS CAMPOS
    para_todas_semanas = db.Column(db.Boolean, default=True)
    semana_id = db.Column(db.Integer, db.ForeignKey('semana.id'), nullable=True)
    
    # RELACIONAMENTO
    semana = db.relationship('Semana', backref='recados_especificos', foreign_keys=[semana_id])
    
    def __repr__(self):
        return f'<Recado {self.titulo}>'

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

class ConfiguracaoGlobal(db.Model):
    """Configurações globais do sistema"""
    id = db.Column(db.Integer, primary_key=True)
    dias_semana_fixos = db.Column(db.String(100), default='')  # Ex: "2,4,6" para terça, quinta, sábado
    duracao_mensalidade_dias = db.Column(db.Integer, default=30)
    senha_visitante = db.Column(db.String(50), default='volei123')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_dias_semana(self):
        """Retorna lista de dias da semana fixos"""
        if not self.dias_semana_fixos:
            return []
        return [int(dia) for dia in self.dias_semana_fixos.split(',') if dia.strip().isdigit()]


class CicloMensalidade(db.Model):
    """Ciclo de referência para mensalidades"""
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    descricao = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<CicloMensalidade {self.data_inicio} a {self.data_fim}>'
    
class PagamentoCofre(db.Model):
    """Registro de pagamentos no cofrinho por semana"""
    id = db.Column(db.Integer, primary_key=True)
    semana_id = db.Column(db.Integer, db.ForeignKey('semana.id'), nullable=False)
    jogador_id = db.Column(db.Integer, db.ForeignKey('jogador.id'), nullable=False)
    valor = db.Column(db.Float, default=07.00)  # Valor padrão por jogo
    pago = db.Column(db.Boolean, default=False)
    pago_em = db.Column(db.DateTime)
    metodo_pagamento = db.Column(db.String(20), default='dinheiro')  # dinheiro, pix, cartao
    observacao = db.Column(db.String(200))
    registrado_por = db.Column(db.String(100))  # Quem registrou o pagamento
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    semana = db.relationship('Semana', backref='pagamentos_cofre')
    jogador = db.relationship('Jogador', backref='pagamentos_cofre')
    
    def __repr__(self):
        return f'<PagamentoCofre {self.jogador.nome} - R${self.valor} - {self.semana.data}>'

class MovimentoCofre(db.Model):
    """Movimentações do cofrinho (entradas, saídas, ajustes)"""
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)  # entrada, saida, ajuste, deposito, retirada
    valor = db.Column(db.Float, nullable=False)
    descricao = db.Column(db.String(200), nullable=False)
    semana_id = db.Column(db.Integer, db.ForeignKey('semana.id'), nullable=True)  # Pode ser vinculado a uma semana
    observacao = db.Column(db.Text)
    usuario = db.Column(db.String(100))  # Quem fez a movimentação
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamento
    semana = db.relationship('Semana', backref='movimentos_cofre')
    
    def __repr__(self):
        return f'<MovimentoCofre {self.tipo} - R${self.valor} - {self.descricao}>'

class MetaCofre(db.Model):
    """Metas do cofrinho (compras futuras, objetivos)"""
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    valor_meta = db.Column(db.Float, nullable=False)
    valor_atual = db.Column(db.Float, default=0.00)
    data_limite = db.Column(db.Date)
    prioridade = db.Column(db.Integer, default=1)  # 1-5, onde 5 é mais alta
    status = db.Column(db.String(20), default='ativo')  # ativo, concluido, cancelado
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<MetaCofre {self.titulo} - R${self.valor_meta}>'    
   

# ======================================================
# FUNÇÕES AUXILIARES
# ======================================================

def verificar_dependencias_jogador(jogador_id):
    """Verifica se há dependências que impedem a exclusão do jogador"""
    dependencias = []
    
    # Verifica pagamentos do cofre
    pagamentos = PagamentoCofre.query.filter_by(jogador_id=jogador_id).count()
    if pagamentos > 0:
        dependencias.append(f"{pagamentos} pagamento(s) no cofre")
    
    # Verifica confirmações
    confirmacoes = Confirmacao.query.filter_by(jogador_id=jogador_id).count()
    if confirmacoes > 0:
        dependencias.append(f"{confirmacoes} confirmação(ões) de presença")
    
    # Verifica times como capitão
    times_capitao = Time.query.filter_by(capitao_id=jogador_id).count()
    if times_capitao > 0:
        dependencias.append(f"capitão em {times_capitao} time(s)")
    
    # Verifica escolhas de draft
    escolhas = EscolhaDraft.query.filter_by(jogador_id=jogador_id).count()
    if escolhas > 0:
        dependencias.append(f"{escolhas} escolha(s) em drafts")
    
    return dependencias

def obter_ciclo_sistema_ativo():
    """Obtém o ciclo ativo do sistema (configuração de ciclos)"""
    # Busca o ciclo ativo na tabela CicloMensalidade
    ciclo_ativo = CicloMensalidade.query.filter_by(ativo=True).first()
    
    if ciclo_ativo:
        return ciclo_ativo.data_inicio, ciclo_ativo.data_fim, True
    else:
        # Se não há ciclo ativo, retorna None
        return None, None, False

def sincronizar_capitao_permissao(jogador_id):
    """Sincroniza permissões de capitão entre Jogador e User"""
    jogador = Jogador.query.get(jogador_id)
    if not jogador:
        return False
    
    # Se jogador é capitão, verifica se o User tem role correta
    if jogador.capitao:
        if jogador.user:
            if jogador.user.role != 'capitao':
                jogador.user.role = 'capitao'
                print(f"⚠️ Corrigido: User {jogador.user.username} agora tem role 'capitao'")
                db.session.commit()
                return True
        else:
            # Cria usuário para capitão se não existir
            username, password = criar_usuario_para_jogador(jogador, 'capitao')
            print(f"✅ Criado usuário para capitão {jogador.nome}: {username}")
            return True
    
    # Se jogador NÃO é capitão, mas o User tem role 'capitao'
    elif jogador.user and jogador.user.role == 'capitao':
        jogador.user.role = 'jogador'
        print(f"⚠️ Corrigido: User {jogador.user.username} agora tem role 'jogador'")
        db.session.commit()
    
    return False

def obter_jogadores_no_ciclo_atual():
    """Retorna jogadores que estão no ciclo atual"""
    ciclo_inicio, ciclo_fim = obter_ciclo_das_configuracoes()
    
    if not ciclo_inicio or not ciclo_fim:
        return []
    
    jogadores_no_ciclo = Jogador.query.filter(
        Jogador.mensalista == True,
        Jogador.ativo == True,
        Jogador.data_inicio_mensalidade == ciclo_inicio,
        Jogador.data_fim_mensalidade == ciclo_fim
    ).order_by(Jogador.nome).all()
    
    return jogadores_no_ciclo

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Acesso restrito a administradores!', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def criar_semanas_automaticas():
    """Cria semanas automaticamente baseado nos dias fixos configurados e ciclo ativo"""
    config_global = ConfiguracaoGlobal.query.first()
    if not config_global:
        return
    
    hoje = date.today()
    
    # Busca o ciclo ativo do sistema
    ciclo_inicio, ciclo_fim, ciclo_existe = obter_ciclo_sistema_ativo()
    
    # Dias da semana configurados
    dias_semana = []
    if config_global.dias_semana_fixos:
        dias_semana = config_global.get_dias_semana()
    else:
        # Se não houver dias configurados, não cria semanas
        print("⚠️ Nenhum dia da semana configurado. Configure os dias em /admin/configuracoes")
        return
    
    if not dias_semana:
        print("⚠️ Nenhum dia da semana selecionado.")
        return
    
    # Determina até quando criar semanas
    if ciclo_existe and ciclo_inicio and ciclo_fim:
        # Se há ciclo ativo, cria semanas apenas dentro do ciclo
        data_limite = ciclo_fim
        print(f"✅ Usando ciclo ativo: criando semanas de {ciclo_inicio.strftime('%d/%m/%Y')} a {data_limite.strftime('%d/%m/%Y')}")
        
        # Ajusta o início para hoje ou início do ciclo (o que for maior)
        data_inicio_criacao = max(hoje, ciclo_inicio)
    else:
        # Se não há ciclo ativo, usa os próximos 30 dias (comportamento padrão)
        data_inicio_criacao = hoje
        data_limite = hoje + timedelta(days=30)
        print(f"✅ Sem ciclo ativo: criando semanas para os próximos 30 dias")
    
    semanas_criadas = 0
    data_atual = data_inicio_criacao
    
    print(f"📅 Período de criação: {data_atual.strftime('%d/%m/%Y')} até {data_limite.strftime('%d/%m/%Y')}")
    print(f"🎯 Dias de jogo configurados: {', '.join([get_dia_semana_curto(d) for d in dias_semana])}")
    
    # Cria semanas até a data limite
    while data_atual <= data_limite:
        if data_atual.weekday() in dias_semana:
            semana_existente = Semana.query.filter_by(data=data_atual).first()
            if not semana_existente:
                semana = Semana(
                    data=data_atual,
                    descricao=f'Jogo de Vôlei - {data_atual.strftime("%d/%m/%Y")}',
                    lista_aberta=True,
                    max_times=2,
                    max_jogadores_por_time=6
                )
                db.session.add(semana)
                semanas_criadas += 1
                print(f"  ➕ Semana criada para {data_atual.strftime('%d/%m/%Y')} ({get_dia_semana_curto(data_atual.weekday())})")
        
        data_atual += timedelta(days=1)
    
    try:
        db.session.commit()
        if semanas_criadas > 0:
            print(f"✅ {semanas_criadas} semanas criadas automaticamente")
        else:
            print("ℹ️ Nenhuma semana nova criada")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao criar semanas: {e}")
    
    return semanas_criadas
    
@app.route('/admin/limpar_semanas_fora_ciclo')
@admin_required
def limpar_semanas_fora_ciclo():
    """Remove semanas criadas além da data final do ciclo ativo"""
    # Busca o ciclo ativo do sistema
    ciclo_inicio, ciclo_fim, ciclo_existe = obter_ciclo_sistema_ativo()
    
    if not ciclo_existe:
        flash('Nenhum ciclo ativo encontrado! Crie um ciclo primeiro em "Gerenciar Ciclos".', 'warning')
        return redirect(url_for('admin_configuracoes'))
    
    print(f"🔍 Buscando semanas após o fim do ciclo ({format_date_func(ciclo_fim)})...")
    
    # Busca semanas criadas após o fim do ciclo
    semanas_fora_ciclo = Semana.query.filter(
        Semana.data > ciclo_fim
    ).order_by(Semana.data).all()
    
    if not semanas_fora_ciclo:
        flash(f'Não há semanas após o fim do ciclo atual ({format_date_func(ciclo_fim)})!', 'info')
        return redirect(url_for('admin_configuracoes'))
    
    # Lista as semanas que serão removidas
    semanas_para_remover = []
    for semana in semanas_fora_ciclo:
        semanas_para_remover.append({
            'id': semana.id,
            'data': semana.data,
            'dia_semana': get_dia_semana_curto(semana.data.weekday()),
            'status': 'Draft Finalizado' if semana.draft_finalizado else 
                     'Draft em Andamento' if semana.draft_em_andamento else 
                     'Lista Aberta' if semana.lista_aberta else 'Lista Fechada'
        })
    
    # Remove semanas fora do ciclo
    removidas = 0
    for semana in semanas_fora_ciclo:
        try:
            # Impede remoção de semanas com draft finalizado que já aconteceram
            if semana.draft_finalizado and semana.data < date.today():
                print(f"⚠️ Mantida semana de {format_date_func(semana.data)} (draft finalizado no passado)")
                continue
            
            # Remove dados relacionados
            Confirmacao.query.filter_by(semana_id=semana.id).delete()
            ListaEspera.query.filter_by(semana_id=semana.id).delete()
            Time.query.filter_by(semana_id=semana.id).delete()
            EscolhaDraft.query.filter_by(semana_id=semana.id).delete()
            DraftStatus.query.filter_by(semana_id=semana.id).delete()
            HistoricoDraft.query.filter_by(semana_id=semana.id).delete()
            
            # Remove a semana
            db.session.delete(semana)
            removidas += 1
            print(f"🗑️ Removida semana de {format_date_func(semana.data)} (fora do ciclo)")
        except Exception as e:
            print(f"⚠️ Erro ao remover semana {semana.id}: {e}")
    
    if removidas > 0:
        db.session.commit()
        
        # Cria relatório das semanas removidas
        relatorio = "\n".join([f"• {s['data'].strftime('%d/%m/%Y')} ({s['dia_semana']}) - {s['status']}" 
                              for s in semanas_para_remover[:10]])
        if len(semanas_para_remover) > 10:
            relatorio += f"\n• ... e mais {len(semanas_para_remover) - 10} semanas"
        
        flash(f'{removidas} semana(s) removida(s) por estarem após o fim do ciclo!', 'success')
        
        # Log detalhado
        print(f"📋 Relatório de remoção:")
        print(f"Ciclo ativo: {format_date_func(ciclo_inicio)} a {format_date_func(ciclo_fim)}")
        print(f"Semanas removidas: {removidas}")
        for s in semanas_para_remover[:5]:
            print(f"  - {s['data'].strftime('%d/%m/%Y')} ({s['dia_semana']})")
    else:
        flash('Nenhuma semana removida.', 'info')
    
    return redirect(url_for('admin_configuracoes'))


def get_semana_atual():
    """Obtém a PRÓXIMA semana de vôlei, não necessariamente hoje"""
    hoje = date.today()
    
    # Verifica se hoje é um dia de vôlei configurado
    config_global = ConfiguracaoGlobal.query.first()
    dias_volei = []
    
    if config_global and config_global.dias_semana_fixos:
        dias_volei = [int(dia) for dia in config_global.dias_semana_fixos.split(',') if dia.strip().isdigit()]
    
    # Se hoje é dia de vôlei, usa hoje
    if hoje.weekday() in dias_volei:
        semana = Semana.query.filter_by(data=hoje).first()
        if semana:
            atualizar_lista_espera_automaticamente(semana)
            return semana
    
    # Se não, busca a PRÓXIMA semana de vôlei
    for i in range(1, 15):  # Próximos 15 dias
        data_futura = hoje + timedelta(days=i)
        if data_futura.weekday() in dias_volei:
            semana = Semana.query.filter_by(data=data_futura).first()
            if semana:
                atualizar_lista_espera_automaticamente(semana)
                return semana
    
    # Se não encontrou nenhuma, cria uma para o próximo dia de vôlei
    if dias_volei:
        for i in range(1, 8):
            data_futura = hoje + timedelta(days=i)
            if data_futura.weekday() in dias_volei:
                try:
                    semana = Semana(
                        data=data_futura,
                        descricao=f'Jogo de Vôlei - {data_futura.strftime("%d/%m/%Y")}',
                        lista_aberta=True
                    )
                    db.session.add(semana)
                    db.session.commit()
                    return semana
                except:
                    db.session.rollback()
                    break
    
    # Fallback: cria semana para hoje
    try:
        semana = Semana(
            data=hoje,
            descricao=f'Jogo de Vôlei - {hoje.strftime("%d/%m/%Y")}',
            lista_aberta=True
        )
        db.session.add(semana)
        db.session.commit()
        return semana
    except:
        db.session.rollback()
        return Semana.query.filter_by(data=hoje).first()

def atualizar_mensalidades_periodo(data_inicio, data_fim):
    """Atualiza período da mensalidade para todos os mensalistas"""
    mensalistas = Jogador.query.filter_by(mensalista=True, ativo=True).all()
    
    for jogador in mensalistas:
        jogador.data_inicio_mensalidade = data_inicio
        jogador.data_fim_mensalidade = data_fim
    
    db.session.commit()
    return len(mensalistas)

def emitir_atualizacao_publica(semana_id, jogador_id, jogador_nome, time_id, time_nome):
    """Emite atualização específica para o público"""
    try:
        socketio.emit('player_selected_public', {
            'semana_id': semana_id,
            'jogador_id': jogador_id,
            'jogador_nome': jogador_nome,
            'time_id': time_id,
            'time_nome': time_nome,
            'timestamp': datetime.utcnow().isoformat()
        }, room=f'draft_public_{semana_id}')
        print(f"📢 Emitido player_selected_public para draft_public_{semana_id}")
    except Exception as e:
        print(f"❌ Erro ao emitir para público: {e}")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ======================================================
# MIDDLEWARE DE VERIFICAÇÃO DE PERMISSÕES
# ======================================================

@app.before_request
def check_profile_completion():
    """Verifica se usuário precisa completar perfil"""
    if current_user.is_authenticated:
        # Ignora rotas específicas
        exempt_routes = ['completar_perfil', 'logout', 'static', 'login']
        if request.endpoint in exempt_routes:
            return
        
        # Se usuário é admin, não precisa de jogador
        if current_user.role == 'admin':
            return
        
        # Se usuário não tem jogador vinculado
        if not current_user.jogador_id:
            # Se já está tentando acessar completar perfil, permite
            if request.endpoint != 'completar_perfil':
                flash('Complete seu perfil de jogador para continuar.', 'info')
                return redirect(url_for('completar_perfil'))

@app.before_request
def verificar_permissao_capitao():
    """Verifica e corrige permissões de capitão a cada request"""
    if current_user.is_authenticated and current_user.jogador:
        # Se user tem role 'capitao' mas jogador não é capitão
        if current_user.role == 'capitao' and not current_user.jogador.capitao:
            current_user.role = 'jogador'
            db.session.commit()
            print(f"⚠️ Corrigido: {current_user.username} não é mais capitão")
        
        # Se jogador é capitão mas user não tem role 'capitao'
        elif current_user.jogador.capitao and current_user.role != 'capitao':
            current_user.role = 'capitao'
            db.session.commit()
            print(f"⚠️ Corrigido: {current_user.username} agora é capitão")


def capitao_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Faça login para acessar!', 'danger')
            return redirect(url_for('login'))
        
        # Verifica se é admin (admins podem acessar tudo)
        if current_user.role == 'admin':
            return f(*args, **kwargs)
        
        # Verifica se é capitão
        if current_user.role != 'capitao':
            flash('Acesso restrito a capitães!', 'danger')
            return redirect(url_for('index'))
        
        # Verifica se tem jogador vinculado e é capitão
        if not current_user.jogador:
            flash('Você não tem um perfil de jogador vinculado!', 'danger')
            return redirect(url_for('perfil'))
        
        # Sincroniza permissões antes de verificar
        if not current_user.jogador.capitao:
            # Tenta sincronizar
            sincronizar_capitao_permissao(current_user.jogador_id)
            db.session.refresh(current_user)
            
            # Verifica novamente
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
    """Atualiza lista de espera APENAS para convidados - mensalistas NÃO entram"""
    # ANTIGO: Adicionava mensalistas não confirmados à lista de espera
    # NOVO: Apenas verifica se há convidados na lista de espera que podem ser promovidos
    
    # Lista de espera existente (apenas convidados)
    lista_espera_existente = ListaEspera.query.filter_by(
        semana_id=semana.id,
        promovido=False
    ).count()
    
    # Verifica se há vagas e convidados na lista de espera
    total_confirmados = Confirmacao.query.filter_by(
        semana_id=semana.id,
        confirmado=True
    ).count()
    
    total_vagas = semana.max_times * semana.max_jogadores_por_time
    vagas_disponiveis = total_vagas - total_confirmados
    
    # Se há vagas e convidados na lista de espera, podemos promover alguns
    if vagas_disponiveis > 0 and lista_espera_existente > 0:
        # Log para debug
        print(f"✅ Há {vagas_disponiveis} vagas e {lista_espera_existente} convidados na lista de espera")
        # A promoção manual é feita pelo admin via botão "Cadastrar"
    
    # REMOVIDO: Código que adicionava mensalistas automaticamente à lista de espera
    
    db.session.commit()

def verificar_mensalidades_vencidas():
    """Verifica e atualiza status de mensalistas vencidos"""
    hoje = date.today()
    mensalistas = Jogador.query.filter_by(mensalista=True, ativo=True).all()
    
    for jogador in mensalistas:
        if jogador.data_fim_mensalidade and jogador.data_fim_mensalidade < hoje:
            # Se a mensalidade está vencida e não foi paga, remove de mensalista
            if not jogador.mensalidade_paga:
                jogador.mensalista = False
                jogador.mensalidade_paga = False
                db.session.commit()
                print(f"⚠️ Jogador {jogador.nome} removido de mensalista - mensalidade vencida")

def inicializar_draft(semana, tempo_por_escolha=None, modo_draft=None, max_times=None, max_jogadores_por_time=None):
    """Inicializa o draft com os times e status - SEM TIMER"""
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
    # SEMPRE define tempo como 0 (sem tempo)
    semana.tempo_escolha = 0
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
    
    # Inicializa status do draft - SEM TEMPO
    draft_status = DraftStatus(
        semana_id=semana.id,
        vez_capitao_id=capitaes[0].id,
        rodada_atual=1,
        escolha_atual=len(times) + 1,
        tempo_restante=None,  # Sem tempo
        finalizado=False,
        modo_snake=(semana.modo_draft == 'snake')
    )
    db.session.add(draft_status)
    
    # Atualiza status da semana
    semana.draft_em_andamento = True
    semana.lista_aberta = False
    semana.lista_encerrada = True
    
    db.session.commit()
    
    # Emite atualização inicial
    emitir_status_draft_atualizado(semana.id)
    
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

# ======================================================
# FUNÇÕES AUXILIARES (ADICIONAR/ATUALIZAR)
# ======================================================

def obter_dias_volei():
    """Retorna os dias de vôlei configurados (dias fixos OU baseado em ciclo)"""
    config_global = ConfiguracaoGlobal.query.first()
    if not config_global:
        return [3]  # Padrão: quintas-feiras
    
    # Se tem dias fixos configurados, usa eles
    if config_global.dias_semana_fixos:
        return config_global.get_dias_semana()
    
    # Se não, usa as quintas do ciclo atual
    ciclo_inicio, ciclo_fim, _ = obter_ciclo_atual_mensalidade()
    if ciclo_inicio and ciclo_fim:
        # Retorna apenas quintas (3) dentro do ciclo
        return [3]  # Ou pode calcular outros dias baseado no ciclo
    
    # Fallback: quintas-feiras
    return [3]

def get_semana_atual():
    """Obtém a PRÓXIMA semana de vôlei usando o sistema configurado"""
    hoje = date.today()
    dias_volei = obter_dias_volei()
    
    # Se hoje é dia de vôlei, usa hoje
    if hoje.weekday() in dias_volei:
        semana = Semana.query.filter_by(data=hoje).first()
        if semana:
            atualizar_lista_espera_automaticamente(semana)
            return semana
    
    # Se não, busca a PRÓXIMA semana de vôlei
    for i in range(1, 15):  # Próximos 15 dias
        data_futura = hoje + timedelta(days=i)
        if data_futura.weekday() in dias_volei:
            semana = Semana.query.filter_by(data=data_futura).first()
            if semana:
                atualizar_lista_espera_automaticamente(semana)
                return semana
    
    # Se não encontrou, cria uma
    if dias_volei:
        for i in range(1, 8):
            data_futura = hoje + timedelta(days=i)
            if data_futura.weekday() in dias_volei:
                try:
                    semana = Semana(
                        data=data_futura,
                        descricao=f'Jogo de Vôlei - {data_futura.strftime("%d/%m/%Y")}',
                        lista_aberta=True
                    )
                    db.session.add(semana)
                    db.session.commit()
                    return semana
                except:
                    db.session.rollback()
                    break
    
    # Fallback
    return Semana.query.filter(Semana.data >= hoje).order_by(Semana.data).first()

def emitir_status_draft_atualizado(semana_id):
    """Emite atualização do status do draft via SocketIO - CORRIGIDA"""
    semana = Semana.query.get(semana_id)
    if not semana:
        return
    
    draft_status = DraftStatus.query.filter_by(semana_id=semana.id).first()
    if not draft_status:
        return
    
    # Busca todos os times
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
            'capitao_id': capitao.id if capitao else None,
            'jogadores': jogadores,
            'total_jogadores': len(jogadores)
        })
    
    # Verifica quem é o próximo capitão
    proximo_capitao = None
    if draft_status.vez_capitao_id:
        capitao_obj = Jogador.query.get(draft_status.vez_capitao_id)
        if capitao_obj:
            proximo_capitao = capitao_obj.nome
    
    # Emite atualização para todos conectados ao draft
    socketio.emit('draft_status_update', {
        'semana_id': semana.id,
        'draft_em_andamento': semana.draft_em_andamento,
        'finalizado': draft_status.finalizado,
        'rodada_atual': draft_status.rodada_atual,
        'escolha_atual': draft_status.escolha_atual,
        'tempo_restante': draft_status.tempo_restante if semana.tempo_escolha > 0 else None,
        'vez_capitao_id': draft_status.vez_capitao_id,
        'capitao_atual': proximo_capitao,
        'times': times_info
    }, room=f'draft_{semana.id}')

def inicializar_draft(semana, tempo_por_escolha=None, modo_draft=None, max_times=None, max_jogadores_por_time=None):
    """Inicializa o draft com os times e status - CORRIGIDA"""
    # Remove dados anteriores do draft
    Time.query.filter_by(semana_id=semana.id).delete()
    EscolhaDraft.query.filter_by(semana_id=semana.id).delete()
    DraftStatus.query.filter_by(semana_id=semana.id).delete()
    HistoricoDraft.query.filter_by(semana_id=semana.id).delete()  # Limpa histórico também
    
    # Usa configurações da semana ou os parâmetros fornecidos
    if max_times:
        semana.max_times = max_times
    if max_jogadores_por_time:
        semana.max_jogadores_por_time = max_jogadores_por_time
    if tempo_por_escolha is not None:  # Aceita 0 (sem timer)
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
    # Se tempo_por_escolha for 0, define tempo_restante como None (sem timer)
    tempo_inicial = None if tempo_por_escolha == 0 else semana.tempo_escolha
    
    draft_status = DraftStatus(
        semana_id=semana.id,
        vez_capitao_id=capitaes[0].id,
        rodada_atual=1,
        escolha_atual=len(times) + 1,  # Já contando com os capitães
        tempo_restante=tempo_inicial,
        finalizado=False,
        modo_snake=(semana.modo_draft == 'snake')
    )
    db.session.add(draft_status)
    
    # Atualiza status da semana
    semana.draft_em_andamento = True
    semana.lista_aberta = False
    semana.lista_encerrada = True
    
    db.session.commit()
    
    # Emite atualização inicial
    emitir_status_draft_atualizado(semana.id)
    
    return times, draft_status

@app.route('/admin/recriar_semanas_automaticas')
@admin_required
def recriar_semanas_automaticas():
    """Força a recriação de semanas automaticamente"""
    try:
        # Remove semanas futuras primeiro
        hoje = date.today()
        semanas_futuras = Semana.query.filter(Semana.data >= hoje).all()
        
        removidas = 0
        for semana in semanas_futuras:
            try:
                # Não remove semanas com draft em andamento ou finalizado
                if semana.draft_em_andamento or semana.draft_finalizado:
                    continue
                
                # Remove dados relacionados
                Confirmacao.query.filter_by(semana_id=semana.id).delete()
                ListaEspera.query.filter_by(semana_id=semana.id).delete()
                
                # Remove a semana
                db.session.delete(semana)
                removidas += 1
            except:
                pass
        
        if removidas > 0:
            db.session.commit()
            print(f"🗑️ {removidas} semanas futuras removidas")
        
        # Cria semanas automaticamente
        semanas_criadas = criar_semanas_automaticas()
        
        if semanas_criadas > 0:
            flash(f'{semanas_criadas} semanas recriadas automaticamente dentro do ciclo ativo!', 'success')
        else:
            flash('Nenhuma nova semana criada. Verifique a configuração do ciclo e dias da semana.', 'info')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao recriar semanas: {str(e)}', 'danger')
    
    return redirect(url_for('admin_configuracoes'))

# ======================================================
# NOVAS ROTAS PARA GESTÃO DE MENSALIDADES
# ======================================================

@app.route('/admin/semana/<int:id>/excluir')
@admin_required
def excluir_semana(id):
    """Exclui uma semana específica"""
    semana = Semana.query.get_or_404(id)
    
    # Impede exclusão de semana passada com histórico importante
    hoje = date.today()
    if semana.data < hoje and semana.draft_finalizado:
        flash('Não é possível excluir semanas passadas com draft finalizado!', 'danger')
        return redirect(url_for('admin_todas_semanas'))
    
    try:
        # Remove dados relacionados
        Confirmacao.query.filter_by(semana_id=id).delete()
        ListaEspera.query.filter_by(semana_id=id).delete()
        Time.query.filter_by(semana_id=id).delete()
        EscolhaDraft.query.filter_by(semana_id=id).delete()
        DraftStatus.query.filter_by(semana_id=id).delete()
        HistoricoDraft.query.filter_by(semana_id=id).delete()
        
        # Remove a semana
        db.session.delete(semana)
        db.session.commit()
        
        flash(f'Semana de {format_date_func(semana.data)} excluída com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir semana: {str(e)}', 'danger')
    
    return redirect(url_for('admin_todas_semanas'))

@app.route('/admin/semana/criar_manual', methods=['POST'])
@admin_required
def criar_semana_manual():
    """Cria uma semana manualmente"""
    data_str = request.form.get('data_semana')
    descricao = request.form.get('descricao', '')
    
    if not data_str:
        flash('Informe a data da semana!', 'danger')
        return redirect(url_for('admin_todas_semanas'))
    
    try:
        data = datetime.strptime(data_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Data inválida! Use o formato AAAA-MM-DD.', 'danger')
        return redirect(url_for('admin_todas_semanas'))
    
    # Verifica se já existe semana para esta data
    if Semana.query.filter_by(data=data).first():
        flash(f'Já existe uma semana para {format_date_func(data)}!', 'warning')
        return redirect(url_for('admin_todas_semanas'))
    
    try:
        semana = Semana(
            data=data,
            descricao=descricao or f'Jogo de Vôlei - {data.strftime("%d/%m/%Y")}',
            lista_aberta=True,
            max_times=2,
            max_jogadores_por_time=6
        )
        db.session.add(semana)
        db.session.commit()
        
        flash(f'Semana criada com sucesso para {format_date_func(data)}!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao criar semana: {str(e)}', 'danger')
    
    return redirect(url_for('admin_todas_semanas'))    

@app.route('/admin/semanas/todas')
@admin_required
def admin_todas_semanas():
    """Lista e gerencia todas as semanas"""
    # Filtros
    filtro_data = request.args.get('filtro_data', 'futuras')  # futuras, passadas, todas
    filtro_status = request.args.get('filtro_status', 'todas')  # todas, abertas, fechadas, draft
    
    hoje = date.today()
    
    # Query base
    query = Semana.query
    
    # Aplicar filtros de data
    if filtro_data == 'futuras':
        query = query.filter(Semana.data >= hoje)
    elif filtro_data == 'passadas':
        query = query.filter(Semana.data < hoje)
    # 'todas' não aplica filtro
    
    # Aplicar filtros de status
    if filtro_status == 'abertas':
        query = query.filter_by(lista_aberta=True)
    elif filtro_status == 'fechadas':
        query = query.filter_by(lista_encerrada=True, draft_em_andamento=False, draft_finalizado=False)
    elif filtro_status == 'draft_andamento':
        query = query.filter_by(draft_em_andamento=True)
    elif filtro_status == 'draft_finalizado':
        query = query.filter_by(draft_finalizado=True)
    # 'todas' não aplica filtro
    
    semanas = query.order_by(Semana.data).all()
    
    # Calcular estatísticas para cada semana
    semanas_com_info = []
    for semana in semanas:
        confirmados = Confirmacao.query.filter_by(semana_id=semana.id, confirmado=True).count()
        lista_espera = ListaEspera.query.filter_by(semana_id=semana.id, promovido=False).count()
        times = Time.query.filter_by(semana_id=semana.id).count()
        
        semanas_com_info.append({
            'semana': semana,
            'confirmados': confirmados,
            'lista_espera': lista_espera,
            'times': times,
            'total_vagas': semana.max_times * semana.max_jogadores_por_time
        })
    
    return render_template('admin/todas_semanas.html',
                         semanas_com_info=semanas_com_info,
                         hoje=hoje,
                         filtro_data=filtro_data,
                         filtro_status=filtro_status)

@app.route('/admin/relatorio/dias')
@admin_required
def relatorio_por_dia():
    """Relatório de frequência por dia da semana"""
    # Agrupa confirmações por dia da semana
    from collections import defaultdict
    
    hoje = date.today()
    um_mes_atras = hoje - timedelta(days=30)
    
    semanas = Semana.query.filter(
        Semana.data >= um_mes_atras,
        Semana.data <= hoje
    ).all()
    
    dados_por_dia = defaultdict(lambda: {'total': 0, 'confirmados': 0})
    
    for semana in semanas:
        dia_semana = semana.data.weekday()
        confirmados = semana.confirmacoes.filter_by(confirmado=True).count()
        
        dados_por_dia[dia_semana]['total'] += 1
        dados_por_dia[dia_semana]['confirmados'] += confirmados
    
    return render_template('admin/relatorio_dias.html', dados=dados_por_dia)

@app.route('/admin/semanas')
@admin_required
def admin_semanas():
    """Lista todas as semanas futuras"""
    hoje = date.today()
    semanas = Semana.query.filter(Semana.data >= hoje).order_by(Semana.data).all()
    
    # Estatísticas para cada semana
    semanas_com_stats = []
    for semana in semanas:
        confirmados = semana.confirmacoes.filter_by(confirmado=True).count()
        lista_espera = semana.lista_espera.filter_by(promovido=False).count()
        
        semanas_com_stats.append({
            'semana': semana,
            'confirmados': confirmados,
            'lista_espera': lista_espera,
            'total_vagas': semana.max_times * semana.max_jogadores_por_time
        })
    
    return render_template('admin/semanas.html', 
                         semanas_com_stats=semanas_com_stats,
                         hoje=hoje)

@app.route('/admin/mensalidades')
@admin_required
def admin_mensalidades():
    """Painel completo de gestão de mensalidades"""
    resumo = obter_resumo_mensalidades()
    
    # Busca todos os mensalistas com detalhes
    mensalistas = Jogador.query.filter_by(mensalista=True, ativo=True).order_by(Jogador.nome).all()
    
    # Separa por status
    mensalistas_pagos = []
    mensalistas_pendentes = []
    mensalistas_vencidos = []
    
    hoje = date.today()
    
    for jogador in mensalistas:
        status = {
            'jogador': jogador,
            'dias_restantes': None,
            'status': 'desconhecido'
        }
        
        if jogador.data_fim_mensalidade:
            dias = (jogador.data_fim_mensalidade - hoje).days
            status['dias_restantes'] = dias
            
            if jogador.mensalidade_paga:
                if dias >= 0:
                    status['status'] = 'pago'
                    mensalistas_pagos.append(status)
                else:
                    status['status'] = 'vencido'
                    mensalistas_vencidos.append(status)
            else:
                if dias >= 0:
                    status['status'] = 'pendente'
                    mensalistas_pendentes.append(status)
                else:
                    status['status'] = 'vencido_pendente'
                    mensalistas_vencidos.append(status)
        else:
            status['status'] = 'sem_data'
            mensalistas_pendentes.append(status)
    
    # Calcula próximo ciclo sugerido
    proximo_inicio, proximo_fim = calcular_proximo_ciclo_mensalidade()
    
    return render_template('admin/mensalidades.html',
                         resumo=resumo,
                         mensalistas_pagos=mensalistas_pagos,
                         mensalistas_pendentes=mensalistas_pendentes,
                         mensalistas_vencidos=mensalistas_vencidos,
                         proximo_inicio=proximo_inicio,
                         proximo_fim=proximo_fim)

@app.route('/admin/mensalidade/definir_ciclo', methods=['GET', 'POST'])
@admin_required
def definir_ciclo_mensalidade():
    """Define novo ciclo de mensalidade para mensalistas - ATUALIZADA"""
    if request.method == 'POST':
        data_inicio_str = request.form.get('data_inicio')
        data_fim_str = request.form.get('data_fim')
        acao = request.form.get('acao', 'todos')  # todos, apenas_pagos, apenas_selecionados
        
        # IDs de jogadores selecionados (se acao for 'apenas_selecionados')
        jogadores_selecionados = request.form.getlist('jogadores_selecionados')
        
        if not data_inicio_str or not data_fim_str:
            flash('Informe as datas de início e fim!', 'danger')
            return redirect(url_for('definir_ciclo_mensalidade'))
        
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Datas inválidas! Use o formato AAAA-MM-DD.', 'danger')
            return redirect(url_for('definir_ciclo_mensalidade'))
        
        if data_fim <= data_inicio:
            flash('A data de fim deve ser posterior à data de início!', 'danger')
            return redirect(url_for('definir_ciclo_mensalidade'))
        
        # NOVO: Define este ciclo como ciclo de referência ativo
        definir_ciclo_manual(data_inicio, data_fim, f"Ciclo criado via definição em lote")
        
        # Aplica o ciclo conforme a ação selecionada
        if acao == 'todos':
            # Atualiza todos os mensalistas
            quantos = atualizar_mensalidades_periodo(data_inicio, data_fim)
            flash(f'Ciclo definido para {quantos} mensalistas e salvo como ciclo ativo do sistema! De {format_date_func(data_inicio)} a {format_date_func(data_fim)}', 'success')
            
        elif acao == 'apenas_pagos':
            # Apenas para mensalistas com pagamento confirmado
            mensalistas_pagos = Jogador.query.filter_by(mensalista=True, mensalidade_paga=True, ativo=True).all()
            for jogador in mensalistas_pagos:
                jogador.data_inicio_mensalidade = data_inicio
                jogador.data_fim_mensalidade = data_fim
            db.session.commit()
            flash(f'Ciclo definido para {len(mensalistas_pagos)} mensalistas com pagamento confirmado e salvo como ciclo ativo do sistema!', 'success')
            
        elif acao == 'apenas_selecionados' and jogadores_selecionados:
            # Para jogadores específicos selecionados
            quantos = renovar_mensalidade_em_lote(jogadores_selecionados, data_inicio, data_fim)
            flash(f'Ciclo definido para {quantos} jogadores selecionados e salvo como ciclo ativo do sistema!', 'success')
        
        return redirect(url_for('admin_mensalidades'))
    
    # Calcula datas sugeridas
    hoje = date.today()
    
    # Verifica se há um ciclo ativo no sistema
    ciclo_atual_inicio, ciclo_atual_fim = obter_ciclo_das_configuracoes()
    
    if ciclo_atual_inicio and ciclo_atual_fim:
        # Sugere o ciclo atual como padrão
        data_inicio_sugerida = ciclo_atual_inicio
        data_fim_sugerida = ciclo_atual_fim
    else:
        # Se não houver ciclo, sugere baseado na configuração
        config_global = ConfiguracaoGlobal.query.first()
        duracao = config_global.duracao_mensalidade_dias if config_global else 30
        
        # Sugere início para próxima segunda-feira se hoje não for segunda
        if hoje.weekday() != 0:  # 0 = segunda-feira
            dias_para_segunda = (7 - hoje.weekday()) % 7
            data_inicio_sugerida = hoje + timedelta(days=dias_para_segunda)
        else:
            data_inicio_sugerida = hoje
        
        data_fim_sugerida = data_inicio_sugerida + timedelta(days=duracao - 1)
    
    # Busca mensalistas ativos para seleção
    mensalistas = Jogador.query.filter_by(mensalista=True, ativo=True).order_by(Jogador.nome).all()
    
    return render_template('admin/definir_ciclo.html',
                         data_inicio_sugerida=data_inicio_sugerida,
                         data_fim_sugerida=data_fim_sugerida,
                         mensalistas=mensalistas,
                         ciclo_atual_inicio=ciclo_atual_inicio,
                         ciclo_atual_fim=ciclo_atual_fim)

@app.route('/admin/mensalidade/renovar_vencidos', methods=['POST'])
@admin_required
def renovar_mensalidades_vencidas():
    """Renova automaticamente mensalidades vencidas para novo ciclo"""
    hoje = date.today()
    
    # Busca mensalistas vencidos
    mensalistas_vencidos = Jogador.query.filter(
        Jogador.mensalista == True,
        Jogador.ativo == True,
        Jogador.data_fim_mensalidade < hoje
    ).all()
    
    if not mensalistas_vencidos:
        flash('Não há mensalistas vencidos para renovar!', 'info')
        return redirect(url_for('admin_mensalidades'))
    
    # Calcula novo ciclo
    config_global = ConfiguracaoGlobal.query.first()
    duracao = config_global.duracao_mensalidade_dias if config_global else 30
    
    # Começa de hoje ou do próximo dia útil
    data_inicio = hoje
    if hoje.weekday() >= 5:  # Fim de semana
        dias_para_segunda = (7 - hoje.weekday()) % 7
        data_inicio = hoje + timedelta(days=dias_para_segunda)
    
    data_fim = data_inicio + timedelta(days=duracao - 1)
    
    # Renova cada mensalista vencido
    renovados = 0
    for jogador in mensalistas_vencidos:
        jogador.mensalista = True
        jogador.mensalidade_paga = False  # Marca como não pago para novo ciclo
        jogador.data_inicio_mensalidade = data_inicio
        jogador.data_fim_mensalidade = data_fim
        renovados += 1
    
    db.session.commit()
    
    flash(f'{renovados} mensalistas vencidos renovados para novo ciclo ({format_date_func(data_inicio)} a {format_date_func(data_fim)})!', 'success')
    return redirect(url_for('admin_mensalidades'))

@app.route('/admin/mensalidade/relatorio')
@admin_required
def relatorio_mensalidades():
    """Gera relatório detalhado de mensalidades"""
    hoje = date.today()
    
    # Filtros
    status_filter = request.args.get('status', 'todos')
    mes_filter = request.args.get('mes', '')
    ano_filter = request.args.get('ano', str(hoje.year))
    
    # Query base
    query = Jogador.query.filter_by(ativo=True)
    
    if status_filter == 'pagos':
        query = query.filter_by(mensalista=True, mensalidade_paga=True)
    elif status_filter == 'pendentes':
        query = query.filter_by(mensalista=True, mensalidade_paga=False)
    elif status_filter == 'vencidos':
        query = query.filter(
            Jogador.mensalista == True,
            Jogador.data_fim_mensalidade < hoje
        )
    elif status_filter == 'ativos':
        query = query.filter(
            Jogador.mensalista == True,
            Jogador.mensalidade_paga == True,
            Jogador.data_fim_mensalidade >= hoje
        )
    else:  # 'todos'
        query = query.filter_by(mensalista=True)
    
    jogadores = query.order_by(Jogador.nome).all()
    
    # Estatísticas
    total = len(jogadores)
    pagos = sum(1 for j in jogadores if j.mensalidade_paga)
    vencidos = sum(1 for j in jogadores if j.data_fim_mensalidade and j.data_fim_mensalidade < hoje)
    ativos = sum(1 for j in jogadores if j.mensalidade_paga and j.data_fim_mensalidade and j.data_fim_mensalidade >= hoje)
    
    # Valores totais (exemplo: R$ 50,00 por mensalidade)
    valor_mensalidade = 22.00
    valor_total = total * valor_mensalidade
    valor_recebido = pagos * valor_mensalidade
    valor_pendente = (total - pagos) * valor_mensalidade
    
    return render_template('admin/relatorio_mensalidades.html',
                         jogadores=jogadores,
                         total=total,
                         pagos=pagos,
                         vencidos=vencidos,
                         ativos=ativos,
                         valor_mensalidade=valor_mensalidade,
                         valor_total=valor_total,
                         valor_recebido=valor_recebido,
                         valor_pendente=valor_pendente,
                         status_filter=status_filter,
                         hoje=hoje)

@app.route('/api/mensalidades/status')
@admin_required
def api_mensalidades_status():
    """API para status das mensalidades (usado no dashboard) - SIMPLIFICADA"""
    resumo = obter_resumo_mensalidades()
    
    # Formata as datas para exibição
    ciclo_texto = "Ciclo não definido"
    if resumo['ciclo_atual_inicio'] and resumo['ciclo_atual_fim']:
        inicio = resumo['ciclo_atual_inicio']
        fim = resumo['ciclo_atual_fim']
        ciclo_texto = f"{inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}"
    
    return jsonify({
        'success': True,
        'resumo': {
            'total': resumo['total_mensalistas'],
            'ativas': resumo['mensalistas_pagos'],  # Isso é o que o card deve mostrar
            'pendentes': resumo['mensalistas_pendentes'],
            'vencidas': resumo['mensalistas_vencidos'],
            'ciclo_atual': ciclo_texto
        },
        'atualizado_em': datetime.utcnow().isoformat()
    })



# ======================================================
# ROTAS DO ADMIN (ATUALIZAR)
# ======================================================

@app.route('/admin/ciclos')
@admin_required
def admin_ciclos():
    """Página para gerenciar ciclos de mensalidade"""
    ciclos = CicloMensalidade.query.order_by(CicloMensalidade.created_at.desc()).all()
    ciclo_atual_inicio, ciclo_atual_fim = obter_ciclo_das_configuracoes()
    
    return render_template('admin/ciclos.html',
                         ciclos=ciclos,
                         ciclo_atual_inicio=ciclo_atual_inicio,
                         ciclo_atual_fim=ciclo_atual_fim)

@app.route('/admin/ciclo/novo', methods=['GET', 'POST'])
@admin_required
def novo_ciclo():
    """Criar novo ciclo"""
    if request.method == 'POST':
        data_inicio_str = request.form['data_inicio']
        data_fim_str = request.form['data_fim']
        descricao = request.form.get('descricao', '')
        
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Datas inválidas! Use o formato AAAA-MM-DD.', 'danger')
            return redirect(url_for('novo_ciclo'))
        
        if data_fim <= data_inicio:
            flash('A data de fim deve ser posterior à data de início!', 'danger')
            return redirect(url_for('novo_ciclo'))
        
        # Define o novo ciclo
        ciclo = definir_ciclo_manual(data_inicio, data_fim, descricao)
        
        flash(f'Ciclo definido com sucesso! ({format_date_func(data_inicio)} a {format_date_func(data_fim)})', 'success')
        return redirect(url_for('admin_ciclos'))
    
    # Sugere datas padrão
    hoje = date.today()
    primeiro_dia_mes = hoje.replace(day=1)
    dias_para_segunda = (7 - primeiro_dia_mes.weekday()) % 7
    data_inicio_sugerida = primeiro_dia_mes + timedelta(days=dias_para_segunda)
    
    config_global = ConfiguracaoGlobal.query.first()
    duracao = config_global.duracao_mensalidade_dias if config_global else 30
    data_fim_sugerida = data_inicio_sugerida + timedelta(days=duracao - 1)
    
    return render_template('admin/novo_ciclo.html',
                         data_inicio_sugerida=data_inicio_sugerida,
                         data_fim_sugerida=data_fim_sugerida)

@app.route('/admin/ciclo/<int:id>/ativar')
@admin_required
def ativar_ciclo(id):
    """Ativa um ciclo existente"""
    ciclo = CicloMensalidade.query.get_or_404(id)
    
    # Desativa todos os ciclos
    CicloMensalidade.query.update({'ativo': False})
    
    # Ativa este ciclo
    ciclo.ativo = True
    ciclo.updated_at = datetime.utcnow()
    db.session.commit()
    
    flash(f'Ciclo {format_date_func(ciclo.data_inicio)} a {format_date_func(ciclo.data_fim)} ativado!', 'success')
    return redirect(url_for('admin_ciclos'))

@app.route('/admin/ciclo/<int:id>/excluir')
@admin_required
def excluir_ciclo(id):
    """Exclui um ciclo"""
    ciclo = CicloMensalidade.query.get_or_404(id)
    
    if ciclo.ativo:
        flash('Não é possível excluir o ciclo ativo! Desative-o primeiro.', 'danger')
        return redirect(url_for('admin_ciclos'))
    
    db.session.delete(ciclo)
    db.session.commit()
    
    flash('Ciclo excluído com sucesso!', 'success')
    return redirect(url_for('admin_ciclos'))

@app.route('/admin/mensalidade/definir_periodo', methods=['GET', 'POST'])
@admin_required
def definir_periodo_mensalidade():
    """Define período da mensalidade para todos os mensalistas"""
    if request.method == 'POST':
        data_inicio_str = request.form.get('data_inicio')
        data_fim_str = request.form.get('data_fim')
        
        if not data_inicio_str or not data_fim_str:
            flash('Informe as datas de início e fim!', 'danger')
            return redirect(url_for('definir_periodo_mensalidade'))
        
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Datas inválidas! Use o formato AAAA-MM-DD.', 'danger')
            return redirect(url_for('definir_periodo_mensalidade'))
        
        if data_fim <= data_inicio:
            flash('A data de fim deve ser posterior à data de início!', 'danger')
            return redirect(url_for('definir_periodo_mensalidade'))
        
        # Atualiza todos os mensalistas
        quantos = atualizar_mensalidades_periodo(data_inicio, data_fim)
        
        flash(f'Período definido para {quantos} mensalistas! De {format_date_func(data_inicio)} a {format_date_func(data_fim)}', 'success')
        return redirect(url_for('admin_jogadores'))
    
    return render_template('admin/definir_periodo_mensalidade.html')

  

@app.route('/admin/jogador/<int:id>/remover_nao_mensalista')
@admin_required
def remover_nao_mensalista(id):
    """Remove um jogador não mensalista - CORRIGIDA"""
    jogador = Jogador.query.get_or_404(id)
    
    # Só permite remover se não for mensalista
    if jogador.mensalista:
        flash(f'{jogador.nome} é mensalista! Use "Inativar" em vez de "Remover".', 'warning')
        return redirect(url_for('admin_jogadores'))
    
    # Verifica se tem confirmações
    tem_confirmacoes = Confirmacao.query.filter_by(jogador_id=jogador.id).first()
    if tem_confirmacoes:
        flash(f'{jogador.nome} tem histórico de presenças. Use "Inativar" para manter o histórico.', 'warning')
        return redirect(url_for('admin_jogadores'))
    
    nome_jogador = jogador.nome
    
    try:
        # Remove foto se existir
        if jogador.foto_perfil:
            old_path = os.path.join(app.static_folder, jogador.foto_perfil.lstrip('/'))
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except:
                    pass
        
        # Remove pagamentos do cofre associados a este jogador
        PagamentoCofre.query.filter_by(jogador_id=id).delete()
        
        # Remove usuário associado se existir
        if jogador.user:
            db.session.delete(jogador.user)
        
        # Remove o jogador
        db.session.delete(jogador)
        db.session.commit()
        
        flash(f'Jogador {nome_jogador} removido com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao remover jogador: {str(e)}', 'danger')
        print(f"❌ Erro detalhado ao remover não mensalista {id}: {e}")
    
    return redirect(url_for('admin_jogadores'))

    
@app.route('/admin/configuracoes', methods=['GET', 'POST'])
@admin_required
def admin_configuracoes():
    """Configurações globais do sistema - COMPLETAMENTE ATUALIZADA"""
    config = ConfiguracaoGlobal.query.first()
    if not config:
        config = ConfiguracaoGlobal()
        db.session.add(config)
        db.session.commit()
    
    # Busca o ciclo ativo do sistema
    ciclo_inicio, ciclo_fim, ciclo_existe = obter_ciclo_sistema_ativo()
    
    hoje = date.today()
    
    # Calcula dias restantes (se houver ciclo ativo)
    dias_restantes_ciclo = 0
    duracao_total_ciclo = 0
    
    if ciclo_inicio and ciclo_fim:
        try:
            # IMPORTANTE: Calcula dias RESTANTES do ciclo a partir de HOJE
            if hoje < ciclo_inicio:
                # Ciclo ainda não começou
                dias_restantes_ciclo = (ciclo_fim - ciclo_inicio).days + 1
            elif ciclo_inicio <= hoje <= ciclo_fim:
                # Ciclo em andamento - calcula dias restantes
                dias_restantes_ciclo = max(0, (ciclo_fim - hoje).days + 1)
            else:
                # Ciclo já terminou
                dias_restantes_ciclo = 0
            
            duracao_total_ciclo = (ciclo_fim - ciclo_inicio).days + 1
        except Exception as e:
            print(f"❌ Erro ao calcular dias do ciclo: {e}")
            dias_restantes_ciclo = 0
            duracao_total_ciclo = 0
    
    if request.method == 'POST':
        try:
            print(f"🔧 Salvando configurações - Usuário: {current_user.username}")
            
            # 1. Coleta os dados do formulário
            dias_selecionados = request.form.getlist('dias_semana')
            config.dias_semana_fixos = ','.join(dias_selecionados)
            
            # Duração da mensalidade
            duracao = request.form.get('duracao_mensalidade', type=int)
            if duracao and 7 <= duracao <= 90:
                config.duracao_mensalidade_dias = duracao
            else:
                flash('Duração da mensalidade deve ser entre 7 e 90 dias!', 'warning')
                return redirect(url_for('admin_configuracoes'))
            
            # Senha para visitantes
            senha_visitante = request.form.get('senha_visitante', '').strip()
            if senha_visitante:
                config.senha_visitante = senha_visitante
            
            config.updated_at = datetime.utcnow()
            
            # Valida se há dias selecionados
            if not dias_selecionados:
                flash('Selecione pelo menos um dia da semana para vôlei!', 'danger')
                return redirect(url_for('admin_configuracoes'))
            
            print(f"📅 Dias selecionados: {dias_selecionados}")
            print(f"⏱️ Duração mensalidade: {config.duracao_mensalidade_dias} dias")
            
            # Commit inicial das configurações
            db.session.commit()
            print("✅ Configurações salvas no banco")
            
            # 2. Se há ciclo ativo, remove semanas fora do ciclo primeiro
            semanas_removidas = 0
            if ciclo_existe and ciclo_inicio and ciclo_fim:
                print(f"🔍 Ciclo ativo encontrado: {format_date_func(ciclo_inicio)} a {format_date_func(ciclo_fim)}")
                print(f"📊 Dias restantes no ciclo: {dias_restantes_ciclo}")
                
                try:
                    # Busca semanas criadas após o fim do ciclo
                    semanas_fora = Semana.query.filter(
                        Semana.data > ciclo_fim,
                        Semana.draft_em_andamento == False,  # Não remove drafts em andamento
                        Semana.draft_finalizado == False     # Não remove drafts finalizados
                    ).all()
                    
                    for semana in semanas_fora:
                        print(f"🗑️ Removendo semana fora do ciclo: {format_date_func(semana.data)}")
                        
                        # Remove dados relacionados
                        Confirmacao.query.filter_by(semana_id=semana.id).delete()
                        ListaEspera.query.filter_by(semana_id=semana.id).delete()
                        
                        # Remove a semana
                        db.session.delete(semana)
                        semanas_removidas += 1
                    
                    if semanas_removidas > 0:
                        db.session.commit()
                        print(f"✅ {semanas_removidas} semanas fora do ciclo removidas")
                    
                except Exception as e:
                    db.session.rollback()
                    print(f"⚠️ Erro ao remover semanas fora do ciclo: {e}")
            
            # 3. Cria semanas automaticamente APENAS para os dias restantes
            print("🔄 Criando semanas automaticamente...")
            semanas_criadas = criar_semanas_automaticas()
            
            # 4. Mensagem personalizada baseada no ciclo
            if ciclo_existe and ciclo_inicio and ciclo_fim:
                if semanas_criadas > 0:
                    if semanas_removidas > 0:
                        flash(
                            f'✅ Configurações salvas! {semanas_removidas} semana(s) removida(s) fora do ciclo e {semanas_criadas} semana(s) criada(s) para os {dias_restantes_ciclo} dias restantes do ciclo.', 
                            'success'
                        )
                    else:
                        flash(
                            f'✅ Configurações salvas! {semanas_criadas} semana(s) criada(s) para os {dias_restantes_ciclo} dias restantes do ciclo.', 
                            'success'
                        )
                else:
                    flash(
                        f'✅ Configurações salvas! Todas semanas já existiam para os {dias_restantes_ciclo} dias restantes do ciclo.', 
                        'info'
                    )
            else:
                flash('✅ Configurações salvas! Semanas criadas automaticamente para os próximos 30 dias.', 'success')
            
            # 5. Log detalhado
            print(f"📋 Resumo da operação:")
            print(f"   - Dias configurados: {config.dias_semana_fixos}")
            print(f"   - Ciclo ativo: {ciclo_existe}")
            if ciclo_existe:
                print(f"   - Período do ciclo: {format_date_func(ciclo_inicio)} a {format_date_func(ciclo_fim)}")
                print(f"   - Dias restantes: {dias_restantes_ciclo}")
            print(f"   - Semanas removidas: {semanas_removidas}")
            print(f"   - Semanas criadas: {semanas_criadas}")
            
            return redirect(url_for('admin_configuracoes'))
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ ERRO CRÍTICO ao salvar configurações: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f'❌ Erro ao salvar configurações: {str(e)}', 'danger')
            return redirect(url_for('admin_configuracoes'))
    
    # =========== GET REQUEST ===========
    
    # Busca semanas futuras criadas
    semanas_futuras = Semana.query.filter(Semana.data >= hoje).order_by(Semana.data).limit(20).all()
    
    # Dias selecionados
    dias_selecionados = []
    if config.dias_semana_fixos:
        dias_selecionados = [int(dia) for dia in config.dias_semana_fixos.split(',') if dia.strip().isdigit()]
    
    # Prepara os dias para o template
    dias_semana_nomes = [
        (0, 'Segunda-feira'),
        (1, 'Terça-feira'),
        (2, 'Quarta-feira'),
        (3, 'Quinta-feira'),
        (4, 'Sexta-feira'),
        (5, 'Sábado'),
        (6, 'Domingo')
    ]
    
    # Estatísticas - CORRIGIDAS E MELHORADAS
    total_jogadores = Jogador.query.filter_by(ativo=True).count()
    total_mensalistas = Jogador.query.filter_by(mensalista=True, ativo=True).count()
    total_capitaes = Jogador.query.filter_by(capitao=True, ativo=True).count()
    
    # CORREÇÃO: Conta apenas semanas FUTURAS (não todas as semanas)
    total_semanas_futuras = Semana.query.filter(Semana.data >= hoje).count()
    
    # Conta semanas ativas no ciclo atual (se houver ciclo)
    semanas_no_ciclo = 0
    semanas_fora_ciclo = 0
    
    if ciclo_existe and ciclo_inicio and ciclo_fim:
        # Semanas dentro do ciclo
        semanas_no_ciclo = Semana.query.filter(
            Semana.data >= max(hoje, ciclo_inicio),
            Semana.data <= ciclo_fim
        ).count()
        
        # Semanas após o fim do ciclo (que seriam removidas)
        semanas_fora_ciclo = Semana.query.filter(Semana.data > ciclo_fim).count()
    
    # Calcula quantas semanas seriam criadas baseado na configuração atual
    semanas_potenciais = 0
    if dias_selecionados:
        if ciclo_existe and ciclo_inicio and ciclo_fim:
            # Calcula semanas dentro dos dias restantes do ciclo
            data_inicio = max(hoje, ciclo_inicio)
            if data_inicio <= ciclo_fim:
                dias_totais = (ciclo_fim - data_inicio).days + 1
                for i in range(dias_totais):
                    data = data_inicio + timedelta(days=i)
                    if data.weekday() in dias_selecionados:
                        semanas_potenciais += 1
        else:
            # Sem ciclo: próximos 30 dias
            for i in range(30):
                data = hoje + timedelta(days=i)
                if data.weekday() in dias_selecionados:
                    semanas_potenciais += 1
    
    # Debug info
    print(f"🔍 DEBUG - Estatísticas de semanas:")
    print(f"   - Total semanas futuras: {total_semanas_futuras}")
    print(f"   - Semanas no ciclo: {semanas_no_ciclo}")
    print(f"   - Semanas fora do ciclo: {semanas_fora_ciclo}")
    print(f"   - Semanas potenciais: {semanas_potenciais}")
    print(f"   - Dias selecionados: {dias_selecionados}")
    if ciclo_existe:
        print(f"   - Ciclo: {format_date_func(ciclo_inicio)} a {format_date_func(ciclo_fim)}")
    
    return render_template('admin/configuracoes.html',
                         config=config,
                         semanas_futuras=semanas_futuras,
                         dias_selecionados=dias_selecionados,
                         dias_semana_nomes=dias_semana_nomes,
                         total_jogadores=total_jogadores,
                         total_mensalistas=total_mensalistas,
                         total_capitaes=total_capitaes,
                         total_semanas=total_semanas_futuras,  # Agora mostra apenas semanas futuras
                         semanas_no_ciclo=semanas_no_ciclo,    # Nova estatística
                         semanas_fora_ciclo=semanas_fora_ciclo, # Semanas que seriam removidas
                         semanas_potenciais=semanas_potenciais, # Semanas que poderiam ser criadas
                         ciclo_inicio=ciclo_inicio,
                         ciclo_fim=ciclo_fim,
                         ciclo_existe=ciclo_existe,
                         dias_restantes_ciclo=dias_restantes_ciclo,
                         duracao_total_ciclo=duracao_total_ciclo,
                         hoje=hoje)  # Passa hoje para o template
    
def criar_semanas_automaticas():
    """Cria semanas automaticamente baseado nos dias fixos configurados e ciclo ativo - CORRIGIDA"""
    config_global = ConfiguracaoGlobal.query.first()
    if not config_global:
        print("⚠️ Configuração global não encontrada")
        return 0
    
    hoje = date.today()
    
    # Busca o ciclo ativo do sistema
    ciclo_inicio, ciclo_fim, ciclo_existe = obter_ciclo_sistema_ativo()
    
    # Dias da semana configurados
    dias_semana = []
    if config_global.dias_semana_fixos:
        dias_semana = config_global.get_dias_semana()
    else:
        # Se não houver dias configurados, não cria semanas
        print("⚠️ Nenhum dia da semana configurado. Configure os dias em /admin/configuracoes")
        return 0
    
    if not dias_semana:
        print("⚠️ Nenhum dia da semana selecionado.")
        return 0
    
    # Determina período de criação
    if ciclo_existe and ciclo_inicio and ciclo_fim:
        # IMPORTANTE: Cria semanas apenas para os DIAS RESTANTES do ciclo
        # Começa de HOJE (ou início do ciclo se ainda não começou)
        data_inicio_criacao = max(hoje, ciclo_inicio)
        data_limite = ciclo_fim  # Até o fim do ciclo
        
        # Verifica se o ciclo ainda é válido
        if data_inicio_criacao > ciclo_fim:
            print(f"⚠️ Ciclo já terminou: {format_date_func(ciclo_fim)}")
            return 0
            
        dias_no_periodo = (data_limite - data_inicio_criacao).days + 1
        print(f"✅ Criando semanas para os próximos {dias_no_periodo} dias (até {format_date_func(data_limite)})")
    else:
        # Se não há ciclo ativo, usa os próximos 30 dias (comportamento padrão)
        data_inicio_criacao = hoje
        data_limite = hoje + timedelta(days=30)
        dias_no_periodo = 30
        print(f"✅ Sem ciclo ativo: criando semanas para os próximos 30 dias")
    
    print(f"📅 Período de criação: {format_date_func(data_inicio_criacao)} até {format_date_func(data_limite)}")
    print(f"🎯 Dias de jogo configurados: {', '.join([get_dia_semana_curto(d) for d in dias_semana])}")
    
    semanas_criadas = 0
    data_atual = data_inicio_criacao
    
    # Cria semanas apenas para dias úteis configurados dentro do período
    while data_atual <= data_limite:
        if data_atual.weekday() in dias_semana:
            semana_existente = Semana.query.filter_by(data=data_atual).first()
            if not semana_existente:
                semana = Semana(
                    data=data_atual,
                    descricao=f'Jogo de Vôlei - {data_atual.strftime("%d/%m/%Y")}',
                    lista_aberta=True,
                    max_times=2,
                    max_jogadores_por_time=6
                )
                db.session.add(semana)
                semanas_criadas += 1
                print(f"  ➕ Criada semana para {format_date_func(data_atual)} ({get_dia_semana_curto(data_atual.weekday())})")
            else:
                print(f"  ⏭️ Semana já existe para {format_date_func(data_atual)}")
        
        data_atual += timedelta(days=1)
    
    try:
        db.session.commit()
        if semanas_criadas > 0:
            print(f"✅ {semanas_criadas} semanas criadas automaticamente")
        else:
            print("ℹ️ Nenhuma semana nova criada (todas já existiam)")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao criar semanas: {e}")
    
    return semanas_criadas

@app.route('/admin/iniciar_draft', methods=['POST'])
@admin_required
def iniciar_draft():
    """Inicia o draft - MODIFICADA"""
    semana_id = request.form.get('semana_id', type=int)
    
    if semana_id:
        semana = Semana.query.get(semana_id)
    else:
        semana = get_semana_atual()
    
    if not semana:
        flash('Semana não encontrada!', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    # Obtém configurações do formulário
    modo_draft = request.form.get('modo_draft', 'snake')
    max_times = request.form.get('max_times', type=int, default=2)
    max_jogadores_por_time = request.form.get('max_jogadores_por_time', type=int, default=6)
    tempo_por_escolha = request.form.get('tempo_por_escolha', type=int, default=0)
    
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
    
    try:
        inicializar_draft(semana, tempo_por_escolha, modo_draft, max_times, max_jogadores_por_time)
        flash(f'Draft iniciado para {format_date_func(semana.data)}!', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    
    return redirect(url_for('admin_dashboard', semana_id=semana.id))

@app.route('/admin/verificar_capitaes')
@admin_required
def verificar_capitaes():
    """Verifica e corrige permissões de todos os capitães"""
    capitaes = Jogador.query.filter_by(capitao=True, ativo=True).all()
    
    corrigidos = 0
    problemas = []
    
    for capitao in capitaes:
        print(f"\n🔍 Verificando capitão: {capitao.nome}")
        print(f"   Jogador.capitao: {capitao.capitao}")
        print(f"   Tem usuário: {bool(capitao.user)}")
        
        if capitao.user:
            print(f"   User.role: {capitao.user.role}")
            
            if capitao.user.role != 'capitao':
                capitao.user.role = 'capitao'
                corrigidos += 1
                problemas.append(f"Capitão {capitao.nome}: User tinha role '{capitao.user.role}', corrigido para 'capitao'")
        else:
            # Cria usuário para capitão
            username, password = criar_usuario_para_jogador(capitao, 'capitao')
            corrigidos += 1
            problemas.append(f"Capitão {capitao.nome}: Criado usuário '{username}' com senha '{password}'")
    
    if corrigidos > 0:
        db.session.commit()
        flash(f'{corrigidos} capitães corrigidos!', 'success')
        for problema in problemas:
            flash(problema, 'info')
    else:
        flash('Todos os capitães estão corretos!', 'info')
    
    return redirect(url_for('admin_jogadores'))

# ======================================================
# SOCKET.IO - ATUALIZAÇÕES (ADICIONAR)
# ======================================================

@socketio.on('request_draft_status')
def handle_request_draft_status(data):
    semana_id = data.get('semana_id')
    if not semana_id:
        return
    
    semana = Semana.query.get(semana_id)
    if not semana or not semana.draft_em_andamento:
        return
    
    draft_status = DraftStatus.query.filter_by(semana_id=semana.id).first()
    if not draft_status:
        return
    
    # Busca todos os times
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
            'capitao_id': capitao.id if capitao else None,
            'jogadores': jogadores,
            'total_jogadores': len(jogadores)
        })
    
    # Verifica quem é o próximo capitão
    proximo_capitao = None
    if draft_status.vez_capitao_id:
        capitao_obj = Jogador.query.get(draft_status.vez_capitao_id)
        if capitao_obj:
            proximo_capitao = capitao_obj.nome
    
    # Emite apenas para este cliente
    emit('draft_status_update', {
        'semana_id': semana.id,
        'draft_em_andamento': semana.draft_em_andamento,
        'finalizado': draft_status.finalizado,
        'rodada_atual': draft_status.rodada_atual,
        'escolha_atual': draft_status.escolha_atual,
        'tempo_restante': draft_status.tempo_restante if semana.tempo_escolha > 0 else None,
        'vez_capitao_id': draft_status.vez_capitao_id,
        'capitao_atual': proximo_capitao,
        'times': times_info
    })

@socketio.on('player_selected')
def handle_player_selected(data):
    """Quando um jogador é escolhido, notifica todos"""
    semana_id = data.get('semana_id')
    jogador_id = data.get('jogador_id')
    time_id = data.get('time_id')
    
    if not all([semana_id, jogador_id, time_id]):
        return
    
    # Busca informações
    semana = Semana.query.get(semana_id)
    jogador = Jogador.query.get(jogador_id)
    time = Time.query.get(time_id)
    
    if not all([semana, jogador, time]):
        return
    
    # Emite atualização para todos
    emit('player_selected_update', {
        'semana_id': semana.id,
        'jogador_id': jogador.id,
        'jogador_nome': jogador.nome,
        'time_id': time.id,
        'time_nome': time.nome
    }, room=f'draft_{semana.id}')
    
    # Também emite status completo
    emitir_status_draft_atualizado(semana.id)

@socketio.on('player_selected')
def handle_player_selected(data):
    """Quando um jogador é escolhido, notifica todos"""
    semana_id = data.get('semana_id')
    jogador_id = data.get('jogador_id')
    time_id = data.get('time_id')
    
    if not all([semana_id, jogador_id, time_id]):
        return
    
    # Busca informações
    semana = Semana.query.get(semana_id)
    jogador = Jogador.query.get(jogador_id)
    time = Time.query.get(time_id)
    
    if not all([semana, jogador, time]):
        return
    
    # Emite atualização para todos
    emit('player_selected_update', {
        'semana_id': semana.id,
        'jogador_id': jogador.id,
        'jogador_nome': jogador.nome,
        'time_id': time.id,
        'time_nome': time.nome
    }, room=f'draft_{semana.id}')
    
    # Também emite status completo
    emitir_status_draft_atualizado(semana.id) 

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

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Painel do administrador - MODIFICADA"""
    semana_id = request.args.get('semana_id', type=int)
    
    if semana_id:
        semana = Semana.query.get(semana_id)
        if not semana:
            flash('Semana não encontrada!', 'danger')
            semana = get_semana_atual()
    else:
        semana = get_semana_atual()
    
    # Estatísticas
    total_jogadores = Jogador.query.filter_by(ativo=True).count()
    total_mensalistas = Jogador.query.filter_by(mensalista=True, ativo=True).count()
    total_capitaes = Jogador.query.filter_by(capitao=True, ativo=True).count()
    
    # Confirmações da semana
    confirmacoes = Confirmacao.query.filter_by(semana_id=semana.id).all()
    confirmados = [c for c in confirmacoes if c.confirmado]
    
    # Lista de espera
    lista_espera = ListaEspera.query.filter_by(
        semana_id=semana.id,
        promovido=False
    ).order_by(ListaEspera.adicionado_em).all()
    
    # Mensalistas não confirmados
    mensalistas_ativos = Jogador.query.filter_by(mensalista=True, ativo=True).all()
    mensalistas_nao_confirmados = []
    
    for jogador in mensalistas_ativos:
        confirmacao = Confirmacao.query.filter_by(
            jogador_id=jogador.id,
            semana_id=semana.id
        ).first()
        
        if not confirmacao or not confirmacao.confirmado:
            mensalistas_nao_confirmados.append(jogador)
    
    # Times (se draft em andamento ou finalizado)
    times = []
    if semana.draft_em_andamento or semana.draft_finalizado:
        times = Time.query.filter_by(semana_id=semana.id).order_by(Time.ordem_escolha).all()
    
    # Busca outras semanas disponíveis
    hoje = date.today()
    outras_semanas = Semana.query.filter(
        Semana.data >= hoje,
        Semana.id != semana.id
    ).order_by(Semana.data).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         semana=semana,
                         total_jogadores=total_jogadores,
                         total_mensalistas=total_mensalistas,
                         total_capitaes=total_capitaes,
                         confirmados=len(confirmados),
                         mensalistas_nao_confirmados=mensalistas_nao_confirmados,
                         lista_espera=lista_espera,
                         times=times,
                         outras_semanas=outras_semanas)  # Novo parâmetro
                         

# ======================================================
# NOVAS ROTAS ADMIN
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
    # Busca semanas futuras para o dropdown
    hoje = date.today()
    semanas_futuras = Semana.query.filter(
        Semana.data >= hoje
    ).order_by(Semana.data).limit(20).all()
    
    if request.method == 'POST':
        titulo = request.form['titulo']
        conteudo = request.form['conteudo']
        autor = request.form.get('autor', 'Admin')
        importante = 'importante' in request.form
        
        # Processa semana vinculada
        semana_id = request.form.get('semana_id')
        if semana_id and semana_id != '':
            semana_id_int = int(semana_id)
            para_todas_semanas = False
        else:
            semana_id_int = None
            para_todas_semanas = True
        
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
            data_expiracao=data_expiracao,
            semana_id=semana_id_int,
            para_todas_semanas=para_todas_semanas
        )
        db.session.add(recado)
        db.session.commit()
        
        flash('Recado publicado com sucesso!', 'success')
        return redirect(url_for('admin_recados'))
    
    return render_template('admin/novo_recado.html', semanas_futuras=semanas_futuras)

@app.route('/admin/recado/<int:id>/editar', methods=['GET', 'POST'])
@admin_required
def editar_recado(id):
    """Editar recado existente"""
    recado = Recado.query.get_or_404(id)
    
    # Busca semanas futuras para o dropdown
    hoje = date.today()
    semanas_futuras = Semana.query.filter(
        Semana.data >= hoje
    ).order_by(Semana.data).limit(20).all()
    
    if request.method == 'POST':
        recado.titulo = request.form['titulo']
        recado.conteudo = request.form['conteudo']
        recado.autor = request.form.get('autor', 'Admin')
        recado.importante = 'importante' in request.form
        recado.ativo = 'ativo' in request.form
        
        # Processa semana vinculada
        semana_id = request.form.get('semana_id')
        if semana_id and semana_id != '':
            recado.semana_id = int(semana_id)
            recado.para_todas_semanas = False
        else:
            recado.semana_id = None
            recado.para_todas_semanas = True
        
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
    
    return render_template('admin/editar_recado.html', 
                         recado=recado, 
                         semanas_futuras=semanas_futuras)

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
    # Busca semanas futuras para o dropdown
    hoje = date.today()
    semanas_futuras = Semana.query.filter(
        Semana.data >= hoje
    ).order_by(Semana.data).limit(20).all()
    
    if request.method == 'POST':
        chave_pix = request.form['chave_pix']
        tipo_chave = request.form['tipo_chave']
        nome_recebedor = request.form['nome_recebedor']
        cidade_recebedor = request.form.get('cidade_recebedor', '')
        descricao = request.form.get('descricao', '')
        
        # Processa semana vinculada
        semana_id = request.form.get('semana_id')
        if semana_id and semana_id != '':
            semana_id_int = int(semana_id)
            para_todas_semanas = False
        else:
            semana_id_int = None
            para_todas_semanas = True
        
        pix = PixInfo(
            chave_pix=chave_pix,
            tipo_chave=tipo_chave,
            nome_recebedor=nome_recebedor,
            cidade_recebedor=cidade_recebedor,
            descricao=descricao,
            semana_id=semana_id_int,
            para_todas_semanas=para_todas_semanas
        )
        db.session.add(pix)
        db.session.commit()
        
        flash('Chave PIX adicionada com sucesso!', 'success')
        return redirect(url_for('admin_pix'))
    
    return render_template('admin/novo_pix.html', semanas_futuras=semanas_futuras)

@app.route('/admin/pix/<int:id>/editar', methods=['GET', 'POST'])
@admin_required
def editar_pix(id):
    """Editar chave PIX"""
    pix = PixInfo.query.get_or_404(id)
    
    # Busca semanas futuras para o dropdown
    hoje = date.today()
    semanas_futuras = Semana.query.filter(
        Semana.data >= hoje
    ).order_by(Semana.data).limit(20).all()
    
    if request.method == 'POST':
        pix.chave_pix = request.form['chave_pix']
        pix.tipo_chave = request.form['tipo_chave']
        pix.nome_recebedor = request.form['nome_recebedor']
        pix.cidade_recebedor = request.form.get('cidade_recebedor', '')
        pix.descricao = request.form.get('descricao', '')
        pix.ativo = 'ativo' in request.form
        
        # Processa semana vinculada
        semana_id = request.form.get('semana_id')
        if semana_id and semana_id != '':
            pix.semana_id = int(semana_id)
            pix.para_todas_semanas = False
        else:
            pix.semana_id = None
            pix.para_todas_semanas = True
        
        db.session.commit()
        flash('Chave PIX atualizada com sucesso!', 'success')
        return redirect(url_for('admin_pix'))
    
    return render_template('admin/editar_pix.html', 
                         pix=pix, 
                         semanas_futuras=semanas_futuras)

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
    """Configurar parâmetros específicos da semana - MODIFICADA PARA SEM TEMPO"""
    semana = Semana.query.get_or_404(id)
    
    # Busca confirmações da semana
    confirmados = Confirmacao.query.filter_by(
        semana_id=semana.id,
        confirmado=True
    ).count()
    
    if request.method == 'POST':
        semana.max_times = request.form.get('max_times', type=int, default=2)
        semana.max_jogadores_por_time = request.form.get('max_jogadores_por_time', type=int, default=6)
        # SEMPRE define tempo como 0
        semana.tempo_escolha = 0
        semana.modo_draft = request.form.get('modo_draft', 'snake')
        
        db.session.commit()
        flash('Configurações da semana atualizadas com sucesso!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/configurar_semana.html', semana=semana, confirmados=confirmados)

# ======================================================
# ROTAS PÚBLICAS (com username em minúsculo)
# ======================================================

@app.route('/copiar_pix/<int:id>')
def copiar_pix(id):
    """API para copiar chave PIX"""
    pix = PixInfo.query.get_or_404(id)
    return jsonify({'success': True, 'chave': pix.chave_pix})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username'].lower()
        password = request.form['password']
        remember = 'remember' in request.form  # Novo campo "remember me"
        
        # Busca por username (case insensitive)
        user = User.query.filter(func.lower(User.username) == username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user, remember=remember)  # Adiciona remember
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

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    logout_user()
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username'].lower().strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        email = request.form.get('email', '').strip()
        nome_completo = request.form.get('nome_completo', '').strip()
        telefone = request.form.get('telefone', '').strip()
        posicao = request.form.get('posicao', '')
        nivel = request.form.get('nivel', 'intermediario')
        
        # VALIDAÇÕES MELHORADAS
        # 1. Verificar se username contém espaços
        if ' ' in username:
            flash('Nome de usuário não pode conter espaços! Use um único nome (ex: joao, joao.silva, joao_silva).', 'danger')
            return redirect(url_for('register'))
        
        # 2. Verificar se username é válido (apenas letras, números, pontos e underlines)
        import re
        if not re.match(r'^[a-z0-9._]+$', username):
            flash('Nome de usuário inválido! Use apenas letras minúsculas, números, pontos (.) ou underlines (_).', 'danger')
            return redirect(url_for('register'))
        
        # 3. Verificar tamanho mínimo e máximo
        if len(username) < 3:
            flash('Nome de usuário deve ter pelo menos 3 caracteres.', 'danger')
            return redirect(url_for('register'))
        
        if len(username) > 30:
            flash('Nome de usuário deve ter no máximo 30 caracteres.', 'danger')
            return redirect(url_for('register'))
        
        # Validações básicas originais (mantidas)
        if password != confirm_password:
            flash('As senhas não coincidem!', 'danger')
            return redirect(url_for('register'))
        
        # Verifica se username já existe (case insensitive)
        if User.query.filter(func.lower(User.username) == username).first():
            flash('Nome de usuário já está em uso!', 'danger')
            return redirect(url_for('register'))
        
        if email and User.query.filter_by(email=email).first():
            flash('E-mail já está em uso!', 'danger')
            return redirect(url_for('register'))
        
        # Cria novo usuário
        try:
            user = User(
                username=username.lower(),
                password=generate_password_hash(password),
                email=email if email else None,
                role='jogador'
            )
            db.session.add(user)
            db.session.commit()
            
            # Se forneceu nome completo, cria jogador também
            jogador = None
            if nome_completo:
                jogador = Jogador(
                    nome=nome_completo,
                    telefone=telefone,
                    posicao=posicao,
                    nivel=nivel,
                    ativo=True
                )
                db.session.add(jogador)
                db.session.commit()
                
                # Vincula jogador ao usuário
                user.jogador_id = jogador.id
                db.session.commit()
            
            # Armazena user_id na sessão para login automático depois
            session['new_user_id'] = user.id
            
            # Redireciona para completar perfil
            flash('Conta criada com sucesso! Complete seu perfil.', 'success')
            return redirect(url_for('completar_perfil'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar conta: {str(e)}', 'danger')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/admin/usuarios')
@admin_required
def admin_usuarios():
    """Lista todos os usuários do sistema"""
    # Busca todos os usuários com informações do jogador
    usuarios = db.session.query(
        User,
        Jogador
    ).outerjoin(
        Jogador, User.jogador_id == Jogador.id
    ).order_by(
        User.username
    ).all()
    
    # Busca jogadores sem usuário (para criação)
    jogadores_sem_usuario = Jogador.query.filter(
        Jogador.ativo == True,
        ~Jogador.id.in_(
            db.session.query(User.jogador_id).filter(User.jogador_id.isnot(None))
        )
    ).order_by(Jogador.nome).all()
    
    return render_template('admin/usuarios.html',
                         usuarios=usuarios,
                         jogadores_sem_usuario=jogadores_sem_usuario)

@app.route('/admin/usuario/<int:id>/editar', methods=['GET', 'POST'])
@admin_required
def admin_editar_usuario_detalhes(id):
    """Editar detalhes de um usuário específico"""
    user = User.query.get_or_404(id)
    jogador = user.jogador if user.jogador_id else None
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        email = request.form.get('email', '').strip()
        role = request.form.get('role', 'jogador')
        reset_password = 'reset_password' in request.form
        nova_senha = request.form.get('nova_senha', '').strip()
        vincular_jogador_id = request.form.get('vincular_jogador_id', type=int)
        
        # Validações
        if not username:
            flash('O nome de usuário é obrigatório!', 'danger')
            return redirect(url_for('admin_editar_usuario_detalhes', id=id))
        
        if ' ' in username:
            flash('Nome de usuário não pode conter espaços!', 'danger')
            return redirect(url_for('admin_editar_usuario_detalhes', id=id))
        
        import re
        if not re.match(r'^[a-z0-9._]+$', username):
            flash('Nome de usuário inválido! Use apenas letras minúsculas, números, pontos (.) ou underlines (_).', 'danger')
            return redirect(url_for('admin_editar_usuario_detalhes', id=id))
        
        # Verificar se username já existe (exceto para o próprio usuário)
        outro_usuario = User.query.filter(
            User.username == username,
            User.id != user.id
        ).first()
        
        if outro_usuario:
            flash('Este nome de usuário já está em uso por outro jogador!', 'danger')
            return redirect(url_for('admin_editar_usuario_detalhes', id=id))
        
        # Atualizar dados básicos
        user.username = username
        user.email = email if email else None
        user.role = role
        
        # Vincular/desvincular jogador
        if vincular_jogador_id:
            # Desvincular jogador atual se existir
            if user.jogador_id and user.jogador_id != vincular_jogador_id:
                jogador_atual = Jogador.query.get(user.jogador_id)
                if jogador_atual:
                    # Se o jogador atual era capitão, verificar se precisa ajustar
                    if jogador_atual.capitao and jogador_atual.capitao != (role == 'capitao'):
                        # Ajustar sincronização
                        sincronizar_capitao_permissao(jogador_atual.id)
            
            # Vincular novo jogador
            novo_jogador = Jogador.query.get(vincular_jogador_id)
            if novo_jogador:
                user.jogador_id = novo_jogador.id
                # Sincronizar capitão se necessário
                if role == 'capitao' and not novo_jogador.capitao:
                    novo_jogador.capitao = True
                elif role != 'capitao' and novo_jogador.capitao:
                    novo_jogador.capitao = False
        elif request.form.get('desvincular_jogador') == 'true':
            # Desvincular jogador atual
            if user.jogador_id:
                jogador_atual = Jogador.query.get(user.jogador_id)
                if jogador_atual and jogador_atual.capitao:
                    # Se desvinculando de um capitão, ajustar permissões
                    jogador_atual.capitao = False
                    sincronizar_capitao_permissao(jogador_atual.id)
            
            user.jogador_id = None
        
        # Resetar senha se solicitado
        senha_gerada = None
        if reset_password:
            if nova_senha:
                if len(nova_senha) < 6:
                    flash('A senha deve ter pelo menos 6 caracteres!', 'danger')
                    return redirect(url_for('admin_editar_usuario_detalhes', id=id))
                user.password = generate_password_hash(nova_senha)
                senha_gerada = nova_senha
            else:
                senha_aleatoria = secrets.token_hex(6)
                user.password = generate_password_hash(senha_aleatoria)
                senha_gerada = senha_aleatoria
        
        # Atualizar data de modificação
        user.last_login = datetime.utcnow()
        
        try:
            db.session.commit()
            
            mensagem = f'Usuário "{username}" atualizado com sucesso!'
            if senha_gerada:
                mensagem += f' Nova senha: <strong>{senha_gerada}</strong>'
            
            flash(mensagem, 'success')
            return redirect(url_for('admin_usuarios'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar usuário: {str(e)}', 'danger')
    
    # Buscar todos os jogadores para vincular
    jogadores_disponiveis = Jogador.query.filter_by(ativo=True).order_by(Jogador.nome).all()
    
    return render_template('admin/editar_usuario_detalhes.html',
                         user=user,
                         jogador=jogador,
                         jogadores_disponiveis=jogadores_disponiveis)

@app.route('/admin/usuario/novo', methods=['GET', 'POST'])
@admin_required
def admin_novo_usuario():
    """Criar novo usuário manualmente"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        email = request.form.get('email', '').strip()
        role = request.form.get('role', 'jogador')
        senha = request.form.get('senha', '').strip()
        vincular_jogador_id = request.form.get('vincular_jogador_id', type=int)
        
        # Validações
        if not username:
            flash('O nome de usuário é obrigatório!', 'danger')
            return redirect(url_for('admin_novo_usuario'))
        
        if ' ' in username:
            flash('Nome de usuário não pode conter espaços!', 'danger')
            return redirect(url_for('admin_novo_usuario'))
        
        import re
        if not re.match(r'^[a-z0-9._]+$', username):
            flash('Nome de usuário inválido! Use apenas letras minúsculas, números, pontos (.) ou underlines (_).', 'danger')
            return redirect(url_for('admin_novo_usuario'))
        
        if User.query.filter_by(username=username).first():
            flash('Este nome de usuário já está em uso!', 'danger')
            return redirect(url_for('admin_novo_usuario'))
        
        if email and User.query.filter_by(email=email).first():
            flash('Este e-mail já está em uso!', 'danger')
            return redirect(url_for('admin_novo_usuario'))
        
        if not senha or len(senha) < 6:
            flash('A senha deve ter pelo menos 6 caracteres!', 'danger')
            return redirect(url_for('admin_novo_usuario'))
        
        # Criar usuário
        user = User(
            username=username,
            password=generate_password_hash(senha),
            email=email if email else None,
            role=role,
            jogador_id=vincular_jogador_id if vincular_jogador_id else None
        )
        
        # Sincronizar capitão se necessário
        if role == 'capitao' and vincular_jogador_id:
            jogador = Jogador.query.get(vincular_jogador_id)
            if jogador:
                jogador.capitao = True
        
        try:
            db.session.add(user)
            db.session.commit()
            
            flash(f'Usuário "{username}" criado com sucesso! Senha: <strong>{senha}</strong>', 'success')
            return redirect(url_for('admin_usuarios'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar usuário: {str(e)}', 'danger')
    
    # Buscar jogadores sem usuário
    jogadores_sem_usuario = Jogador.query.filter(
        Jogador.ativo == True,
        ~Jogador.id.in_(
            db.session.query(User.jogador_id).filter(User.jogador_id.isnot(None))
        )
    ).order_by(Jogador.nome).all()
    
    return render_template('admin/novo_usuario.html',
                         jogadores_sem_usuario=jogadores_sem_usuario)

@app.route('/admin/usuario/<int:id>/excluir')
@admin_required
def admin_excluir_usuario(id):
    """Excluir um usuário"""
    user = User.query.get_or_404(id)
    username = user.username
    
    try:
        # Verificar se é o último admin
        if user.role == 'admin':
            total_admins = User.query.filter_by(role='admin').count()
            if total_admins <= 1:
                flash('Não é possível excluir o único administrador do sistema!', 'danger')
                return redirect(url_for('admin_usuarios'))
        
        # Desvincular jogador se existir
        if user.jogador_id:
            jogador = Jogador.query.get(user.jogador_id)
            if jogador and jogador.capitao:
                jogador.capitao = False
        
        # Excluir usuário
        db.session.delete(user)
        db.session.commit()
        
        flash(f'Usuário "{username}" excluído com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir usuário: {str(e)}', 'danger')
    
    return redirect(url_for('admin_usuarios'))

# ======================================================
# ROTAS DO COFRINHO
# ======================================================

@app.route('/admin/cofre')
@admin_required
def cofre_principal():
    """Página principal do cofrinho - ATUALIZADA"""
    semana_id = request.args.get('semana_id', type=int)
    
    if semana_id:
        semana = Semana.query.get(semana_id)
    else:
        semana = get_semana_atual()
    
    if not semana:
        flash('Semana não encontrada!', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    # Buscar próximas semanas (para o seletor)
    hoje = date.today()
    semanas = Semana.query.filter(
        Semana.data >= hoje - timedelta(days=30)
    ).order_by(Semana.data).limit(10).all()
    
    semanas_com_info = []
    for s in semanas:
        total_pagamentos = PagamentoCofre.query.filter_by(semana_id=s.id, pago=True).count()
        semanas_com_info.append({
            'semana': s,
            'total_pagamentos': total_pagamentos
        })
    
    # IMPORTANTE: Buscar apenas jogadores não-mensalistas que ESTÃO EM TIMES formados
    # Primeiro, buscar todas as escolhas do draft desta semana
    escolhas_draft = EscolhaDraft.query.filter_by(semana_id=semana.id).all()
    
    jogadores_cofre = []
    jogadores_em_times = set()  # Para evitar duplicatas
    
    for escolha in escolhas_draft:
        jogador = Jogador.query.get(escolha.jogador_id)
        
        # Verificar se o jogador existe, está ativo e NÃO é mensalista
        if jogador and jogador.ativo and not jogador.mensalista:
            # Evitar duplicatas
            if jogador.id in jogadores_em_times:
                continue
                
            jogadores_em_times.add(jogador.id)
            
            # Buscar time do jogador
            time = Time.query.get(escolha.time_id)
            time_nome = time.nome if time else "Sem time"
            time_id = time.id if time else None
            
            # Buscar ou criar pagamento
            pagamento = PagamentoCofre.query.filter_by(
                semana_id=semana.id,
                jogador_id=jogador.id
            ).first()
            
            if not pagamento:
                pagamento = PagamentoCofre(
                    semana_id=semana.id,
                    jogador_id=jogador.id,
                    valor=VALOR_PADRAO_JOGO,
                    pago=False,
                    metodo_pagamento='dinheiro'
                )
                db.session.add(pagamento)
                db.session.commit()
            
            jogadores_cofre.append({
                'jogador': jogador,
                'time_nome': time_nome,
                'time_id': time_id,
                'pagamento': pagamento
            })
    
    # Adicionar também jogadores confirmados que NÃO estão em times (para draft não finalizado)
    if not semana.draft_finalizado:
        confirmacoes = Confirmacao.query.filter_by(
            semana_id=semana.id,
            confirmado=True
        ).all()
        
        for conf in confirmacoes:
            jogador = conf.jogador
            
            # Verificar se já está na lista (em time)
            if jogador.id in jogadores_em_times:
                continue
                
            # Incluir apenas jogadores não-mensalistas
            if not jogador.mensalista:
                jogadores_em_times.add(jogador.id)
                
                # Buscar ou criar pagamento
                pagamento = PagamentoCofre.query.filter_by(
                    semana_id=semana.id,
                    jogador_id=jogador.id
                ).first()
                
                if not pagamento:
                    pagamento = PagamentoCofre(
                        semana_id=semana.id,
                        jogador_id=jogador.id,
                        valor=VALOR_PADRAO_JOGO,
                        pago=False,
                        metodo_pagamento='dinheiro'
                    )
                    db.session.add(pagamento)
                    db.session.commit()
                
                jogadores_cofre.append({
                    'jogador': jogador,
                    'time_nome': "Aguardando time",
                    'time_id': None,
                    'pagamento': pagamento
                })
    
    # Buscar times formados (para filtro)
    times = Time.query.filter_by(semana_id=semana.id).order_by(Time.nome).all()
    
    # Calcular saldo total do cofre
    entradas = db.session.query(func.sum(MovimentoCofre.valor)).filter(
        MovimentoCofre.tipo.in_(['entrada', 'deposito', 'ajuste'])
    ).scalar() or 0
    
    saidas = db.session.query(func.sum(MovimentoCofre.valor)).filter(
        MovimentoCofre.tipo.in_(['saida', 'retirada'])
    ).scalar() or 0
    
    saldo_total = entradas - saidas
    
    # Estatísticas da semana
    pagamentos_semana = PagamentoCofre.query.filter_by(semana_id=semana.id).all()
    
    semana_info = {
        'total': len(pagamentos_semana),
        'pagos': sum(1 for p in pagamentos_semana if p.pago),
        'pendentes': sum(1 for p in pagamentos_semana if not p.pago),
        'arrecadado': sum(p.valor for p in pagamentos_semana if p.pago)
    }
    
    # Resumo por método de pagamento
    resumo_metodos = {
        'dinheiro': sum(p.valor for p in pagamentos_semana if p.pago and p.metodo_pagamento == 'dinheiro'),
        'pix': sum(p.valor for p in pagamentos_semana if p.pago and p.metodo_pagamento == 'pix'),
        'cartao': sum(p.valor for p in pagamentos_semana if p.pago and p.metodo_pagamento == 'cartao'),
        'outro': sum(p.valor for p in pagamentos_semana if p.pago and p.metodo_pagamento == 'outro')
    }
    
    # Movimentos recentes
    movimentos = MovimentoCofre.query.order_by(MovimentoCofre.created_at.desc()).limit(20).all()
    
    # Metas ativas
    metas = MetaCofre.query.filter_by(status='ativo').order_by(MetaCofre.prioridade.desc()).all()
    meta_ativa = metas[0] if metas else None
    
    # Estatísticas das metas
    metas_ativas = MetaCofre.query.filter_by(status='ativo').count()
    metas_concluidas = MetaCofre.query.filter_by(status='concluido').count()
    total_metas = sum(m.valor_meta for m in MetaCofre.query.all())
    
    # Relatórios das últimas semanas
    ultimas_semanas = Semana.query.filter(
        Semana.data >= hoje - timedelta(days=90)
    ).order_by(Semana.data.desc()).limit(12).all()
    
    relatorios_semanas = []
    for s in ultimas_semanas:
        pagamentos = PagamentoCofre.query.filter_by(semana_id=s.id).all()
        total = len(pagamentos)
        pagos = sum(1 for p in pagamentos if p.pago)
        arrecadado = sum(p.valor for p in pagamentos if p.pago)
        
        relatorios_semanas.append({
            'semana': s,
            'total_jogadores': total,
            'total': total,
            'pagos': pagos,
            'arrecadado': arrecadado
        })
    
    return render_template('admin/cofre.html',
                         semana=semana,
                         semanas=semanas_com_info,
                         jogadores_cofre=jogadores_cofre,
                         times=times,
                         saldo_total=saldo_total,
                         semana_info=semana_info,
                         resumo_metodos=resumo_metodos,
                         movimentos=movimentos,
                         metas=metas,
                         meta_ativa=meta_ativa,
                         metas_ativas=metas_ativas,
                         metas_concluidas=metas_concluidas,
                         total_metas=total_metas,
                         relatorios_semanas=relatorios_semanas,
                         valor_padrao=VALOR_PADRAO_JOGO)
    
@app.route('/admin/cofre/relatorio/mes/<int:ano>/<int:mes>/exportar')
@admin_required
def exportar_relatorio_mensal(ano, mes):
    """Exporta relatório mensal em CSV"""
    # Buscar semanas do mês
    semanas = Semana.query.filter(
        db.extract('year', Semana.data) == ano,
        db.extract('month', Semana.data) == mes
    ).all()
    
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Cabeçalho
    writer.writerow(['Relatório Mensal', f'{mes:02d}/{ano}'])
    writer.writerow(['Data de geração:', datetime.now().strftime("%d/%m/%Y %H:%M")])
    writer.writerow([])
    writer.writerow(['Semana', 'Jogadores', 'Arrecadado (R$)', 'Pagamentos', 'Taxa'])
    
    total_jogadores = 0
    total_arrecadado = 0
    total_pagamentos = 0
    
    # Dados por semana
    for semana in semanas:
        pagamentos = PagamentoCofre.query.filter_by(semana_id=semana.id).all()
        total = len(pagamentos)
        pagos = sum(1 for p in pagamentos if p.pago)
        arrecadado = sum(p.valor for p in pagamentos if p.pago)
        taxa = (pagos / total * 100) if total > 0 else 0
        
        writer.writerow([
            semana.data.strftime("%d/%m/%Y"),
            total,
            f'{arrecadado:.2f}',
            f'{pagos}/{total}',
            f'{taxa:.1f}%'
        ])
        
        total_jogadores += total
        total_arrecadado += arrecadado
        total_pagamentos += pagos
    
    writer.writerow([])
    writer.writerow(['TOTAL', total_jogadores, f'{total_arrecadado:.2f}', 
                     f'{total_pagamentos}/{total_jogadores}', 
                     f'{(total_pagamentos / total_jogadores * 100) if total_jogadores > 0 else 0:.1f}%'])
    
    output.seek(0)
    
    from flask import make_response
    
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=relatorio_mes_{mes:02d}_{ano}.csv"
    response.headers["Content-type"] = "text/csv"
    
    return response    

@app.route('/api/cofre/pagar', methods=['POST'])
@admin_required
def api_cofre_pagar():
    """API para registrar pagamento"""
    data = request.get_json()
    
    jogador_id = data.get('jogador_id')
    semana_id = data.get('semana_id')
    valor = data.get('valor', VALOR_PADRAO_JOGO)
    metodo_pagamento = data.get('metodo_pagamento', 'dinheiro')
    
    if not jogador_id or not semana_id:
        return jsonify({'success': False, 'message': 'Dados incompletos!'})
    
    try:
        # Buscar ou criar pagamento
        pagamento = PagamentoCofre.query.filter_by(
            semana_id=semana_id,
            jogador_id=jogador_id
        ).first()
        
        if not pagamento:
            pagamento = PagamentoCofre(
                semana_id=semana_id,
                jogador_id=jogador_id,
                valor=valor,
                metodo_pagamento=metodo_pagamento,
                registrado_por=current_user.username
            )
            db.session.add(pagamento)
        
        pagamento.pago = True
        pagamento.pago_em = datetime.utcnow()
        pagamento.valor = valor
        pagamento.metodo_pagamento = metodo_pagamento
        pagamento.updated_at = datetime.utcnow()
        
        # Registrar movimento de entrada
        movimento = MovimentoCofre(
            tipo='entrada',
            valor=valor,
            descricao=f'Pagamento de {pagamento.jogador.nome}',
            semana_id=semana_id,
            observacao=f'Método: {metodo_pagamento}',
            usuario=current_user.username
        )
        db.session.add(movimento)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Pagamento registrado com sucesso!'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'})

@app.route('/api/cofre/desmarcar', methods=['POST'])
@admin_required
def api_cofre_desmarcar():
    """API para desmarcar pagamento"""
    data = request.get_json()
    
    jogador_id = data.get('jogador_id')
    semana_id = data.get('semana_id')
    
    if not jogador_id or not semana_id:
        return jsonify({'success': False, 'message': 'Dados incompletos!'})
    
    try:
        pagamento = PagamentoCofre.query.filter_by(
            semana_id=semana_id,
            jogador_id=jogador_id
        ).first()
        
        if pagamento and pagamento.pago:
            pagamento.pago = False
            pagamento.pago_em = None
            pagamento.updated_at = datetime.utcnow()
            
            # Registrar movimento de ajuste (saída)
            movimento = MovimentoCofre(
                tipo='ajuste',
                valor=-pagamento.valor,
                descricao=f'Ajuste: Cancelamento de pagamento de {pagamento.jogador.nome}',
                semana_id=semana_id,
                observacao='Pagamento cancelado',
                usuario=current_user.username
            )
            db.session.add(movimento)
            
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Pagamento desmarcado!'})
        else:
            return jsonify({'success': False, 'message': 'Pagamento não encontrado ou já está pendente!'})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'})

@app.route('/api/cofre/pagar_todos', methods=['POST'])
@admin_required
def api_cofre_pagar_todos():
    """API para marcar todos como pagos"""
    data = request.get_json()
    
    semana_id = data.get('semana_id')
    valor_padrao = data.get('valor_padrao', VALOR_PADRAO_JOGO)
    
    if not semana_id:
        return jsonify({'success': False, 'message': 'Semana não especificada!'})
    
    try:
        # Buscar todos os jogadores não-mensalistas confirmados
        confirmacoes = Confirmacao.query.filter_by(
            semana_id=semana_id,
            confirmado=True
        ).all()
        
        jogadores_processados = 0
        valor_total = 0
        
        for conf in confirmacoes:
            jogador = conf.jogador
            
            # Processar apenas não-mensalistas
            if not jogador.mensalista:
                # Buscar ou criar pagamento
                pagamento = PagamentoCofre.query.filter_by(
                    semana_id=semana_id,
                    jogador_id=jogador.id
                ).first()
                
                if not pagamento:
                    pagamento = PagamentoCofre(
                        semana_id=semana_id,
                        jogador_id=jogador.id,
                        valor=valor_padrao,
                        metodo_pagamento='dinheiro',
                        registrado_por=current_user.username
                    )
                    db.session.add(pagamento)
                
                if not pagamento.pago:
                    pagamento.pago = True
                    pagamento.pago_em = datetime.utcnow()
                    pagamento.valor = valor_padrao
                    pagamento.updated_at = datetime.utcnow()
                    
                    # Registrar movimento
                    movimento = MovimentoCofre(
                        tipo='entrada',
                        valor=valor_padrao,
                        descricao=f'Pagamento em lote: {jogador.nome}',
                        semana_id=semana_id,
                        observacao='Processamento em lote',
                        usuario=current_user.username
                    )
                    db.session.add(movimento)
                    
                    jogadores_processados += 1
                    valor_total += valor_padrao
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'{jogadores_processados} jogadores marcados como pagos!',
            'total': valor_total
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'})

@app.route('/api/cofre/salvar_observacao', methods=['POST'])
@admin_required
def api_cofre_salvar_observacao():
    """API para salvar observação de pagamento"""
    data = request.get_json()
    
    jogador_id = data.get('jogador_id')
    semana_id = data.get('semana_id')
    observacao = data.get('observacao', '')
    
    if not jogador_id or not semana_id:
        return jsonify({'success': False, 'message': 'Dados incompletos!'})
    
    try:
        pagamento = PagamentoCofre.query.filter_by(
            semana_id=semana_id,
            jogador_id=jogador_id
        ).first()
        
        if pagamento:
            pagamento.observacao = observacao
            pagamento.updated_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Observação salva!'})
        else:
            return jsonify({'success': False, 'message': 'Pagamento não encontrado!'})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'})

@app.route('/api/cofre/deposito', methods=['POST'])
@admin_required
def api_cofre_deposito():
    """API para adicionar dinheiro ao cofre"""
    data = request.get_json()
    
    valor = data.get('valor', 0)
    descricao = data.get('descricao', 'Depósito manual')
    observacao = data.get('observacao', '')
    adicionar_meta = data.get('adicionar_meta', False)
    
    if valor <= 0:
        return jsonify({'success': False, 'message': 'Valor inválido!'})
    
    try:
        # Registrar movimento
        movimento = MovimentoCofre(
            tipo='deposito',
            valor=valor,
            descricao=descricao,
            observacao=observacao,
            usuario=current_user.username
        )
        db.session.add(movimento)
        
        # Se solicitado, adicionar à meta ativa
        if adicionar_meta:
            meta_ativa = MetaCofre.query.filter_by(status='ativo').first()
            if meta_ativa:
                meta_ativa.valor_atual += valor
                meta_ativa.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Depósito de R$ {valor:.2f} realizado com sucesso!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'})

@app.route('/api/cofre/saque', methods=['POST'])
@admin_required
def api_cofre_saque():
    """API para retirar dinheiro do cofre"""
    data = request.get_json()
    
    valor = data.get('valor', 0)
    motivo = data.get('motivo', '')
    descricao = data.get('descricao', '')
    comprovante = data.get('comprovante', '')
    
    if valor <= 0:
        return jsonify({'success': False, 'message': 'Valor inválido!'})
    
    # Verificar saldo
    entradas = db.session.query(func.sum(MovimentoCofre.valor)).filter(
        MovimentoCofre.tipo.in_(['entrada', 'deposito', 'ajuste'])
    ).scalar() or 0
    
    saidas = db.session.query(func.sum(MovimentoCofre.valor)).filter(
        MovimentoCofre.tipo.in_(['saida', 'retirada'])
    ).scalar() or 0
    
    saldo_disponivel = entradas - saidas
    
    if valor > saldo_disponivel:
        return jsonify({
            'success': False, 
            'message': f'Saldo insuficiente! Disponível: R$ {saldo_disponivel:.2f}'
        })
    
    try:
        # Registrar movimento
        movimento = MovimentoCofre(
            tipo='retirada',
            valor=valor,
            descricao=f'Retirada: {motivo}',
            observacao=f'{descricao}\nComprovante: {comprovante}' if comprovante else descricao,
            usuario=current_user.username
        )
        db.session.add(movimento)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Retirada de R$ {valor:.2f} realizada com sucesso!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'})

@app.route('/api/cofre/meta', methods=['POST'])
@admin_required
def api_cofre_criar_meta():
    """API para criar nova meta"""
    data = request.get_json()
    
    titulo = data.get('titulo', '')
    descricao = data.get('descricao', '')
    valor_meta = data.get('valor_meta', 0)
    data_limite = data.get('data_limite')
    prioridade = data.get('prioridade', 2)
    valor_inicial = data.get('valor_inicial', 0)
    
    if not titulo or valor_meta <= 0:
        return jsonify({'success': False, 'message': 'Dados inválidos!'})
    
    try:
        meta = MetaCofre(
            titulo=titulo,
            descricao=descricao,
            valor_meta=valor_meta,
            valor_atual=valor_inicial,
            data_limite=datetime.strptime(data_limite, '%Y-%m-%d').date() if data_limite else None,
            prioridade=prioridade,
            status='ativo'
        )
        db.session.add(meta)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Meta "{titulo}" criada com sucesso!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'})

@app.route('/api/cofre/jogador_manual', methods=['POST'])
@admin_required
def api_cofre_adicionar_jogador_manual():
    """API para adicionar jogador manualmente"""
    data = request.get_json()
    
    nome = data.get('nome', '')
    valor = data.get('valor', VALOR_PADRAO_JOGO)
    metodo_pagamento = data.get('metodo_pagamento', 'dinheiro')
    pago = data.get('pago', False)
    observacao = data.get('observacao', '')
    semana_id = data.get('semana_id')
    
    if not nome or not semana_id:
        return jsonify({'success': False, 'message': 'Dados incompletos!'})
    
    try:
        semana = Semana.query.get(semana_id)
        if not semana:
            return jsonify({'success': False, 'message': 'Semana não encontrada!'})
        
        # Criar jogador temporário (não salva no banco principal)
        # Aqui você pode decidir criar um registro temporário ou usar um sistema diferente
        # Por enquanto, vamos apenas registrar o pagamento
        
        movimento_descricao = f'Pagamento manual: {nome}'
        if pago:
            # Registrar como movimento de entrada
            movimento = MovimentoCofre(
                tipo='entrada',
                valor=valor,
                descricao=movimento_descricao,
                semana_id=semana_id,
                observacao=f'Jogador manual: {observacao}\nMétodo: {metodo_pagamento}',
                usuario=current_user.username
            )
            db.session.add(movimento)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Jogador "{nome}" adicionado com sucesso!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'})

@app.route('/admin/cofre/relatorio/semana/<int:semana_id>/pdf')
@admin_required
def gerar_relatorio_semanal_pdf(semana_id):
    """Gera relatório PDF da semana"""
    # Esta função seria implementada com uma biblioteca como ReportLab ou WeasyPrint
    # Por enquanto, retornamos uma mensagem
    flash('Funcionalidade de PDF em desenvolvimento!', 'info')
    return redirect(url_for('cofre_principal', semana_id=semana_id))

@app.route('/admin/cofre/relatorio/semana/<int:semana_id>/exportar')
@admin_required
def exportar_relatorio_semanal(semana_id):
    """Exporta relatório da semana em CSV"""
    semana = Semana.query.get_or_404(semana_id)
    
    # Buscar pagamentos da semana
    pagamentos = PagamentoCofre.query.filter_by(semana_id=semana_id).all()
    
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Cabeçalho
    writer.writerow(['Relatório de Pagamentos', f'Semana: {semana.data.strftime("%d/%m/%Y")}'])
    writer.writerow(['Data de geração:', datetime.now().strftime("%d/%m/%Y %H:%M")])
    writer.writerow([])
    writer.writerow(['Nome', 'Valor (R$)', 'Método', 'Status', 'Data Pagamento', 'Observação'])
    
    # Dados
    for p in pagamentos:
        writer.writerow([
            p.jogador.nome if p.jogador else 'Jogador Manual',
            f'{p.valor:.2f}',
            p.metodo_pagamento,
            'Pago' if p.pago else 'Pendente',
            p.pago_em.strftime("%d/%m/%Y %H:%M") if p.pago_em else '',
            p.observacao or ''
        ])
    
    output.seek(0)
    
    from flask import make_response
    
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=relatorio_semana_{semana.data.strftime('%Y%m%d')}.csv"
    response.headers["Content-type"] = "text/csv"
    
    return response

# ======================================================
# ROTAS PARA JOGADORES
# ======================================================

@app.route('/redefinir_senha_usuario', methods=['POST'])
@login_required
def redefinir_senha_usuario():
    """Permite ao usuário redefinir sua própria senha"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Dados inválidos!'}), 400
        
        senha_atual = data.get('senha_atual')
        nova_senha = data.get('nova_senha')
        confirmar_senha = data.get('confirmar_senha')
        
        # Validações
        if not senha_atual or not nova_senha or not confirmar_senha:
            return jsonify({'success': False, 'message': 'Preencha todos os campos!'}), 400
        
        if nova_senha != confirmar_senha:
            return jsonify({'success': False, 'message': 'As novas senhas não coincidem!'}), 400
        
        if len(nova_senha) < 6:
            return jsonify({'success': False, 'message': 'A nova senha deve ter pelo menos 6 caracteres!'}), 400
        
        # Verificar senha atual
        if not check_password_hash(current_user.password, senha_atual):
            return jsonify({'success': False, 'message': 'Senha atual incorreta!'}), 401
        
        # Atualizar senha
        current_user.password = generate_password_hash(nova_senha)
        db.session.commit()
        
        print(f"✅ Senha redefinida para usuário: {current_user.username}")
        return jsonify({'success': True, 'message': 'Senha alterada com sucesso!'})
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao redefinir senha: {e}")
        return jsonify({'success': False, 'message': f'Erro interno: {str(e)}'}), 500

@app.route('/admin/jogadores')
@admin_required
def admin_jogadores():
    """Lista de jogadores para administração"""
    # Busca todos os jogadores separados por categoria
    todos_jogadores = Jogador.query.order_by(Jogador.nome).all()
    
    # Separa jogadores por categoria
    mensalistas_ativos = []
    nao_mensalistas = []
    inativos = []
    
    for jogador in todos_jogadores:
        if not jogador.ativo:
            inativos.append(jogador)
        elif jogador.mensalista:
            mensalistas_ativos.append(jogador)
        else:
            nao_mensalistas.append(jogador)
    
    return render_template('admin/jogadores.html',
                         mensalistas_ativos=mensalistas_ativos,
                         nao_mensalistas=nao_mensalistas,
                         inativos=inativos)

@app.route('/admin/jogador/<int:id>/gerenciar_mensalidade', methods=['GET', 'POST'])
@admin_required
def gerenciar_mensalidade(id):
    """Gerencia a mensalidade de um jogador"""
    jogador = Jogador.query.get_or_404(id)
    
    # Busca informações do ciclo atual usando a nova função
    ciclo_atual_inicio, ciclo_atual_fim = obter_ciclo_das_configuracoes()
    dias_restantes_ciclo = 0
    
    if ciclo_atual_inicio and ciclo_atual_fim:
        hoje = date.today()
        # Calcula dias do ciclo (não dias restantes)
        dias_total_ciclo = (ciclo_atual_fim - ciclo_atual_inicio).days + 1
        
        # Calcula em que dia do ciclo estamos
        if ciclo_atual_inicio <= hoje <= ciclo_atual_fim:
            dias_no_ciclo = (hoje - ciclo_atual_inicio).days + 1
            dias_restantes_ciclo = dias_total_ciclo - dias_no_ciclo + 1
        elif hoje < ciclo_atual_inicio:
            # Ciclo ainda não começou
            dias_restantes_ciclo = dias_total_ciclo
        else:
            # Ciclo já terminou
            dias_restantes_ciclo = 0
    
    if request.method == 'POST':
        # Obtém dados do formulário
        mensalista = 'mensalista' in request.form
        mensalidade_paga = 'mensalidade_paga' in request.form
        usar_ciclo_atual = 'usar_ciclo_atual' in request.form
        
        # Atualiza status
        jogador.mensalista = mensalista
        jogador.mensalidade_paga = mensalidade_paga
        
        # Processa datas
        if usar_ciclo_atual and ciclo_atual_inicio and ciclo_atual_fim:
            # Usar ciclo atual EXATAMENTE como está
            jogador.data_inicio_mensalidade = ciclo_atual_inicio
            jogador.data_fim_mensalidade = ciclo_atual_fim
            print(f"=== CICLO APLICADO ===")
            print(f"Jogador: {jogador.nome}")
            print(f"Ciclo usado: {ciclo_atual_inicio} a {ciclo_atual_fim}")
            print(f"====================")
            
            # Marca como mensalista e paga quando usar ciclo atual
            if not jogador.mensalista:
                jogador.mensalista = True
            if not jogador.mensalidade_paga:
                jogador.mensalidade_paga = True
        else:
            # Processar datas manualmente
            data_inicio_str = request.form.get('data_inicio_mensalidade')
            if data_inicio_str:
                try:
                    jogador.data_inicio_mensalidade = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Data de início inválida!', 'danger')
                    return redirect(url_for('gerenciar_mensalidade', id=id))
            elif mensalista and mensalidade_paga and not jogador.data_inicio_mensalidade:
                jogador.data_inicio_mensalidade = date.today()
            
            data_fim_str = request.form.get('data_fim_mensalidade')
            if data_fim_str:
                try:
                    jogador.data_fim_mensalidade = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Data de fim inválida!', 'danger')
                    return redirect(url_for('gerenciar_mensalidade', id=id))
            elif mensalista and mensalidade_paga and not jogador.data_fim_mensalidade:
                # Se marcou como mensalista paga e não tem data de fim, adiciona duração padrão
                config_global = ConfiguracaoGlobal.query.first()
                duracao = config_global.duracao_mensalidade_dias if config_global else 30
                jogador.data_fim_mensalidade = date.today() + timedelta(days=duracao)
        
        # Se desmarcou como mensalista, limpa as datas
        if not mensalista:
            jogador.data_fim_mensalidade = None
            jogador.mensalidade_paga = False
        
        db.session.commit()
        
        if usar_ciclo_atual and ciclo_atual_inicio and ciclo_atual_fim:
            flash(f'Mensalidade de {jogador.nome} definida para o ciclo atual ({format_date_func(ciclo_atual_inicio)} a {format_date_func(ciclo_atual_fim)})!', 'success')
        else:
            flash(f'Configurações de mensalidade de {jogador.nome} atualizadas com sucesso!', 'success')
        
        return redirect(url_for('gerenciar_mensalidade', id=id))
    
    # Calcula dias restantes se houver data de fim
    dias_restantes = None
    if jogador.data_fim_mensalidade:
        hoje = date.today()
        dias = (jogador.data_fim_mensalidade - hoje).days
        dias_restantes = dias
    
    return render_template('admin/gerenciar_mensalidade.html', 
                         jogador=jogador,
                         dias_restantes=dias_restantes,
                         ciclo_atual_inicio=ciclo_atual_inicio,
                         ciclo_atual_fim=ciclo_atual_fim,
                         dias_restantes_ciclo=dias_restantes_ciclo)

@app.route('/admin/jogador/<int:id>/inativar')
@admin_required
def inativar_jogador(id):
    """Inativa um jogador sem excluir o cadastro"""
    jogador = Jogador.query.get_or_404(id)
    
    if not jogador.ativo:
        flash(f'Jogador {jogador.nome} já está inativo!', 'warning')
        return redirect(url_for('admin_jogadores'))
    
    jogador.ativo = False
    db.session.commit()
    
    flash(f'Jogador {jogador.nome} inativado com sucesso!', 'success')
    return redirect(url_for('admin_jogadores'))                         
    

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
def completar_perfil():
    """Completar perfil de jogador após registro com upload de foto"""
    
    # Se já tem jogador vinculado, redireciona
    if current_user.is_authenticated and current_user.jogador_id:
        flash('Você já tem um perfil completo!', 'info')
        return redirect(url_for('perfil'))
    
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        apelido = request.form.get('apelido', '').strip()
        telefone = request.form.get('telefone', '').strip()
        posicao = request.form.get('posicao', '')
        nivel = request.form.get('nivel', 'intermediario')
        altura = request.form.get('altura', '').strip()
        cidade = request.form.get('cidade', '').strip()
        data_nascimento_str = request.form.get('data_nascimento', '')
        
        # Validação do nome (campo obrigatório)
        if not nome:
            flash('O nome completo é obrigatório!', 'danger')
            return redirect(url_for('completar_perfil'))
        
        # Verifica se já existe jogador com este nome
        jogador_existente = Jogador.query.filter(
            func.lower(func.trim(Jogador.nome)) == nome.strip().lower(),
            Jogador.ativo == True
        ).first()
        
        if jogador_existente and jogador_existente.user:
            flash(f'Já existe um jogador cadastrado com o nome "{nome}"!', 'danger')
            return redirect(url_for('completar_perfil'))
        
        try:
            # Se há user_id na sessão (vindo do registro), usa esse usuário
            user_id = session.get('new_user_id')
            
            if user_id:
                user = User.query.get(user_id)
                if not user:
                    flash('Sessão expirada. Faça login novamente.', 'danger')
                    return redirect(url_for('login'))
            else:
                # Se não tem user_id na sessão e não está logado, redireciona para login
                if not current_user.is_authenticated:
                    flash('Faça login primeiro!', 'warning')
                    return redirect(url_for('login'))
                user = current_user
            
            # Processar data de nascimento
            data_nascimento = None
            if data_nascimento_str:
                try:
                    data_nascimento = datetime.strptime(data_nascimento_str, '%Y-%m-%d').date()
                    # Validar idade mínima (12 anos)
                    hoje = date.today()
                    idade = hoje.year - data_nascimento.year - ((hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day))
                    if idade < 12:
                        flash('Você precisa ter pelo menos 12 anos para se cadastrar.', 'warning')
                        data_nascimento = None
                except ValueError:
                    pass
            
            # Processar altura
            altura_formatada = None
            if altura:
                try:
                    # Substituir vírgula por ponto e validar
                    altura_float = float(altura.replace(',', '.'))
                    if 1.0 <= altura_float <= 2.5:
                        altura_formatada = f"{altura_float:.2f}".replace('.', ',')
                except ValueError:
                    pass
            
            # Cria ou atualiza jogador
            if jogador_existente and not jogador_existente.user:
                # Vincula jogador existente ao usuário
                jogador = jogador_existente
                jogador.nome = nome
                jogador.apelido = apelido if apelido else jogador.apelido
                jogador.telefone = telefone if telefone else jogador.telefone
                jogador.posicao = posicao if posicao else jogador.posicao
                jogador.nivel = nivel if nivel else jogador.nivel
                jogador.altura = altura_formatada if altura_formatada else jogador.altura
                jogador.cidade = cidade if cidade else jogador.cidade
                jogador.data_nascimento = data_nascimento if data_nascimento else jogador.data_nascimento
                user.jogador_id = jogador.id
            else:
                # Cria novo jogador
                jogador = Jogador(
                    nome=nome,
                    apelido=apelido,
                    telefone=telefone,
                    posicao=posicao,
                    nivel=nivel,
                    altura=altura_formatada,
                    cidade=cidade,
                    data_nascimento=data_nascimento,
                    ativo=True
                )
                db.session.add(jogador)
                db.session.commit()  # Commit primeiro para obter o ID
                user.jogador_id = jogador.id
            
            # PROCESSAR UPLOAD DE FOTO (ADICIONADO)
            if 'foto' in request.files:
                foto = request.files['foto']
                
                # Verificar se um arquivo foi selecionado
                if foto.filename != '' and allowed_file(foto.filename):
                    try:
                        # Gerar nome único para o arquivo
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                        extensao = foto.filename.rsplit('.', 1)[1].lower() if '.' in foto.filename else 'jpg'
                        filename = secure_filename(f"jogador_{jogador.id}_{timestamp}.{extensao}")
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        
                        # Garantir que a pasta de uploads existe
                        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                        
                        # Salvar arquivo
                        foto.save(filepath)
                        
                        # Verificar se o arquivo foi salvo com sucesso
                        if os.path.exists(filepath):
                            # Remover foto anterior se existir
                            if jogador.foto_perfil:
                                old_path = os.path.join(app.static_folder, jogador.foto_perfil.lstrip('/'))
                                if os.path.exists(old_path) and os.path.basename(old_path) != filename:
                                    try:
                                        os.remove(old_path)
                                    except:
                                        pass
                            
                            # Atualizar caminho da foto no banco de dados
                            jogador.foto_perfil = f"/static/uploads/{filename}"
                            print(f"✅ Foto salva: {jogador.foto_perfil}")
                        else:
                            print(f"❌ Erro: Arquivo não foi salvo em {filepath}")
                            
                    except Exception as e:
                        print(f"❌ Erro ao processar foto: {str(e)}")
                        # Não interrompe o processo se houver erro na foto
                elif foto.filename != '':
                    print(f"❌ Tipo de arquivo não permitido: {foto.filename}")
            
            # Commit final
            db.session.commit()
            
            # Remove user_id da sessão
            session.pop('new_user_id', None)
            
            # FAZ LOGIN AUTOMÁTICO (se não estava logado)
            if not current_user.is_authenticated:
                login_user(user)
                flash('Perfil completado e login realizado automaticamente!', 'success')
            else:
                flash('Perfil completado com sucesso!', 'success')
            
            # Redireciona para o perfil
            return redirect(url_for('perfil'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao completar perfil: {str(e)}', 'danger')
            return redirect(url_for('completar_perfil'))
    
    # Se veio do registro (tem user_id na sessão), mostra formulário
    if 'new_user_id' in session:
        user = User.query.get(session['new_user_id'])
        if user:
            return render_template('completar_perfil.html', 
                                 username=user.username, 
                                 email=user.email)
    
    # Se está logado mas sem jogador vinculado
    if current_user.is_authenticated and not current_user.jogador_id:
        return render_template('completar_perfil.html',
                             username=current_user.username,
                             email=current_user.email)
    
    # Se não se encaixa em nenhum caso, redireciona
    flash('Acesso inválido.', 'danger')
    return redirect(url_for('index'))

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

@app.route('/entrar_lista_espera', methods=['POST'])
def entrar_lista_espera():
    """Entra na lista de espera (página pública) - MODIFICADA PARA EVITAR MENSALISTAS"""
    # Obtém semana_id do formulário
    semana_id = request.form.get('semana_id', type=int)
    
    if semana_id:
        semana = Semana.query.get(semana_id)
    else:
        semana = get_semana_atual()
    
    if not semana:
        flash('Semana não encontrada!', 'danger')
        return redirect(url_for('index'))
    
    if not semana.lista_aberta:
        flash('Lista de presença está fechada!', 'danger')
        return redirect(url_for('index'))
    
    nome = request.form.get('nome')
    telefone = request.form.get('telefone', '')
    posicao = request.form.get('posicao', '')
    
    if not nome:
        flash('Por favor, informe seu nome!', 'danger')
        return redirect(url_for('index'))
    
    # Verifica se é um jogador cadastrado (mensalista ou não)
    jogador_existente = Jogador.query.filter(
        func.lower(func.trim(Jogador.nome)) == nome.strip().lower(),
        Jogador.ativo == True
    ).first()
    
    if jogador_existente:
        flash(f'Jogador "{nome}" já está cadastrado! Use a confirmação normal.', 'warning')
        return redirect(url_for('index'))
    
    # Verifica se já está na lista de espera DESTA SEMANA
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
        flash(f'Você foi adicionado à lista de espera para convidados ({semana.data.strftime("%d/%m/%Y")})!', 'success')
    
    return redirect(url_for('index'))

# ======================================================
# ROTAS DO ADMIN (completo)
# ======================================================

@app.route('/admin/diagnostico_capitaes')
@admin_required
def diagnostico_capitaes():
    """Página de diagnóstico para problemas com capitães"""
    capitaes = Jogador.query.filter_by(capitao=True, ativo=True).all()
    
    capitae_info = []
    for capitao in capitaes:
        info = {
            'id': capitao.id,
            'nome': capitao.nome,
            'tem_usuario': bool(capitao.user),
            'user_username': capitao.user.username if capitao.user else None,
            'user_role': capitao.user.role if capitao.user else None,
            'status': 'OK',
            'problemas': []
        }
        
        if not capitao.user:
            info['status'] = 'CRÍTICO'
            info['problemas'].append('Não tem usuário vinculado')
        elif capitao.user.role != 'capitao':
            info['status'] = 'ERRO'
            info['problemas'].append(f'User tem role "{capitao.user.role}" em vez de "capitao"')
        
        capitae_info.append(info)
    
    # Jogadores com role 'capitao' mas que não são capitões
    usuarios_capitaes_errados = User.query.filter_by(role='capitao').all()
    usuarios_errados = []
    
    for user in usuarios_capitaes_errados:
        if not user.jogador or not user.jogador.capitao:
            usuarios_errados.append({
                'id': user.id,
                'username': user.username,
                'jogador_nome': user.jogador.nome if user.jogador else None,
                'jogador_capitao': user.jogador.capitao if user.jogador else None
            })
    
    return render_template('admin/diagnostico_capitaes.html',
                         capitae_info=capitae_info,
                         usuarios_errados=usuarios_errados)
    
@app.route('/admin/corrigir_capitao/<int:jogador_id>')
@admin_required
def corrigir_capitao(jogador_id):
    """Corrige um capitão específico"""
    jogador = Jogador.query.get_or_404(jogador_id)
    
    if not jogador.capitao:
        return jsonify({'success': False, 'message': 'Jogador não é capitão!'})
    
    corrigido = sincronizar_capitao_permissao(jogador_id)
    
    if corrigido:
        return jsonify({'success': True, 'message': f'Capitão {jogador.nome} corrigido!'})
    else:
        return jsonify({'success': True, 'message': f'Capitão {jogador.nome} já estava correto!'})

@app.route('/admin/corrigir_role_usuario/<int:user_id>')
@admin_required
def corrigir_role_usuario(user_id):
    """Corrige a role de um usuário"""
    user = User.query.get_or_404(user_id)
    
    if user.role == 'capitao' and (not user.jogador or not user.jogador.capitao):
        user.role = 'jogador'
        db.session.commit()
        return jsonify({'success': True, 'message': f'Role de {user.username} corrigida para "jogador"'})
    else:
        return jsonify({'success': False, 'message': 'Nada a corrigir'})

@app.route('/admin/sincronizar_todos_capitaes')
@admin_required
def sincronizar_todos_capitaes():
    """Sincroniza todos os capitães"""
    capitaes = Jogador.query.filter_by(capitao=True, ativo=True).all()
    corrigidos = 0
    
    for capitao in capitaes:
        if sincronizar_capitao_permissao(capitao.id):
            corrigidos += 1
    
    db.session.commit()
    return jsonify({
        'success': True, 
        'message': f'{corrigidos} de {len(capitaes)} capitães sincronizados!'
    })
    

@app.route('/admin/debug_ciclo')
@admin_required
def debug_ciclo():
    """Página de debug para visualizar informações do ciclo"""
    ciclo_inicio, ciclo_fim, no_ciclo = obter_ciclo_atual_mensalidade()
    config_inicio, config_fim = obter_ciclo_das_configuracoes()
    
    # Lista de mensalistas pagos
    mensalistas_pagos = Jogador.query.filter(
        Jogador.mensalista == True,
        Jogador.mensalidade_paga == True,
        Jogador.ativo == True
    ).all()
    
    ciclos_encontrados = {}
    for jogador in mensalistas_pagos:
        if jogador.data_inicio_mensalidade and jogador.data_fim_mensalidade:
            ciclo_key = f"{jogador.data_inicio_mensalidade}_{jogador.data_fim_mensalidade}"
            if ciclo_key in ciclos_encontrados:
                ciclos_encontrados[ciclo_key]['count'] += 1
            else:
                ciclos_encontrados[ciclo_key] = {
                    'inicio': jogador.data_inicio_mensalidade,
                    'fim': jogador.data_fim_mensalidade,
                    'count': 1
                }
    
    return render_template('admin/debug_ciclo.html',
                         ciclo_inicio=ciclo_inicio,
                         ciclo_fim=ciclo_fim,
                         no_ciclo=no_ciclo,
                         config_inicio=config_inicio,
                         config_fim=config_fim,
                         mensalistas_pagos=mensalistas_pagos,
                         ciclos_encontrados=ciclos_encontrados)


@app.route('/admin/reiniciar_semana')
@admin_required
def reiniciar_semana():
    """Reinicia a semana ESPECÍFICA selecionada"""
    # Obtém semana_id da query string
    semana_id = request.args.get('semana_id', type=int)
    
    if semana_id:
        semana = Semana.query.get(semana_id)
    else:
        semana = get_semana_atual()
    
    if not semana:
        flash('Semana não encontrada!', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    # Log da ação
    print(f"Admin {current_user.username} reiniciando semana {semana.id} ({format_date_func(semana.data)})")
    
    try:
        # Remove todos os dados do draft DESTA SEMANA ESPECÍFICA
        EscolhaDraft.query.filter_by(semana_id=semana.id).delete()
        Time.query.filter_by(semana_id=semana.id).delete()
        DraftStatus.query.filter_by(semana_id=semana.id).delete()
        HistoricoDraft.query.filter_by(semana_id=semana.id).delete()
        
        # Reseta status da semana ESPECÍFICA
        semana.draft_em_andamento = False
        semana.draft_finalizado = False
        semana.lista_encerrada = False
        semana.lista_aberta = True
        
        # Remove confirmações DESTA SEMANA
        Confirmacao.query.filter_by(semana_id=semana.id).delete()
        
        # Remove lista de espera DESTA SEMANA
        ListaEspera.query.filter_by(semana_id=semana.id).delete()
        
        db.session.commit()
        
        flash(f'✅ Semana de {format_date_func(semana.data)} reiniciada com sucesso! Lista aberta para novas confirmações.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erro ao reiniciar semana: {str(e)}', 'danger')
        print(f"Erro ao reiniciar semana {semana.id}: {e}")
    
    # Redireciona mantendo a semana selecionada
    return redirect(url_for('admin_dashboard', semana_id=semana.id))

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
        db.session.commit()  # Commit primeiro para obter o ID
        
        # ADICIONE ESTA LINHA: Sincroniza permissões
        sincronizar_capitao_permissao(jogador.id)
        
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
        
        # ADICIONE ESTA LINHA: Sincroniza permissões
        sincronizar_capitao_permissao(jogador.id)
        
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
    """Exclui permanentemente um jogador - CORRIGIDA"""
    jogador = Jogador.query.get_or_404(id)
    
    nome_jogador = jogador.nome
    
    try:
        # Remove foto se existir
        if jogador.foto_perfil:
            old_path = os.path.join(app.static_folder, jogador.foto_perfil.lstrip('/'))
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except:
                    pass
        
        # 1. Remove pagamentos do cofre associados a este jogador
        PagamentoCofre.query.filter_by(jogador_id=id).delete()
        
        # 2. Remove confirmações associadas
        Confirmacao.query.filter_by(jogador_id=id).delete()
        
        # 3. Remove escolhas de draft
        EscolhaDraft.query.filter_by(jogador_id=id).delete()
        
        # 4. Remove histórico de draft
        HistoricoDraft.query.filter_by(jogador_id=id).delete()
        
        # 5. Atualiza times onde é capitão (define como NULL ou outro valor)
        times_como_capitao = Time.query.filter_by(capitao_id=id).all()
        for time in times_como_capitao:
            # Define o capitão como NULL ou 0
            time.capitao_id = None
        
        # 6. Remove usuário associado se existir
        if jogador.user:
            db.session.delete(jogador.user)
        
        # 7. Remove o jogador
        db.session.delete(jogador)
        
        db.session.commit()
        flash(f'Jogador {nome_jogador} excluído permanentemente!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir jogador: {str(e)}', 'danger')
        print(f"❌ Erro detalhado ao excluir jogador {id}: {e}")
    
    return redirect(url_for('admin_jogadores'))

@app.route('/admin/fechar_lista')
@admin_required
def fechar_lista():
    """Fechar lista - MODIFICADA"""
    semana_id = request.args.get('semana_id', type=int)
    
    if semana_id:
        semana = Semana.query.get(semana_id)
    else:
        semana = get_semana_atual()
    
    if not semana:
        flash('Semana não encontrada!', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    semana.lista_aberta = False
    semana.lista_encerrada = True
    
    # Atualiza lista de espera automaticamente
    atualizar_lista_espera_automaticamente(semana)
    
    db.session.commit()
    flash(f'Lista de presença fechada para {format_date_func(semana.data)}!', 'success')
    return redirect(url_for('admin_dashboard', semana_id=semana.id))

@app.route('/admin/abrir_lista')
@admin_required
def abrir_lista():
    """Abrir lista - MODIFICADA"""
    semana_id = request.args.get('semana_id', type=int)
    
    if semana_id:
        semana = Semana.query.get(semana_id)
    else:
        semana = get_semana_atual()
    
    if not semana:
        flash('Semana não encontrada!', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    semana.lista_aberta = True
    semana.lista_encerrada = False
    db.session.commit()
    flash(f'Lista de presença aberta para {format_date_func(semana.data)}!', 'success')
    return redirect(url_for('admin_dashboard', semana_id=semana.id))

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

@app.route('/admin/trocar_jogador', methods=['POST'])
@admin_required
def trocar_jogador():
    try:
        semana_id = request.form.get('semana_id', type=int)
        jogador_id = request.form.get('jogador_id', type=int)
        time_destino_id = request.form.get('time_destino_id', type=int)
        
        if not all([semana_id, jogador_id, time_destino_id]):
            return jsonify({'success': False, 'message': 'Dados incompletos'})
        
        semana = Semana.query.get(semana_id)
        if not semana:
            return jsonify({'success': False, 'message': 'Semana não encontrada'})
        
        # Busca escolha original
        escolha_original = EscolhaDraft.query.filter_by(
            semana_id=semana_id,
            jogador_id=jogador_id
        ).first()
        
        if not escolha_original:
            return jsonify({'success': False, 'message': 'Jogador não encontrado no draft'})
        
        time_origem_id = escolha_original.time_id
        
        # Se for o mesmo time, não faz nada
        if time_origem_id == time_destino_id:
            return jsonify({'success': False, 'message': 'Jogador já está neste time'})
        
        # Verifica se time destino tem vaga
        time_destino = Time.query.get(time_destino_id)
        if not time_destino:
            return jsonify({'success': False, 'message': 'Time destino não encontrado'})
        
        escolhas_destino = EscolhaDraft.query.filter_by(
            semana_id=semana_id,
            time_id=time_destino_id
        ).count()
        
        if escolhas_destino >= semana.max_jogadores_por_time:
            return jsonify({'success': False, 'message': f'Time destino já está completo ({escolhas_destino}/{semana.max_jogadores_por_time})'})
        
        # Realiza a troca
        escolha_original.time_id = time_destino_id
        
        # Registra no histórico
        historico = HistoricoDraft(
            semana_id=semana_id,
            jogador_id=jogador_id,
            time_id=time_destino_id,
            acao='trocado',
            detalhes=f'Trocado do Time {time_origem_id} para Time {time_destino_id} pelo admin'
        )
        db.session.add(historico)
        
        db.session.commit()
        
        # Emite atualização via SocketIO
        try:
            socketio.emit('draft_update', {
                'semana_id': semana_id,
                'acao': 'jogador_trocado',
                'jogador_id': jogador_id,
                'time_origem_id': time_origem_id,
                'time_destino_id': time_destino_id
            }, room=f'draft_{semana_id}')
        except:
            pass
        
        return jsonify({'success': True, 'message': 'Jogador transferido com sucesso!'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'})

@app.route('/admin/adicionar_lista_espera', methods=['POST'])
@admin_required
def adicionar_lista_espera_admin():
    """Admin adiciona pessoa à lista de espera"""
    semana = get_semana_atual()
    
    nome = request.form.get('nome')
    telefone = request.form.get('telefone', '')
    posicao = request.form.get('posicao', '')
    
    if not nome:
        flash('Informe o nome!', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    # Verifica se já existe
    existente = ListaEspera.query.filter_by(
        semana_id=semana.id,
        nome=nome,
        promovido=False
    ).first()
    
    if existente:
        flash('Pessoa já está na lista de espera!', 'warning')
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
        flash(f'{nome} adicionado à lista de espera!', 'success')
    
    return redirect(url_for('admin_dashboard'))        

@app.route('/admin/lista_espera/promover/<int:id>')
@admin_required
def promover_lista_espera(id):
    """Promove convidado da lista de espera para jogador cadastrado NÃO MENSALISTA"""
    lista_espera = ListaEspera.query.get_or_404(id)
    
    # CORREÇÃO: Obtém a semana da lista de espera, não da URL
    semana = Semana.query.get(lista_espera.semana_id)
    
    if not semana:
        flash('Semana não encontrada!', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    # CORREÇÃO: Verifica se há vaga disponível CORRETAMENTE
    total_confirmados = Confirmacao.query.filter_by(
        semana_id=semana.id,
        confirmado=True
    ).count()
    
    total_vagas = semana.max_times * semana.max_jogadores_por_time
    vagas_restantes = total_vagas - total_confirmados
    
    # DEBUG: Mostra informações para diagnóstico
    print(f"=== DIAGNÓSTICO DE VAGAS ===")
    print(f"Semana: {semana.data} (ID: {semana.id})")
    print(f"Total confirmados: {total_confirmados}")
    print(f"Total vagas: {total_vagas} ({semana.max_times} times × {semana.max_jogadores_por_time} jogadores)")
    print(f"Vagas restantes: {vagas_restantes}")
    print(f"Lista de espera: {lista_espera.nome}")
    print(f"============================")
    
    if vagas_restantes <= 0:
        # Se não há vaga, mostra mensagem clara
        flash(f'Não há vagas disponíveis! {total_confirmados}/{total_vagas} vagas preenchidas.', 'warning')
        return redirect(url_for('admin_dashboard'))
    
    # Busca jogador existente ou cria um novo
    jogador = Jogador.query.filter(
        func.lower(func.trim(Jogador.nome)) == lista_espera.nome.strip().lower(),
        Jogador.ativo == True
    ).first()
    
    if not jogador:
        # Cria novo jogador NÃO MENSALISTA (convidado promovido)
        jogador = Jogador(
            nome=lista_espera.nome,
            telefone=lista_espera.telefone,
            posicao=lista_espera.posicao_preferida,
            mensalista=False,  # NÃO é mensalista
            capitao=False,     # NÃO é capitão
            ativo=True,
            nivel='intermediario'  # Nível padrão
        )
        db.session.add(jogador)
        db.session.commit()
        flash(f'Convidado {lista_espera.nome} cadastrado como jogador NÃO MENSALISTA!', 'info')
    
    # Verifica se já está confirmado
    confirmacao = Confirmacao.query.filter_by(
        jogador_id=jogador.id,
        semana_id=semana.id
    ).first()
    
    if confirmacao:
        if confirmacao.confirmado:
            flash(f'{lista_espera.nome} já está confirmado!', 'warning')
        else:
            # Se existia mas não estava confirmado, confirma
            confirmacao.confirmado = True
            confirmacao.confirmado_em = datetime.utcnow()
            flash(f'{lista_espera.nome} confirmado na semana!', 'success')
    else:
        # Cria nova confirmação
        confirmacao = Confirmacao(
            jogador_id=jogador.id,
            semana_id=semana.id,
            confirmado=True,
            confirmado_em=datetime.utcnow(),
            prioridade=0  # Menor prioridade (não é mensalista nem capitão)
        )
        db.session.add(confirmacao)
        flash(f'{lista_espera.nome} adicionado aos confirmados!', 'success')
    
    # Marca como promovido na lista de espera
    lista_espera.promovido = True
    lista_espera.promovido_em = datetime.utcnow()
    
    db.session.commit()
    
    return redirect(url_for('admin_dashboard', semana_id=semana.id))

@app.route('/api/draft/status_public')
def api_draft_status_public():
    """API para status do draft - versão pública"""
    semana_id = request.args.get('semana_id', type=int)
    
    if semana_id:
        semana = Semana.query.get(semana_id)
    else:
        semana = get_semana_atual()
    
    if not semana:
        return jsonify({'success': False, 'message': 'Semana não encontrada'})
    
    # Status do draft
    draft_status = DraftStatus.query.filter_by(semana_id=semana.id).first()
    
    # Jogadores disponíveis
    jogadores_disponiveis = []
    if semana.draft_em_andamento:
        disponiveis = get_jogadores_disponiveis_draft(semana)
        jogadores_disponiveis = [{
            'id': j.id,
            'nome': j.nome,
            'apelido': j.apelido,
            'posicao': j.posicao,
            'posicao_display': get_posicao_display_func(j.posicao),
            'nivel': j.nivel,
            'nivel_display': get_nivel_display_func(j.nivel),
            'foto_perfil': j.foto_perfil,
            'mensalista': j.mensalista,
            'capitao': j.capitao
        } for j in disponiveis]
    
    # Times info COM TODOS OS JOGADORES
    times = Time.query.filter_by(semana_id=semana.id).order_by(Time.ordem_escolha).all()
    times_info = []
    for time in times:
        escolhas = EscolhaDraft.query.filter_by(
            semana_id=semana.id,
            time_id=time.id
        ).order_by(EscolhaDraft.ordem_escolha).all()
        
        jogadores_time = []
        for escolha in escolhas:
            jogador = Jogador.query.get(escolha.jogador_id)
            if jogador:
                jogadores_time.append({
                    'id': jogador.id,
                    'nome': jogador.nome,
                    'apelido': jogador.apelido,
                    'posicao': jogador.posicao,
                    'posicao_display': get_posicao_display_func(jogador.posicao),
                    'nivel': jogador.nivel,
                    'nivel_display': get_nivel_display_func(jogador.nivel),
                    'foto_perfil': jogador.foto_perfil,
                    'mensalista': jogador.mensalista,
                    'round_num': escolha.round_num,
                    'ordem_escolha': escolha.ordem_escolha
                })
        
        times_info.append({
            'id': time.id,
            'nome': time.nome,
            'cor': time.cor,
            'total_jogadores': len(jogadores_time),
            'jogadores': jogadores_time
        })
    
    # Histórico recente (últimas 20 escolhas)
    historico = []
    if semana.draft_em_andamento or semana.draft_finalizado:
        escolhas = EscolhaDraft.query.filter_by(semana_id=semana.id)\
            .order_by(EscolhaDraft.ordem_escolha.desc())\
            .limit(20)\
            .all()
        
        for escolha in escolhas:
            jogador = Jogador.query.get(escolha.jogador_id)
            time = Time.query.get(escolha.time_id)
            if jogador and time:
                historico.append({
                    'jogador_id': jogador.id,
                    'jogador_nome': jogador.nome,
                    'time_id': time.id,
                    'time_nome': time.nome,
                    'time_cor': time.cor,
                    'ordem_escolha': escolha.ordem_escolha,
                    'round_num': escolha.round_num,
                    'posicao': jogador.posicao
                })
    
    # Informações do capitão atual
    vez_capitao = None
    if draft_status and draft_status.vez_capitao_id:
        capitao = Jogador.query.get(draft_status.vez_capitao_id)
        if capitao:
            vez_capitao = {
                'id': capitao.id,
                'nome': capitao.nome
            }
    
    return jsonify({
        'success': True,
        'data': {
            'semana_id': semana.id,
            'draft_em_andamento': semana.draft_em_andamento,
            'draft_finalizado': semana.draft_finalizado,
            'rodada_atual': draft_status.rodada_atual if draft_status else 0,
            'escolha_atual': draft_status.escolha_atual if draft_status else 0,
            'vez_capitao': vez_capitao,
            'jogadores_disponiveis': jogadores_disponiveis,
            'times_info': times_info,
            'historico': historico
        },
        'updated_at': datetime.utcnow().isoformat()
    })

@app.route('/admin/adicionar_jogador_time', methods=['POST'])
@admin_required
def adicionar_jogador_time():
    try:
        semana_id = request.form.get('semana_id', type=int)
        jogador_id = request.form.get('jogador_id', type=int)
        time_id = request.form.get('time_id', type=int)
        
        if not all([semana_id, jogador_id, time_id]):
            return jsonify({'success': False, 'message': 'Dados incompletos'})
        
        semana = Semana.query.get(semana_id)
        if not semana:
            return jsonify({'success': False, 'message': 'Semana não encontrada'})
        
        # Verifica se jogador existe
        jogador = Jogador.query.get(jogador_id)
        if not jogador or not jogador.ativo:
            return jsonify({'success': False, 'message': 'Jogador não encontrado'})
        
        # Verifica se time existe
        time = Time.query.get(time_id)
        if not time:
            return jsonify({'success': False, 'message': 'Time não encontrado'})
        
        # Verifica se jogador está confirmado
        confirmacao = Confirmacao.query.filter_by(
            semana_id=semana_id,
            jogador_id=jogador_id,
            confirmado=True
        ).first()
        
        if not confirmacao:
            return jsonify({'success': False, 'message': 'Jogador não confirmado para esta semana'})
        
        # Verifica se já foi escolhido
        escolha_existente = EscolhaDraft.query.filter_by(
            semana_id=semana_id,
            jogador_id=jogador_id
        ).first()
        
        if escolha_existente:
            return jsonify({'success': False, 'message': 'Jogador já está em um time'})
        
        # Verifica se time tem vaga
        escolhas_time = EscolhaDraft.query.filter_by(
            semana_id=semana_id,
            time_id=time_id
        ).count()
        
        if escolhas_time >= semana.max_jogadores_por_time:
            return jsonify({'success': False, 'message': f'Time já está completo ({escolhas_time}/{semana.max_jogadores_por_time})'})
        
        # Determina ordem da escolha
        ultima_escolha = EscolhaDraft.query.filter_by(semana_id=semana_id).order_by(EscolhaDraft.ordem_escolha.desc()).first()
        nova_ordem = ultima_escolha.ordem_escolha + 1 if ultima_escolha else 1
        
        # Determina rodada
        draft_status = DraftStatus.query.filter_by(semana_id=semana_id).first()
        rodada = draft_status.rodada_atual if draft_status else 1
        
        # Adiciona jogador ao time
        escolha = EscolhaDraft(
            semana_id=semana_id,
            jogador_id=jogador_id,
            time_id=time_id,
            ordem_escolha=nova_ordem,
            round_num=rodada,
            escolhido_em=datetime.utcnow()
        )
        db.session.add(escolha)
        
        # Registra no histórico
        historico = HistoricoDraft(
            semana_id=semana_id,
            jogador_id=jogador_id,
            time_id=time_id,
            acao='adicionado_admin',
            detalhes=f'Adicionado ao Time {time_id} pelo admin'
        )
        db.session.add(historico)
        
        db.session.commit()
        
        # Emite atualização
        try:
            socketio.emit('draft_update', {
                'semana_id': semana_id,
                'acao': 'jogador_adicionado',
                'jogador_id': jogador_id,
                'jogador_nome': jogador.nome,
                'time_id': time_id
            }, room=f'draft_{semana_id}')
        except:
            pass
        
        return jsonify({'success': True, 'message': f'{jogador.nome} adicionado ao time!'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'})    

@app.route('/admin/lista_espera/remover/<int:id>')
@admin_required
def remover_lista_espera(id):
    lista_espera = ListaEspera.query.get_or_404(id)
    db.session.delete(lista_espera)
    db.session.commit()
    flash('Removido da lista de espera!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/mudar_capitao/<int:time_id>', methods=['GET', 'POST'])
@admin_required
def mudar_capitao(time_id):
    """Altera o capitão de um time após o draft iniciado"""
    time = Time.query.get_or_404(time_id)
    semana = Semana.query.get(time.semana_id)
    
    if not semana.draft_em_andamento and not semana.draft_finalizado:
        flash('O draft não está em andamento!', 'warning')
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        novo_capitao_id = request.form.get('novo_capitao_id', type=int)
        
        if not novo_capitao_id:
            flash('Selecione um novo capitão!', 'danger')
            return redirect(url_for('mudar_capitao', time_id=time_id))
        
        novo_capitao = Jogador.query.get(novo_capitao_id)
        if not novo_capitao or not novo_capitao.ativo:
            flash('Jogador não encontrado ou inativo!', 'danger')
            return redirect(url_for('mudar_capitao', time_id=time_id))
        
        # Verifica se o jogador está confirmado para esta semana
        confirmacao = Confirmacao.query.filter_by(
            semana_id=semana.id,
            jogador_id=novo_capitao_id,
            confirmado=True
        ).first()
        
        if not confirmacao:
            flash('O jogador selecionado não está confirmado para esta semana!', 'danger')
            return redirect(url_for('mudar_capitao', time_id=time_id))
        
        # Atualiza o capitão do time
        capitao_antigo = Jogador.query.get(time.capitao_id)
        time.capitao_id = novo_capitao_id
        
        # Se o draft está em andamento e é a vez do capitão antigo, atualiza
        if semana.draft_em_andamento:
            draft_status = DraftStatus.query.filter_by(semana_id=semana.id).first()
            if draft_status and draft_status.vez_capitao_id == capitao_antigo.id:
                draft_status.vez_capitao_id = novo_capitao_id
        
        db.session.commit()
        
        # Registra no histórico
        historico = HistoricoDraft(
            semana_id=semana.id,
            jogador_id=novo_capitao_id,
            time_id=time.id,
            acao='capitao_trocado',
            detalhes=f'Capitão alterado de {capitao_antigo.nome} para {novo_capitao.nome} pelo admin'
        )
        db.session.add(historico)
        db.session.commit()
        
        flash(f'Capitão alterado! Agora {novo_capitao.nome} é o capitão do {time.nome}.', 'success')
        return redirect(url_for('admin_dashboard'))
    
    # Busca jogadores confirmados que podem ser capitães
    confirmacoes = Confirmacao.query.filter_by(
        semana_id=semana.id,
        confirmado=True
    ).all()
    
    jogadores_confirmados_ids = [c.jogador_id for c in confirmacoes]
    jogadores_disponiveis = Jogador.query.filter(
        Jogador.id.in_(jogadores_confirmados_ids),
        Jogador.ativo == True
    ).order_by(Jogador.nome).all()
    
    return render_template('admin/mudar_capitao.html',
                         time=time,
                         semana=semana,
                         jogadores_disponiveis=jogadores_disponiveis)

@app.route('/admin/jogador/reativar/<int:id>')
@admin_required
def reativar_jogador(id):
    """Reativa um jogador inativo"""
    jogador = Jogador.query.get_or_404(id)
    
    if jogador.ativo:
        return jsonify({'success': False, 'message': 'Jogador já está ativo!'})
    
    jogador.ativo = True
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'Jogador {jogador.nome} reativado com sucesso!'})                         

@app.route('/admin/jogador/<int:id>/renovar_mensalidade')
@admin_required
def renovar_mensalidade(id):
    """Renova mensalidade usando o ciclo atual do sistema"""
    jogador = Jogador.query.get_or_404(id)
    
    hoje = date.today()
    
    # Verifica se há um ciclo ativo no sistema
    ciclo_inicio, ciclo_fim = obter_ciclo_das_configuracoes()
    
    if ciclo_inicio and ciclo_fim:
        # Usa o ciclo ativo do sistema
        jogador.mensalista = True
        jogador.mensalidade_paga = True
        jogador.data_inicio_mensalidade = ciclo_inicio
        jogador.data_fim_mensalidade = ciclo_fim
        
        db.session.commit()
        flash(f'Mensalidade de {jogador.nome} renovada usando o ciclo ativo do sistema ({format_date_func(ciclo_inicio)} a {format_date_func(ciclo_fim)})!', 'success')
    else:
        # Fallback para o método antigo (30 dias)
        config_global = ConfiguracaoGlobal.query.first()
        duracao = config_global.duracao_mensalidade_dias if config_global else 30
        
        jogador.mensalista = True
        jogador.mensalidade_paga = True
        jogador.data_inicio_mensalidade = hoje
        jogador.data_fim_mensalidade = hoje + timedelta(days=duracao)
        
        db.session.commit()
        flash(f'Mensalidade de {jogador.nome} renovada por {duracao} dias!', 'success')
    
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

# ======================================================
# ROTAS DO CAPITÃO (corrigidas)
# ======================================================

@app.route('/capitao/escolher', methods=['POST'])
@capitao_required
def capitao_escolher():
    """Escolhe um jogador no draft - COMPLETAMENTE ATUALIZADA PARA MÚLTIPLAS SEMANAS"""
    # Obtém semana_id do POST (prioridade) ou do parâmetro GET
    semana_id = request.form.get('semana_id', type=int)
    if not semana_id:
        # Tenta obter do parâmetro GET para compatibilidade
        semana_id = request.args.get('semana_id', type=int)
    
    if not semana_id:
        # Fallback para compatibilidade com código antigo
        semana = get_semana_atual()
    else:
        semana = Semana.query.get(semana_id)
        if not semana:
            return jsonify({'success': False, 'message': 'Semana não encontrada!'})
    
    # VERIFICAÇÕES DE SEGURANÇA
    if not semana.draft_em_andamento:
        return jsonify({'success': False, 'message': 'Draft não está em andamento!'})
    
    # Garante que apenas o capitão da vez possa escolher
    draft_status = DraftStatus.query.filter_by(semana_id=semana.id).first()
    if not draft_status or draft_status.vez_capitao_id != current_user.jogador_id:
        return jsonify({'success': False, 'message': 'Não é a sua vez de escolher!'})
    
    # Busca time do capitão PARA ESTA SEMANA
    time = Time.query.filter_by(
        semana_id=semana.id,
        capitao_id=current_user.jogador_id
    ).first()
    
    if not time:
        return jsonify({'success': False, 'message': 'Time não encontrado!'})
    
    jogador_id = request.form.get('jogador_id', type=int)
    
    # Verifica jogador
    jogador = db.session.get(Jogador, jogador_id)
    if not jogador or not jogador.ativo:
        return jsonify({'success': False, 'message': 'Jogador não encontrado!'})
    
    # Verifica se jogador está confirmado PARA ESTA SEMANA
    confirmacao = Confirmacao.query.filter_by(
        semana_id=semana.id,
        jogador_id=jogador_id,
        confirmado=True
    ).first()
    
    if not confirmacao:
        return jsonify({'success': False, 'message': 'Jogador não confirmou presença!'})
    
    # Verifica se já foi escolhido NESTA SEMANA
    escolha_existente = EscolhaDraft.query.filter_by(
        semana_id=semana.id,
        jogador_id=jogador_id
    ).first()
    
    if escolha_existente:
        return jsonify({'success': False, 'message': 'Jogador já foi escolhido!'})
    
    # FAZ A ESCOLHA
    escolha = EscolhaDraft(
        semana_id=semana.id,
        jogador_id=jogador_id,
        time_id=time.id,
        ordem_escolha=draft_status.escolha_atual,
        round_num=draft_status.rodada_atual,
        escolhido_em=datetime.utcnow()
    )
    db.session.add(escolha)
    
    # Registra no histórico DESTA SEMANA
    historico = HistoricoDraft(
        semana_id=semana.id,
        jogador_id=jogador_id,
        time_id=time.id,
        acao='escolhido',
        detalhes=f'Escolhido por {current_user.jogador.nome} na rodada {draft_status.rodada_atual}'
    )
    db.session.add(historico)
    
    # Atualiza status do draft DESTA SEMANA
    draft_status.escolha_atual += 1
    
    # LÓGICA PARA DETERMINAR PRÓXIMO CAPITÃO (mantida igual, mas para esta semana)
    times = Time.query.filter_by(semana_id=semana.id).order_by(Time.ordem_escolha).all()
    
    if len(times) == 0:
        return jsonify({'success': False, 'message': 'Nenhum time encontrado!'})
    
    # Encontra índice do time atual
    time_atual_index = -1
    for i, t in enumerate(times):
        if t.id == time.id:
            time_atual_index = i
            break
    
    if time_atual_index == -1:
        return jsonify({'success': False, 'message': 'Time atual não encontrado na lista!'})
    
    # Lógica snake draft (NÃO ALTERADA)
    if draft_status.modo_snake:
        if draft_status.rodada_atual % 2 == 1:
            if time_atual_index == len(times) - 1:
                draft_status.rodada_atual += 1
                proximo_index = time_atual_index - 1
            else:
                proximo_index = time_atual_index + 1
        else:
            if time_atual_index == 0:
                draft_status.rodada_atual += 1
                proximo_index = time_atual_index + 1
            else:
                proximo_index = time_atual_index - 1
    else:
        if time_atual_index == len(times) - 1:
            proximo_index = 0
            draft_status.rodada_atual += 1
        else:
            proximo_index = time_atual_index + 1
    
    # Garante que o índice está dentro dos limites
    proximo_index = max(0, min(proximo_index, len(times) - 1))
    draft_status.vez_capitao_id = times[proximo_index].capitao_id
    
    # Verifica se draft acabou
    draft_completo = True
    for t in times:
        num_escolhas = EscolhaDraft.query.filter_by(
            semana_id=semana.id,
            time_id=t.id
        ).count()
        if num_escolhas < semana.max_jogadores_por_time:
            draft_completo = False
            break
    
    if draft_completo:
        draft_status.finalizado = True
        semana.draft_em_andamento = False
        semana.draft_finalizado = True
    
    db.session.commit()
    
    # EMITE ATUALIZAÇÕES VIA SOCKETIO (para esta semana específica)
    try:
        # Emite para todos os capitães conectados nesta semana
        socketio.emit('player_selected_update', {
            'semana_id': semana.id,
            'jogador_id': jogador.id,
            'jogador_nome': jogador.nome,
            'time_id': time.id,
            'time_nome': time.nome,
            'vez_capitao_id': draft_status.vez_capitao_id,
            'rodada_atual': draft_status.rodada_atual,
            'escolha_atual': draft_status.escolha_atual,
            'finalizado': draft_status.finalizado
        }, room=f'draft_{semana.id}')
        
        # Emite status completo atualizado
        emitir_status_draft_atualizado(semana.id)
        
        # Emite para o público também
        emitir_atualizacao_publica(semana.id, jogador.id, jogador.nome, time.id, time.nome)
        
    except Exception as e:
        print(f"Erro ao emitir atualizações SocketIO: {e}")
        # Continua mesmo com erro no SocketIO
    
    return jsonify({
        'success': True,
        'message': f'{jogador.nome} escolhido para o {time.nome}!',
        'draft_finalizado': draft_status.finalizado,
        'proximo_capitao_id': draft_status.vez_capitao_id,
        'semana_id': semana.id  # Adicionado para referência
    })

# ======================================================
# ROTAS DO DRAFT (VISUALIZAÇÃO PÚBLICA)
# ======================================================

@app.route('/times')
def ver_times():
    """Página para visualizar todos os times formados por semana"""
    # Filtros
    ano = request.args.get('ano', type=int)
    mes = request.args.get('mes', type=int)
    status = request.args.get('status', 'todos')  # todos, finalizados, andamento
    
    hoje = date.today()
    
    # Query base - busca semanas com times formados
    query = Semana.query.filter(
        Semana.draft_finalizado == True  # Apenas drafts finalizados
    )
    
    # Aplicar filtros
    if ano:
        query = query.filter(db.extract('year', Semana.data) == ano)
    if mes:
        query = query.filter(db.extract('month', Semana.data) == mes)
    
    # Ordenar por data (mais recente primeiro)
    semanas = query.order_by(Semana.data.desc()).all()
    
    # Para cada semana, buscar times e jogadores
    semanas_com_times = []
    for semana in semanas:
        times = Time.query.filter_by(semana_id=semana.id).order_by(Time.ordem_escolha).all()
        
        # Para cada time, buscar jogadores
        times_com_jogadores = []
        for time in times:
            escolhas = EscolhaDraft.query.filter_by(
                semana_id=semana.id,
                time_id=time.id
            ).order_by(EscolhaDraft.ordem_escolha).all()
            
            jogadores = []
            for escolha in escolhas:
                jogador = Jogador.query.get(escolha.jogador_id)
                if jogador:
                    jogadores.append({
                        'jogador': jogador,
                        'ordem_escolha': escolha.ordem_escolha,
                        'round': escolha.round_num
                    })
            
            times_com_jogadores.append({
                'time': time,
                'jogadores': jogadores,
                'total_jogadores': len(jogadores)
            })
        
        # Estatísticas da semana
        total_jogadores = sum(len(t['jogadores']) for t in times_com_jogadores)
        capitaes = [Jogador.query.get(time.capitao_id) for time in times if time.capitao_id]
        
        semanas_com_times.append({
            'semana': semana,
            'times': times_com_jogadores,
            'estatisticas': {
                'total_times': len(times),
                'total_jogadores': total_jogadores,
                'capitaes': capitaes
            }
        })
    
    # Buscar anos/meses disponíveis para filtro
    anos_disponiveis = db.session.query(
        db.extract('year', Semana.data).label('ano')
    ).filter(Semana.draft_finalizado == True).distinct().order_by('ano').all()
    
    meses_disponiveis = db.session.query(
        db.extract('month', Semana.data).label('mes')
    ).filter(Semana.draft_finalizado == True).distinct().order_by('mes').all()
    
    return render_template('times/historico.html',
                         semanas_com_times=semanas_com_times,
                         anos_disponiveis=[a.ano for a in anos_disponiveis if a.ano],
                         meses_disponiveis=[m.mes for m in meses_disponiveis if m.mes],
                         ano_selecionado=ano,
                         mes_selecionado=mes,
                         status_selecionado=status,
                         hoje=hoje)

@app.route('/draft')
def visualizar_draft():
    """Visualizar draft - MODIFICADA PARA ACEITAR SEMANA_ID"""
    semana_id = request.args.get('semana_id', type=int)
    
    if semana_id:
        semana = Semana.query.get(semana_id)
        if not semana:
            flash('Semana não encontrada!', 'info')
            return redirect(url_for('index'))
    else:
        # Tenta buscar uma semana com draft em andamento primeiro
        hoje = date.today()
        semana = Semana.query.filter(
            or_(
                Semana.draft_em_andamento == True,
                Semana.draft_finalizado == True
            ),
            Semana.data >= hoje - timedelta(days=7)  # Últimos 7 dias
        ).order_by(
            Semana.draft_em_andamento.desc(),  # Prioriza drafts em andamento
            Semana.data.desc()
        ).first()
        
        if not semana:
            semana = get_semana_atual()
    
    if not semana:
        flash('Semana não encontrada!', 'info')
        return redirect(url_for('index'))
    
    if not (semana.draft_em_andamento or semana.draft_finalizado):
        flash('Não há draft em andamento ou finalizado para esta semana!', 'info')
        # Mostra a página mesmo assim, mas com mensagem
        # Não redireciona, permite visualizar a semana sem draft
    
    # O RESTO DO CÓDIGO PERMANECE IDÊNTICO
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
    
    # Busca outras semanas disponíveis para navegação
    hoje = date.today()
    outras_semanas = Semana.query.filter(
        or_(
            Semana.draft_em_andamento == True,
            Semana.draft_finalizado == True
        ),
        Semana.data >= hoje - timedelta(days=30)
    ).order_by(Semana.data.desc()).all()
    
    return render_template('draft/publico.html',
                         semana=semana,
                         times=times,
                         escolhas_por_time=escolhas_por_time,
                         draft_status=draft_status,
                         jogadores_disponiveis=jogadores_disponiveis,
                         MAX_JOGADORES_POR_TIME=semana.max_jogadores_por_time,
                         outras_semanas=outras_semanas)


@app.route('/draft_publico')
def draft_publico():
    """Página de draft público COM SELEÇÃO DE DATA - NOVA"""
    # Obter todas as semanas com draft (últimos 60 dias)
    hoje = date.today()
    data_inicio = hoje - timedelta(days=60)
    
    # Busca semanas com draft
    semanas_com_draft = Semana.query.filter(
        Semana.data >= data_inicio,
        or_(
            Semana.draft_em_andamento == True,
            Semana.draft_finalizado == True
        )
    ).order_by(Semana.data.desc()).all()
    
    # Busca a semana selecionada
    semana_id = request.args.get('semana_id', type=int)
    
    if semana_id:
        semana_selecionada = Semana.query.get(semana_id)
    elif semanas_com_draft:
        # Prioridade: draft em andamento > draft finalizado > nenhum
        semana_em_andamento = next((s for s in semanas_com_draft if s.draft_em_andamento), None)
        if semana_em_andamento:
            semana_selecionada = semana_em_andamento
        else:
            semana_selecionada = semanas_com_draft[0]
    else:
        # Se não houver drafts, usa a semana atual
        semana_selecionada = get_semana_atual()
        semanas_com_draft = [semana_selecionada]
    
    # Se não encontrou semana, redireciona
    if not semana_selecionada:
        flash('Semana não encontrada!', 'danger')
        return redirect(url_for('index'))
    
    # A PARTIR DAQUI USA A MESMA LÓGICA DA ROTA /draft
    if not (semana_selecionada.draft_em_andamento or semana_selecionada.draft_finalizado):
        flash('Não há draft em andamento ou finalizado para esta semana!', 'info')
    
    # Busca times
    times = Time.query.filter_by(semana_id=semana_selecionada.id).order_by(Time.ordem_escolha).all()
    
    # Busca escolhas
    escolhas_por_time = {}
    for time in times:
        escolhas = EscolhaDraft.query.filter_by(
            semana_id=semana_selecionada.id,
            time_id=time.id
        ).order_by(EscolhaDraft.ordem_escolha).all()
        escolhas_por_time[time.id] = escolhas
    
    # Busca status do draft
    draft_status = DraftStatus.query.filter_by(semana_id=semana_selecionada.id).first()
    
    # Jogadores disponíveis (se draft em andamento)
    jogadores_disponiveis = []
    if semana_selecionada.draft_em_andamento:
        jogadores_disponiveis = get_jogadores_disponiveis_draft(semana_selecionada)
    
    # Busca próximas semanas com draft para o dropdown
    semanas_disponiveis = Semana.query.filter(
        Semana.data >= hoje - timedelta(days=30),
        Semana.data <= hoje + timedelta(days=60)
    ).order_by(Semana.data.desc()).all()
    
    # Marca quais semanas têm draft
    semanas_com_info = []
    for s in semanas_disponiveis:
        tem_draft = s.draft_em_andamento or s.draft_finalizado
        semanas_com_info.append({
            'semana': s,
            'tem_draft': tem_draft,
            'ativo': s.draft_em_andamento
        })
    
    # Busca recados ativos para mostrar (opcional)
    recados = Recado.query.filter_by(ativo=True).filter(
        or_(
            Recado.data_expiracao.is_(None),
            Recado.data_expiracao >= date.today()
        )
    ).order_by(Recado.importante.desc(), Recado.data_publicacao.desc()).limit(3).all()
    
    return render_template('draft/publico.html',
                         # PARÂMETROS EXISTENTES (mantém compatibilidade)
                         semana=semana_selecionada,
                         times=times,
                         escolhas_por_time=escolhas_por_time,
                         draft_status=draft_status,
                         jogadores_disponiveis=jogadores_disponiveis,
                         MAX_JOGADORES_POR_TIME=semana_selecionada.max_jogadores_por_time,
                         # NOVOS PARÂMETROS PARA SELEÇÃO DE DATA
                         semanas_com_draft=semanas_com_draft,
                         semanas_disponiveis=semanas_com_info,
                         recados=recados,
                         modo_publico=True)  # Flag para ativar funcionalidades extras



# ======================================================
# SOCKET.IO - COMUNICAÇÃO EM TEMPO REAL (corrigido)
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
    if not semana_id:
        return
    
    semana = Semana.query.get(semana_id)
    if not semana or not semana.draft_em_andamento:
        return
    
    draft_status = DraftStatus.query.filter_by(semana_id=semana.id).first()
    if not draft_status:
        return
    
    # NÃO DECREMENTA O TIMER AQUI - isso é feito pela thread em background
    
    # Emite status atualizado apenas para este cliente
    try:
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
                'capitao_id': capitao.id if capitao else None,
                'jogadores': jogadores,
                'total_jogadores': len(jogadores)
            })
        
        # Emite apenas para este cliente
        emit('draft_status_update', {
            'semana_id': semana.id,
            'draft_em_andamento': semana.draft_em_andamento,
            'finalizado': draft_status.finalizado,
            'rodada_atual': draft_status.rodada_atual,
            'escolha_atual': draft_status.escolha_atual,
            'tempo_restante': draft_status.tempo_restante if draft_status and semana.tempo_escolha > 0 else None,
            'tempo_configurado': semana.tempo_escolha,
            'vez_capitao_id': draft_status.vez_capitao_id if draft_status else None,
            'capitao_atual': draft_status.vez_capitao.nome if draft_status and draft_status.vez_capitao else None,
            'times': times_info
        })
        
    except Exception as e:
        print(f"Erro ao emitir status: {e}")

@socketio.on('player_selected')
def handle_player_selected(data):
    """Quando um jogador é escolhido, notifica todos os capitães"""
    semana_id = data.get('semana_id')
    jogador_id = data.get('jogador_id')
    time_id = data.get('time_id')
    
    if not all([semana_id, jogador_id, time_id]):
        return
    
    # Busca informações
    semana = Semana.query.get(semana_id)
    jogador = Jogador.query.get(jogador_id)
    time = Time.query.get(time_id)
    
    if not all([semana, jogador, time]):
        return
    
    # Busca draft status atualizado
    draft_status = DraftStatus.query.filter_by(semana_id=semana.id).first()
    if not draft_status:
        return
    
    # Emite atualização específica
    emit('player_selected_update', {
        'semana_id': semana.id,
        'jogador_id': jogador.id,
        'jogador_nome': jogador.nome,
        'time_id': time.id,
        'time_nome': time.nome,
        'vez_capitao_id': draft_status.vez_capitao_id,
        'rodada_atual': draft_status.rodada_atual,
        'escolha_atual': draft_status.escolha_atual,
        'finalizado': draft_status.finalizado
    }, room=f'draft_{semana.id}')        


@socketio.on('join_draft_public')
def handle_join_draft_public(data):
    """Público entra em sala separada"""
    semana_id = data.get('semana_id')
    if semana_id:
        join_room(f'draft_public_{semana_id}')
        print(f"👥 Público {request.sid} entrou na sala draft_public_{semana_id}")
        emit('joined_draft_public', {'semana_id': semana_id})

@socketio.on('request_draft_status_public')
def handle_request_draft_status_public(data):
    """Público solicita status"""
    semana_id = data.get('semana_id')
    if not semana_id:
        return
    
    semana = Semana.query.get(semana_id)
    if not semana:
        return
    
    # Envia status simplificado para o público
    draft_status = DraftStatus.query.filter_by(semana_id=semana.id).first()
    if not draft_status:
        return
    
    times = Time.query.filter_by(semana_id=semana.id).order_by(Time.ordem_escolha).all()
    
    times_info_simplificado = []
    for time in times:
        escolhas = EscolhaDraft.query.filter_by(
            semana_id=semana.id,
            time_id=time.id
        ).order_by(EscolhaDraft.ordem_escolha).all()
        
        jogadores_simplificado = []
        for escolha in escolhas:
            jogador = Jogador.query.get(escolha.jogador_id)
            jogadores_simplificado.append({
                'id': jogador.id,
                'nome': jogador.nome,
                'posicao': jogador.posicao
            })
        
        times_info_simplificado.append({
            'id': time.id,
            'nome': time.nome,
            'cor': time.cor,
            'total_jogadores': len(jogadores_simplificado)
        })
    
    emit('draft_status_public', {
        'semana_id': semana.id,
        'rodada_atual': draft_status.rodada_atual,
        'escolha_atual': draft_status.escolha_atual,
        'vez_capitao_id': draft_status.vez_capitao_id,
        'times': times_info_simplificado
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
        'date': date,
        'get_dia_semana': get_dia_semana,
        'get_dia_semana_curto': get_dia_semana_curto,
        'obter_ciclo_das_configuracoes': obter_ciclo_das_configuracoes,
        'obter_jogadores_no_ciclo_atual': obter_jogadores_no_ciclo_atual,
        
    }

@app.route('/')
def index():
    """PÁGINA PRINCIPAL - MODIFICADA PARA MOSTRAR MÚLTIPLAS SEMANAS"""
    # Busca próximas semanas (próximos 14 dias)
    hoje = date.today()
    # Mostrar sempre as próximas X semanas
    proximas_semanas = Semana.query.filter(
        Semana.data >= hoje
    ).order_by(Semana.data).limit(10).all()  # Mostrar 10 semanas
    
    # Se não há semanas, usa a semana atual
    if not proximas_semanas:
        semana_atual = get_semana_atual()
        proximas_semanas = [semana_atual]
    
    # Busca jogadores ativos
    jogadores = Jogador.query.filter_by(ativo=True).order_by(Jogador.nome).all()
    
    # Para cada semana, busca suas confirmações, recados e PIX
    semanas_com_info = []
    for semana in proximas_semanas:
        confirmacoes_dict = {}
        confirmacoes = Confirmacao.query.filter_by(semana_id=semana.id).all()
        
        for conf in confirmacoes:
            confirmacoes_dict[conf.jogador_id] = {
                'confirmado': conf.confirmado,
                'prioridade': conf.prioridade,
                'presente': conf.presente
            }
        
        # Busca TIMES desta semana (SE HOUVER)
        times_da_semana = Time.query.filter_by(semana_id=semana.id).all()
        
        # Para cada time, busca suas escolhas
        for time in times_da_semana:
            time.escolhas = EscolhaDraft.query.filter_by(
                semana_id=semana.id,
                time_id=time.id
            ).order_by(EscolhaDraft.ordem_escolha).all()
        
        # Busca RECADOS para esta semana específica
        recados_semana = Recado.query.filter(
            Recado.ativo == True,
            or_(
                Recado.para_todas_semanas == True,  # Recados globais
                Recado.semana_id == semana.id       # Recados específicos desta semana
            ),
            or_(
                Recado.data_expiracao.is_(None),
                Recado.data_expiracao >= hoje
            )
        ).order_by(Recado.importante.desc(), Recado.data_publicacao.desc()).all()
        
        # Busca PIX para esta semana específica
        pix_semana = PixInfo.query.filter(
            PixInfo.ativo == True,
            or_(
                PixInfo.para_todas_semanas == True,  # PIX globais
                PixInfo.semana_id == semana.id       # PIX específicos desta semana
            )
        ).all()
        
        # Estatísticas da semana
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
        
        semanas_com_info.append({
            'semana': semana,
            'confirmacoes': confirmacoes_dict,
            'times': times_da_semana,
            'lista_espera': lista_espera,
            'total_confirmados': total_confirmados,
            'mensalistas_confirmados': mensalistas_confirmados,
            'recados': recados_semana,      # RECADOS ESPECÍFICOS
            'pix_infos': pix_semana         # PIX ESPECÍFICOS
        })
    
    # Busca recados e PIX globais para compatibilidade
    recados_globais = Recado.query.filter_by(ativo=True, para_todas_semanas=True).filter(
        or_(
            Recado.data_expiracao.is_(None),
            Recado.data_expiracao >= hoje
        )
    ).order_by(Recado.importante.desc(), Recado.data_publicacao.desc()).all()
    
    pix_globais = PixInfo.query.filter_by(ativo=True, para_todas_semanas=True).all()
    
    return render_template('index.html',
                         semanas_com_info=semanas_com_info,
                         jogadores=jogadores,
                         recados=recados_globais,      # Recados globais (fallback)
                         pix_infos=pix_globais,        # PIX globais (fallback)
                         hoje=hoje)

@app.route('/capitao')
@capitao_required
def capitao_dashboard():
    """PAINEL DO CAPITÃO - ATUALIZADO PARA MÚLTIPLAS SEMANAS"""
    # Aceita semana_id como parâmetro
    semana_id = request.args.get('semana_id', type=int)
    
    if semana_id:
        semana = Semana.query.get(semana_id)
        if not semana:
            flash('Semana não encontrada!', 'danger')
            semana = get_semana_atual()
    else:
        semana = get_semana_atual()
    
    # Busca semanas disponíveis para este capitão (próximas 30 dias)
    hoje = date.today()
    semanas_disponiveis = Semana.query.filter(
        Semana.data >= hoje,
        Semana.data <= hoje + timedelta(days=30)
    ).order_by(Semana.data).all()
    
    # Busca time do capitão (se houver draft)
    time = None
    draft_status = None
    minha_vez = False
    jogadores_disponiveis = []
    minhas_escolhas = []
    times = []
    
    if semana.draft_em_andamento or semana.draft_finalizado:
        # Busca time do capitão PARA ESTA SEMANA
        time = Time.query.filter_by(
            semana_id=semana.id,
            capitao_id=current_user.jogador_id
        ).first()
        
        if not time:
            flash('Você não é capitão no draft desta semana!', 'warning')
            # Permite acesso mesmo assim, mas mostra mensagem
            time = Time(semana_id=semana.id, capitao_id=current_user.jogador_id, nome=f"Time {current_user.jogador.nome}")
        else:
            # Busca status do draft DESTA SEMANA
            draft_status = DraftStatus.query.filter_by(semana_id=semana.id).first()
            
            # Verifica se é a vez deste capitão
            if draft_status and draft_status.vez_capitao_id:
                minha_vez = draft_status.vez_capitao_id == current_user.jogador_id
            
            # Busca jogadores disponíveis (apenas se draft em andamento)
            if semana.draft_em_andamento:
                jogadores_disponiveis = get_jogadores_disponiveis_draft(semana)
            
            # Busca escolhas do time DESTA SEMANA
            minhas_escolhas = EscolhaDraft.query.filter_by(
                semana_id=semana.id,
                time_id=time.id
            ).order_by(EscolhaDraft.ordem_escolha).all()
            
            # Busca todos os times DESTA SEMANA
            times = Time.query.filter_by(semana_id=semana.id).order_by(Time.ordem_escolha).all()
    
    return render_template('capitao/dashboard.html',
                         semana=semana,
                         semanas_disponiveis=semanas_disponiveis,  # NOVO
                         time=time,
                         draft_status=draft_status,
                         minha_vez=minha_vez,
                         jogadores_disponiveis=jogadores_disponiveis,
                         minhas_escolhas=minhas_escolhas,
                         times=times)

@app.route('/jogador/<int:id>')
def ver_jogador(id):
    """VER PERFIL DE JOGADOR - ESTAVA FALTANDO"""
    jogador = Jogador.query.get_or_404(id)
    
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

@app.route('/confirmar_presenca', methods=['POST'])
def confirmar_presenca():
    """Confirmar presença - PÚBLICO (com código) ou ADMIN (sem código)"""
    semana_id = request.form.get('semana_id', type=int)
    
    if semana_id:
        semana = Semana.query.get(semana_id)
    else:
        semana = get_semana_atual()
    
    if not semana:
        return jsonify({'success': False, 'message': 'Semana não encontrada!'})
    
    if not semana.lista_aberta:
        return jsonify({'success': False, 'message': 'Lista de presença está fechada!'})
    
    jogador_id = request.form.get('jogador_id', type=int)
    confirmar = request.form.get('confirmar') == 'true'
    codigo = request.form.get('codigo', '')  # Código de acesso para público
    
    jogador = Jogador.query.get(jogador_id)
    if not jogador or not jogador.ativo:
        return jsonify({'success': False, 'message': 'Jogador não encontrado ou inativo!'})
    
    # VERIFICAÇÃO DE PERMISSÕES CORRIGIDA:
    
    # 1. Admin pode confirmar qualquer um (SEM código)
    if current_user.is_authenticated and current_user.role == 'admin':
        # Admin tem permissão total, não precisa de verificação adicional
        pass
    
    # 2. Usuário logado comum só pode confirmar seu próprio jogador
    elif current_user.is_authenticated:
        if not current_user.jogador_id or current_user.jogador_id != jogador_id:
            return jsonify({'success': False, 'message': 'Você só pode confirmar sua própria presença!'})
    
    # 3. Usuário NÃO logado precisa do código de acesso
    else:
        # Verifica código de acesso
        config_global = ConfiguracaoGlobal.query.first()
        senha_correta = config_global.senha_visitante if config_global else 'volei123'
        
        if codigo != senha_correta:
            return jsonify({'success': False, 'message': 'Código de acesso inválido! Faça login ou use o código correto.'})
    
    # Busca ou cria confirmação
    confirmacao = Confirmacao.query.filter_by(
        jogador_id=jogador_id,
        semana_id=semana.id
    ).first()
    
    if not confirmacao:
        # Define prioridade automática
        prioridade = 2 if jogador.capitao else (1 if jogador.mensalista else 0)
        
        confirmacao = Confirmacao(
            jogador_id=jogador_id,
            semana_id=semana.id,
            confirmado=confirmar,
            confirmado_em=datetime.utcnow() if confirmar else None,
            prioridade=prioridade
        )
        db.session.add(confirmacao)
    else:
        confirmacao.confirmado = confirmar
        confirmacao.confirmado_em = datetime.utcnow() if confirmar else None
    
    db.session.commit()
    
    mensagem = 'Presença confirmada!' if confirmar else 'Presença removida!'
    return jsonify({'success': True, 'message': mensagem})

@app.route('/admin/confirmar_jogador/<int:jogador_id>/<int:semana_id>')
@admin_required
def admin_confirmar_jogador(jogador_id, semana_id):
    """Admin confirma/desconfirma jogador rapidamente"""
    semana = Semana.query.get_or_404(semana_id)
    jogador = Jogador.query.get_or_404(jogador_id)
    
    confirmacao = Confirmacao.query.filter_by(
        jogador_id=jogador_id,
        semana_id=semana_id
    ).first()
    
    if confirmacao:
        # Alterna status
        confirmacao.confirmado = not confirmacao.confirmado
        confirmacao.confirmado_em = datetime.utcnow() if confirmacao.confirmado else None
    else:
        # Cria nova confirmação
        prioridade = 2 if jogador.capitao else (1 if jogador.mensalista else 0)
        confirmacao = Confirmacao(
            jogador_id=jogador_id,
            semana_id=semana_id,
            confirmado=True,
            confirmado_em=datetime.utcnow(),
            prioridade=prioridade
        )
        db.session.add(confirmacao)
    
    db.session.commit()
    
    flash(f'{jogador.nome} {"confirmado" if confirmacao.confirmado else "desconfirmado"}!', 'success')
    return redirect(url_for('admin_dashboard', semana_id=semana_id))


# ======================================================
# FUNÇÕES PARA GESTÃO DE MENSALIDADES (NOVAS)
# ======================================================

def get_dia_semana(numero_dia):
    """Retorna o nome do dia da semana"""
    dias = [
        'Segunda-feira',
        'Terça-feira', 
        'Quarta-feira',
        'Quinta-feira',
        'Sexta-feira',
        'Sábado',
        'Domingo'
    ]
    return dias[numero_dia] if 0 <= numero_dia < len(dias) else 'Desconhecido'

def get_dia_semana_curto(numero_dia):
    """Retorna o nome curto do dia da semana"""
    dias_curto = [
        'Seg',
        'Ter',
        'Qua', 
        'Qui',
        'Sex',
        'Sáb',
        'Dom'
    ]
    return dias_curto[numero_dia] if 0 <= numero_dia < len(dias_curto) else '??'

def calcular_proximo_ciclo_mensalidade():
    """Calcula automaticamente o próximo ciclo de mensalidade baseado na configuração"""
    config_global = ConfiguracaoGlobal.query.first()
    duracao = config_global.duracao_mensalidade_dias if config_global else 30
    
    hoje = date.today()
    
    # Verifica se há um ciclo ativo
    ultima_mensalidade = db.session.query(
        func.max(Jogador.data_fim_mensalidade)
    ).filter(
        Jogador.mensalista == True,
        Jogador.mensalidade_paga == True
    ).scalar()
    
    if ultima_mensalidade and ultima_mensalidade >= hoje:
        # Usa a data de fim mais recente como base
        data_inicio = ultima_mensalidade + timedelta(days=1)
    else:
        # Começa de hoje
        data_inicio = hoje
    
    data_fim = data_inicio + timedelta(days=duracao - 1)  # -1 para incluir o último dia
    
    return data_inicio, data_fim

def verificar_e_atualizar_mensalidades():
    """Verifica e atualiza status das mensalidades automaticamente"""
    hoje = date.today()
    mensalistas = Jogador.query.filter_by(mensalista=True, ativo=True).all()
    
    atualizados = 0
    vencidos = 0
    
    for jogador in mensalistas:
        # Se a mensalidade está vencida e não foi paga
        if jogador.data_fim_mensalidade and jogador.data_fim_mensalidade < hoje:
            if not jogador.mensalidade_paga:
                jogador.mensalista = False
                jogador.mensalidade_paga = False
                vencidos += 1
                print(f"⚠️ Jogador {jogador.nome} removido de mensalista - mensalidade vencida")
            else:
                # Se foi paga, mantém como mensalista mas marca como não paga para novo ciclo
                jogador.mensalidade_paga = False
                atualizados += 1
        
        # Se não tem data de fim, cria uma baseada na data de início
        elif jogador.mensalidade_paga and jogador.data_inicio_mensalidade and not jogador.data_fim_mensalidade:
            config_global = ConfiguracaoGlobal.query.first()
            duracao = config_global.duracao_mensalidade_dias if config_global else 30
            jogador.data_fim_mensalidade = jogador.data_inicio_mensalidade + timedelta(days=duracao - 1)
            atualizados += 1
    
    db.session.commit()
    return atualizados, vencidos

def renovar_mensalidade_em_lote(jogadores_ids, data_inicio, data_fim):
    """Renova mensalidade para vários jogadores de uma vez"""
    atualizados = 0
    
    for jogador_id in jogadores_ids:
        jogador = Jogador.query.get(jogador_id)
        if jogador and jogador.ativo:
            jogador.mensalista = True
            jogador.mensalidade_paga = True
            jogador.data_inicio_mensalidade = data_inicio
            jogador.data_fim_mensalidade = data_fim
            atualizados += 1
    
    db.session.commit()
    return atualizados

def obter_ciclo_atual_mensalidade():
    """Obtém o ciclo atual de mensalidade ativa - CORRIGIDA E MELHORADA"""
    hoje = date.today()
    
    # Busca TODOS os mensalistas pagos com data de fim futura
    mensalistas_pagos = Jogador.query.filter(
        Jogador.mensalista == True,
        Jogador.mensalidade_paga == True,
        Jogador.ativo == True,
        Jogador.data_fim_mensalidade.isnot(None),
        Jogador.data_fim_mensalidade >= hoje
    ).all()
    
    if not mensalistas_pagos:
        # Se não há mensalistas pagos, busca o ciclo configurado
        config_global = ConfiguracaoGlobal.query.first()
        duracao = config_global.duracao_mensalidade_dias if config_global else 30
        
        # Tenta encontrar uma data de início baseada em mensalistas ativos
        ultima_mensalidade = db.session.query(
            func.max(Jogador.data_fim_mensalidade)
        ).filter(
            Jogador.mensalista == True,
            Jogador.ativo == True,
            Jogador.data_fim_mensalidade.isnot(None)
        ).scalar()
        
        if ultima_mensalidade and ultima_mensalidade >= hoje:
            # Usa a data de fim mais recente como base
            data_inicio = ultima_mensalidade + timedelta(days=1)
            data_fim = data_inicio + timedelta(days=duracao - 1)
            return data_inicio, data_fim, 0
        else:
            # Não há ciclo ativo
            return None, None, 0
    
    # Agrupa por ciclo (início + fim)
    ciclos = {}
    for jogador in mensalistas_pagos:
        if jogador.data_inicio_mensalidade and jogador.data_fim_mensalidade:
            ciclo_key = f"{jogador.data_inicio_mensalidade}_{jogador.data_fim_mensalidade}"
            if ciclo_key in ciclos:
                ciclos[ciclo_key]['count'] += 1
                ciclos[ciclo_key]['jogadores'].append(jogador.nome)
            else:
                ciclos[ciclo_key] = {
                    'inicio': jogador.data_inicio_mensalidade,
                    'fim': jogador.data_fim_mensalidade,
                    'count': 1,
                    'jogadores': [jogador.nome]
                }
    
    if not ciclos:
        return None, None, 0
    
    # Encontra o ciclo mais comum (com mais jogadores)
    ciclo_mais_comum = max(ciclos.values(), key=lambda x: x['count'])
    
    # DEBUG: Mostra informação sobre os ciclos encontrados
    print(f"Ciclos encontrados: {len(ciclos)}")
    for key, ciclo in ciclos.items():
        print(f"  Ciclo: {ciclo['inicio']} a {ciclo['fim']} ({ciclo['count']} jogadores)")
    print(f"Ciclo mais comum: {ciclo_mais_comum['inicio']} a {ciclo_mais_comum['fim']}")
    
    return ciclo_mais_comum['inicio'], ciclo_mais_comum['fim'], ciclo_mais_comum['count']

def obter_ciclo_das_configuracoes():
    """Obtém o ciclo baseado nas configurações do sistema"""
    # PRIMEIRO: Verifica se há um ciclo ativo na tabela de ciclos
    ciclo_ativa = CicloMensalidade.query.filter_by(ativo=True).order_by(CicloMensalidade.updated_at.desc()).first()
    
    if ciclo_ativa:
        print(f"Ciclo encontrado na tabela: {ciclo_ativa.data_inicio} a {ciclo_ativa.data_fim}")
        return ciclo_ativa.data_inicio, ciclo_ativa.data_fim
    
    # SEGUNDO: Tenta obter o ciclo atual dos mensalistas pagos
    ciclo_inicio, ciclo_fim, _ = obter_ciclo_atual_mensalidade()
    
    if ciclo_inicio and ciclo_fim:
        print(f"Ciclo encontrado nos mensalistas: {ciclo_inicio} a {ciclo_fim}")
        return ciclo_inicio, ciclo_fim
    
    # TERCEIRO: Se não há ciclo, calcula um baseado na configuração
    config_global = ConfiguracaoGlobal.query.first()
    if not config_global:
        return None, None
    
    duracao = config_global.duracao_mensalidade_dias
    hoje = date.today()
    
    # Tenta criar um ciclo padrão começando na primeira segunda-feira do mês atual
    primeiro_dia_mes = hoje.replace(day=1)
    
    # Encontra a primeira segunda-feira do mês
    dias_para_segunda = (7 - primeiro_dia_mes.weekday()) % 7
    data_inicio = primeiro_dia_mes + timedelta(days=dias_para_segunda)
    data_fim = data_inicio + timedelta(days=duracao - 1)
    
    # Verifica se hoje está dentro deste ciclo
    if data_inicio <= hoje <= data_fim:
        print(f"Ciclo calculado para o mês: {data_inicio} a {data_fim}")
        return data_inicio, data_fim
    
    # Se não, cria um ciclo padrão de 30 dias a partir de hoje
    data_inicio = hoje
    data_fim = data_inicio + timedelta(days=duracao - 1)
    
    print(f"Cicro padrão criado: {data_inicio} a {data_fim}")
    return data_inicio, data_fim

def definir_ciclo_manual(data_inicio, data_fim, descricao=None):
    """Define manualmente um ciclo de mensalidade"""
    # Desativa ciclos anteriores
    CicloMensalidade.query.update({'ativo': False})
    
    # Cria novo ciclo
    novo_ciclo = CicloMensalidade(
        data_inicio=data_inicio,
        data_fim=data_fim,
        ativo=True,
        descricao=descricao or f"Ciclo manual: {data_inicio} a {data_fim}"
    )
    db.session.add(novo_ciclo)
    db.session.commit()
    
    print(f"Ciclo manual definido: {data_inicio} a {data_fim}")
    return novo_ciclo


def obter_resumo_mensalidades():
    """Obtém resumo completo das mensalidades"""
    hoje = date.today()  # Use 'hoje' (português) em toda a função
    
    # Total de mensalistas ativos
    total_mensalistas = Jogador.query.filter_by(mensalista=True, ativo=True).count()
    
    # Busca ciclo atual do sistema
    ciclo_inicio, ciclo_fim = obter_ciclo_das_configuracoes()
    
    # Inicializa no_ciclo_atual
    no_ciclo_atual = 0
    
    if ciclo_inicio and ciclo_fim:
        # Jogadores no ciclo atual (datas alinhadas)
        no_ciclo_atual = Jogador.query.filter(
            Jogador.mensalista == True,
            Jogador.ativo == True,
            Jogador.data_inicio_mensalidade == ciclo_inicio,
            Jogador.data_fim_mensalidade == ciclo_fim
        ).count()
        
        # Mensalistas pagos no ciclo atual
        mensalistas_pagos = Jogador.query.filter(
            Jogador.mensalista == True,
            Jogador.mensalidade_paga == True,
            Jogador.ativo == True,
            Jogador.data_inicio_mensalidade == ciclo_inicio,
            Jogador.data_fim_mensalidade == ciclo_fim
        ).count()
    else:
        # Se não há ciclo ativo
        ciclo_inicio = None
        ciclo_fim = None
        
        # Mensalistas pagos com data futura
        mensalistas_pagos = Jogador.query.filter(
            Jogador.mensalista == True,
            Jogador.mensalidade_paga == True,
            Jogador.ativo == True,
            Jogador.data_fim_mensalidade >= hoje  # CORRIGIDO: use 'hoje'
        ).count()
    
    # Mensalistas vencidos (data vencida, independente de pagamento)
    mensalistas_vencidos = Jogador.query.filter(
        Jogador.mensalista == True,
        Jogador.ativo == True,
        Jogador.data_fim_mensalidade < hoje  # CORRIGIDO: use 'hoje'
    ).count()
    
    # Mensalistas pendentes (não pagos mas ainda no prazo)
    mensalistas_pendentes = Jogador.query.filter(
        Jogador.mensalista == True,
        Jogador.mensalidade_paga == False,
        Jogador.data_fim_mensalidade >= hoje,  # CORRIGIDO: use 'hoje'
        Jogador.ativo == True
    ).count()
    
    # Próximo vencimento mais próximo
    proximo_vencimento = db.session.query(
        func.min(Jogador.data_fim_mensalidade)
    ).filter(
        Jogador.mensalista == True,
        Jogador.ativo == True,
        Jogador.data_fim_mensalidade >= hoje  # CORRIGIDO: use 'hoje'
    ).scalar()
    
    return {
        'total_mensalistas': total_mensalistas,
        'mensalistas_pagos': mensalistas_pagos,
        'mensalistas_pendentes': mensalistas_pendentes,
        'mensalistas_vencidos': mensalistas_vencidos,
        'proximo_vencimento': proximo_vencimento,
        'ciclo_atual_inicio': ciclo_inicio,
        'ciclo_atual_fim': ciclo_fim,
        'no_ciclo_atual': no_ciclo_atual
    }   

@app.route('/api/dashboard/estatisticas')
@admin_required
def api_dashboard_estatisticas():
    """API para estatísticas do dashboard admin"""
    # Resumo de mensalidades
    resumo_mensalidades = obter_resumo_mensalidades()
    
    # Total de jogadores
    total_jogadores = Jogador.query.filter_by(ativo=True).count()
    
    # Total de mensalistas
    total_mensalistas = Jogador.query.filter_by(mensalista=True, ativo=True).count()
    
    # Total de capitães
    total_capitaes = Jogador.query.filter_by(capitao=True, ativo=True).count()
    
    # Semana atual (para confirmações)
    semana = get_semana_atual()
    confirmados = Confirmacao.query.filter_by(
        semana_id=semana.id,
        confirmado=True
    ).count()
    
    return jsonify({
        'success': True,
        'mensalidades': {
            'ativas': resumo_mensalidades['mensalistas_pagos'],
            'total': resumo_mensalidades['total_mensalistas'],
            'pendentes': resumo_mensalidades['mensalistas_pendentes'],
            'vencidas': resumo_mensalidades['mensalistas_vencidos'],
            'ciclo_atual': {
                'inicio': resumo_mensalidades['ciclo_atual_inicio'].isoformat() 
                    if resumo_mensalidades['ciclo_atual_inicio'] else None,
                'fim': resumo_mensalidades['ciclo_atual_fim'].isoformat() 
                    if resumo_mensalidades['ciclo_atual_fim'] else None
            }
        },
        'jogadores': total_jogadores,
        'mensalistas': total_mensalistas,
        'capitaes': total_capitaes,
        'confirmados_hoje': confirmados
    })       

@app.route('/admin/limpar_config_dias')
@admin_required
def limpar_config_dias():
    """Limpa a configuração de dias da semana"""
    config = ConfiguracaoGlobal.query.first()
    if config:
        config.dias_semana_fixos = ''
        config.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Configuração de dias limpa! Configure novamente.', 'info')
    return redirect(url_for('admin_configuracoes'))

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
    # Cria todas as tabelas do banco de dados se ainda não existirem
    db.create_all()
    
    # Cria usuário admin padrão
    criar_admin_padrao()

    # Cria configurações globais se não existirem
    if not ConfiguracaoGlobal.query.first():
        config = ConfiguracaoGlobal(
            dias_semana_fixos='2,4,5',  # Quarta, sexta, sábado (0=segunda, 6=domingo)
            senha_visitante='volei123',
            duracao_mensalidade_dias=30
        )
        db.session.add(config)
        db.session.commit()
        print('✅ Configurações globais criadas')

    # Cria pasta de uploads se não existir
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Cria semanas automáticas apenas se não houver nenhuma semana no banco
    if not Semana.query.first():
        criar_semanas_automaticas()
        print('✅ Semanas automáticas criadas')

    # Busca semana atual, não criando novas se já existirem
    get_semana_atual()

    print('✅ Sistema inicializado com sucesso!')

    

# ======================================================
# EXECUÇÃO
# ======================================================

if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=False
    )
