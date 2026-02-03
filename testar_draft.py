#!/usr/bin/env python3
# test_draft.py

import sys
import os

# Configurar ambiente antes de importar o app
os.environ['DATABASE_URL'] = 'sqlite:///instance/volei_draft.db'

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Semana, Time, Confirmacao, Jogador, DraftStatus, EscolhaDraft

def testar_draft_semana(semana_id=4):
    """Testa se pode iniciar draft para uma semana"""
    with app.app_context():
        print(f"🔍 Testando semana {semana_id}")
        
        semana = Semana.query.get(semana_id)
        if not semana:
            print(f"❌ Semana {semana_id} não encontrada")
            return
        
        print(f"📅 Semana: {semana.data}")
        print(f"📊 Status: lista_aberta={semana.lista_aberta}, draft_em_andamento={semana.draft_em_andamento}, draft_finalizado={semana.draft_finalizado}")
        
        # Times
        times = Time.query.filter_by(semana_id=semana.id).all()
        print(f"\n🏀 Times definidos: {len(times)}")
        for i, time in enumerate(times, 1):
            capitao = Jogador.query.get(time.capitao_id)
            print(f"  {i}. {time.nome}: Capitão '{capitao.nome if capitao else 'Nenhum'}' (ID: {time.capitao_id})")
            
            # Verificar se capitão tem escolha no draft
            escolha = EscolhaDraft.query.filter_by(
                semana_id=semana.id,
                jogador_id=time.capitao_id
            ).first()
            print(f"     Tem escolha no draft: {'✅' if escolha else '❌'}")
        
        # Confirmações
        confirmados = Confirmacao.query.filter_by(
            semana_id=semana.id,
            confirmado=True
        ).count()
        print(f"\n👥 Jogadores confirmados: {confirmados}")
        
        # Verificação para iniciar draft
        if len(times) >= 2:
            necessario = len(times) * 6  # 6 jogadores por time
            print(f"\n📋 Verificação:")
            print(f"   Times: {len(times)}")
            print(f"   Jogadores por time: 6")
            print(f"   Necessário total: {necessario}")
            print(f"   Confirmados: {confirmados}")
            
            if confirmados >= necessario:
                print(f"\n✅ PRONTO para iniciar draft!")
                return True
            else:
                print(f"\n❌ FALTAM jogadores")
                print(f"   Faltam: {necessario - confirmados} jogadores")
                return False
        else:
            print(f"\n❌ FALTAM times (mínimo 2)")
            print(f"   Times atuais: {len(times)}")
            return False

def simular_iniciar_draft(semana_id=4):
    """Simula a inicialização do draft"""
    with app.app_context():
        print(f"\n🎮 Simulando início do draft para semana {semana_id}")
        
        semana = Semana.query.get(semana_id)
        
        # Verificar status atual do draft
        draft_status = DraftStatus.query.filter_by(semana_id=semana.id).first()
        if draft_status:
            print(f"⚠️ Já existe um DraftStatus para esta semana")
            print(f"   Finalizado: {draft_status.finalizado}")
            print(f"   Vez do capitão: {draft_status.vez_capitao_id}")
        
        # Limpar dados de draft existentes (como a função faz)
        print(f"\n🧹 Limpando dados do draft anterior...")
        EscolhaDraft.query.filter_by(semana_id=semana.id).delete()
        DraftStatus.query.filter_by(semana_id=semana.id).delete()
        
        print("✅ Dados anteriores removidos")
        
        # Verificar se temos times suficientes
        times = Time.query.filter_by(semana_id=semana.id).all()
        if len(times) < 2:
            print(f"❌ É necessário pelo menos 2 times definidos! Times encontrados: {len(times)}")
            return
        
        # Verificar se todos os times têm capitão
        for time in times:
            if not time.capitao_id:
                print(f"❌ Time {time.nome} não tem capitão definido!")
                return
        
        # Verificar número total de jogadores
        total_necessario = len(times) * 6
        confirmados = Confirmacao.query.filter_by(
            semana_id=semana.id,
            confirmado=True
        ).count()
        
        if confirmados < total_necessario:
            print(f"❌ É necessário pelo menos {total_necessario} jogadores confirmados! Confirmados: {confirmados}")
            return
        
        print(f"\n✅ Tudo OK! Pode iniciar draft com:")
        print(f"   Times: {len(times)}")
        print(f"   Jogadores confirmados: {confirmados}")
        print(f"   Jogadores necessários: {total_necessario}")

if __name__ == "__main__":
    # Testar se pode iniciar draft
    pode_iniciar = testar_draft_semana(4)
    
    if pode_iniciar:
        # Simular início do draft
        simular_iniciar_draft(4)
    else:
        print("\n❌ Não pode iniciar draft - verifique os problemas acima")