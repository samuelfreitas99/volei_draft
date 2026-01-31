# install.py
import subprocess
import sys

def install_packages():
    packages = [
        "Flask==2.3.3",
        "Flask-SQLAlchemy==3.0.5",
        "Flask-Login==0.6.2",
        "Flask-SocketIO==5.3.4",
        "python-socketio==5.9.0",
        "python-engineio==4.4.1",
        "Werkzeug==2.3.7",
        "Jinja2==3.1.2"
    ]
    
    for package in packages:
        print(f"Instalando {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    
    print("Todas as dependências foram instaladas com sucesso!")

if __name__ == "__main__":
    install_packages()