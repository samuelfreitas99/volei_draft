# migrate.py
import os
import sys
from app import app, db
from models import Recado, PixInfo

def migrate_database():
    """Adiciona colunas para recados e PIX por semana"""
    with app.app_context():
        print("🔄 Iniciando migração do banco de dados...")
        
        # Adiciona colunas à tabela Recado
        try:
            print("📝 Adicionando colunas à tabela Recado...")
            db.engine.execute('''
                ALTER TABLE recado 
                ADD COLUMN para_todas_semanas BOOLEAN DEFAULT 1;
            ''')
            db.engine.execute('''
                ALTER TABLE recado 
                ADD COLUMN semana_id INTEGER REFERENCES semana(id);
            ''')
            print("✅ Colunas adicionadas à tabela Recado")
        except Exception as e:
            print(f"⚠️  Aviso ao adicionar colunas à Recado: {e}")
        
        # Adiciona colunas à tabela PixInfo
        try:
            print("💰 Adicionando colunas à tabela PixInfo...")
            db.engine.execute('''
                ALTER TABLE pix_info 
                ADD COLUMN para_todas_semanas BOOLEAN DEFAULT 1;
            ''')
            db.engine.execute('''
                ALTER TABLE pix_info 
                ADD COLUMN semana_id INTEGER REFERENCES semana(id);
            ''')
            print("✅ Colunas adicionadas à tabela PixInfo")
        except Exception as e:
            print(f"⚠️  Aviso ao adicionar colunas à PixInfo: {e}")
        
        # Atualiza registros existentes
        try:
            print("🔄 Atualizando registros existentes...")
            
            # Recados existentes: marcar como para todas as semanas
            db.engine.execute('''
                UPDATE recado 
                SET para_todas_semanas = 1
                WHERE para_todas_semanas IS NULL;
            ''')
            
            # PIX existentes: marcar como para todas as semanas
            db.engine.execute('''
                UPDATE pix_info 
                SET para_todas_semanas = 1
                WHERE para_todas_semanas IS NULL;
            ''')
            
            print("✅ Registros atualizados")
            
        except Exception as e:
            print(f"⚠️  Aviso ao atualizar registros: {e}")
        
        print("🎉 Migração concluída com sucesso!")

if __name__ == '__main__':
    migrate_database()