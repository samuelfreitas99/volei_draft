import re

# Lê o arquivo app.py
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Encontra todas as funções upload_foto_jogador
pattern = r'@app\.route\(\'/upload_foto_jogador\'.*?\ndef upload_foto_jogador.*?\n    .*?\n'
matches = list(re.finditer(pattern, content, re.DOTALL))

if len(matches) > 1:
    print(f"Encontradas {len(matches)} duplicações da função upload_foto_jogador")
    
    # Mantém apenas a primeira ocorrência
    first_match = matches[0]
    other_matches = matches[1:]
    
    # Remove as duplicações
    for match in reversed(other_matches):
        content = content[:match.start()] + content[match.end():]
    
    # Salva o arquivo corrigido
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Duplicações removidas!")
else:
    print("✅ Nenhuma duplicação encontrada.")