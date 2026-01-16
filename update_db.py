import os
import sys
from datetime import date, datetime

# Adiciona o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Jogador, User, Semana, Confirmacao, Time, EscolhaDraft, DraftStatus, ListaEspera, HistoricoDraft
from werkzeug.security import generate_password_hash

def atualizar_banco():
    """Atualiza o banco de dados com as novas colunas"""
    with app.app_context():
        # Verifica se o banco já existe
        db_file = 'volei_draft.db'
        
        try:
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tabelas_existentes = inspector.get_table_names()
            
            print("📊 Tabelas existentes:", tabelas_existentes)
            
            if 'jogador' in tabelas_existentes:
                # Verifica colunas da tabela Jogador
                jogador_columns = [col['name'] for col in inspector.get_columns('jogador')]
                print("📋 Colunas da tabela Jogador:", jogador_columns)
                
                # Verifica se faltam colunas
                colunas_necessarias = ['altura', 'data_nascimento', 'cidade']
                colunas_faltantes = [col for col in colunas_necessarias if col not in jogador_columns]
                
                if colunas_faltantes:
                    print(f"⚠️  Colunas faltantes na tabela Jogador: {colunas_faltantes}")
                    print("⚠️  É necessário recriar o banco para adicionar as novas colunas.")
                    
                    resposta = input("Deseja recriar o banco? (S/N): ")
                    if resposta.upper() == 'S':
                        db.drop_all()
                        db.create_all()
                        print("✅ Banco recriado com todas as tabelas e colunas")
                    else:
                        print("⚠️  Continuando com o banco existente. Algumas funcionalidades podem não funcionar.")
                else:
                    print("✅ Todas as colunas necessárias já existem!")
            else:
                # Banco não existe ou está vazio, cria todas as tabelas
                db.create_all()
                print("✅ Banco de dados criado com todas as tabelas")
                
        except Exception as e:
            print(f"❌ Erro ao verificar banco: {e}")
            print("🔄 Criando novo banco de dados...")
            if os.path.exists(db_file):
                os.remove(db_file)
                print("✅ Banco de dados antigo removido")
            
            db.create_all()
        
        # Cria admin padrão se não existir
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password=generate_password_hash('admin123'),
                email='admin@volei.com',
                role='admin'
            )
            db.session.add(admin)
            print("✅ Usuário admin criado")
        
        # Cria uma semana de teste se não existir
        hoje = date.today()
        semana = Semana.query.filter_by(data=hoje).first()
        
        if not semana:
            semana = Semana(
                data=hoje,
                descricao=f'Jogo de Vôlei - {hoje.strftime("%d/%m/%Y")}',
                lista_aberta=True
            )
            db.session.add(semana)
            print(f"✅ Semana criada para {hoje}")
        else:
            print(f"✅ Semana já existe para {hoje}")
        
        # Cria alguns jogadores de exemplo se não existirem
        if Jogador.query.count() == 0:
            jogadores_exemplo = [
                Jogador(nome="João Silva", posicao="levantador", nivel="avancado", mensalista=True, capitao=True, ordem_capitao=1),
                Jogador(nome="Maria Santos", posicao="ponteiro", nivel="intermediario", mensalista=True, capitao=True, ordem_capitao=2),
                Jogador(nome="Pedro Oliveira", posicao="central", nivel="avancado", mensalista=True, capitao=False),
                Jogador(nome="Ana Costa", posicao="libero", nivel="iniciante", mensalista=False, capitao=False),
                Jogador(nome="Carlos Mendes", posicao="oposto", nivel="intermediario", mensalista=True, capitao=False),
            ]
            
            for jogador in jogadores_exemplo:
                db.session.add(jogador)
            
            print(f"✅ {len(jogadores_exemplo)} jogadores de exemplo criados")
        
        try:
            db.session.commit()
            print("✅ Banco de dados atualizado com sucesso!")
            
            # Mostra estatísticas
            print("\n📊 Estatísticas:")
            print(f"   Usuários: {User.query.count()}")
            print(f"   Jogadores: {Jogador.query.count()}")
            print(f"   Semanas: {Semana.query.count()}")
            
        except Exception as e:
            print(f"❌ Erro ao salvar alterações: {e}")
            db.session.rollback()

def criar_admin():
    """Cria apenas o usuário admin"""
    with app.app_context():
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password=generate_password_hash('admin123'),
                email='admin@volei.com',
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Usuário admin criado: admin / admin123")
        else:
            print("✅ Usuário admin já existe")

def criar_semana_atual():
    """Cria a semana atual se não existir"""
    with app.app_context():
        hoje = date.today()
        semana = Semana.query.filter_by(data=hoje).first()
        
        if not semana:
            semana = Semana(
                data=hoje,
                descricao=f'Jogo de Vôlei - {hoje.strftime("%d/%m/%Y")}',
                lista_aberta=True
            )
            db.session.add(semana)
            db.session.commit()
            print(f"✅ Semana criada para {hoje}")
        else:
            print(f"✅ Semana já existe para {hoje}")

if __name__ == '__main__':
    print("🔧 Script de Atualização do Banco de Dados")
    print("=" * 50)
    
    print("\nEscolha uma opção:")
    print("1. Atualizar/Criar banco completo")
    print("2. Criar apenas usuário admin")
    print("3. Criar apenas semana atual")
    
    try:
        opcao = int(input("\nOpção (1-3): "))
        
        if opcao == 1:
            atualizar_banco()
        elif opcao == 2:
            criar_admin()
        elif opcao == 3:
            criar_semana_atual()
        else:
            print("❌ Opção inválida!")
            
    except ValueError:
        print("❌ Por favor, digite um número!")
    except KeyboardInterrupt:
        print("\n\n⚠️  Operação cancelada pelo usuário")