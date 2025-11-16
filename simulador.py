import requests
import time
import random
from datetime import datetime
import json

# --- 1. Configurações ---
API_URL = "http://127.0.0.1:8000" # Usar 127.0.0.1 para consistência
BACKEND_URL_TOKEN = f"{API_URL}/auth/token"
BACKEND_URL_EVENT = f"{API_URL}/api/event"

# --- 2. NOVO: Credenciais de Login ---
# Use o utilizador e senha que você acabou de registar no site
SIMULATOR_USER = "admin"
SIMULATOR_PASS = "1234" # Mude se você usou uma senha diferente

# Listas de dados (sem mudanças)
EVENT_TYPES = ["page_view", "add_to_cart", "remove_from_cart", "checkout_start", "payment_error", "purchase_complete", "user_login", "user_logout"]
PRODUCTS = [
    {"id": "P001", "name": "Smartwatch XYZ", "price": 299.99},
    {"id": "P002", "name": "Fone Bluetooth Mega", "price": 149.50},
    {"id": "P003", "name": "Carregador Portátil 10000mAh", "price": 75.00},
    {"id": "P004", "name": "Câmera de Segurança HD", "price": 350.00},
    {"id": "P005", "name": "Mouse Gamer Óptico", "price": 120.00},
    {"id": "P006", "name": "Teclado Mecânico RGB", "price": 400.00},
    {"id": "P007", "name": "Monitor Ultrawide 27'", "price": 1200.00},
    {"id": "P008", "name": "Webcam Full HD", "price": 99.00},
    {"id": "P009", "name": "Headset Gamer Pro", "price": 250.00},
    {"id": "P010", "name": "Placa de Vídeo RTX3060", "price": 2500.00},
]
REGIONS = ["São Paulo", "Rio de Janeiro", "Belo Horizonte", "Porto Alegre", "Curitiba", "Salvador", "Fortaleza", "Brasília"]

# --- 3. NOVO: Função de Login ---
def get_auth_token():
    """Faz login no backend e obtém um token de acesso."""
    print(f"A autenticar o simulador como '{SIMULATOR_USER}'...")
    
    # O backend espera dados de formulário (x-www-form-urlencoded)
    login_data = {
        'username': SIMULATOR_USER,
        'password': SIMULATOR_PASS
    }
    
    try:
        response = requests.post(BACKEND_URL_TOKEN, data=login_data, timeout=5)
        
        if response.status_code == 200:
            token_data = response.json()
            print("Autenticação bem-sucedida!")
            return token_data['access_token']
        else:
            print(f"Erro ao autenticar: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("Erro de conexão ao tentar autenticar. O backend está a funcionar?")
        return None
    except Exception as e:
        print(f"Erro inesperado no login: {e}")
        return None

# --- 4. Geração de Eventos (sem mudanças) ---
def generate_user_id():
    return f"user_{random.randint(1000, 9999)}"

def generate_event():
    event_type = random.choice(EVENT_TYPES)
    user_id = generate_user_id()
    timestamp = datetime.utcnow().isoformat() + "Z"
    event_data = {"user_id": user_id, "timestamp": timestamp, "event_type": event_type, "metadata": {}}
    if event_type in ["add_to_cart", "remove_from_cart", "purchase_complete"]:
        product = random.choice(PRODUCTS)
        event_data["metadata"]["product_id"] = product["id"]
        event_data["metadata"]["product_name"] = product["name"]
        event_data["metadata"]["price"] = product["price"]
        event_data["metadata"]["quantity"] = random.randint(1, 3)
    if event_type == "purchase_complete":
        event_data["metadata"]["order_id"] = f"ORD{random.randint(100000, 999999)}"
        event_data["metadata"]["total_amount"] = round(product["price"] * event_data["metadata"]["quantity"], 2)
        event_data["metadata"]["region"] = random.choice(REGIONS)
    elif event_type == "payment_error":
        event_data["metadata"]["error_code"] = f"ERR{random.randint(100, 999)}"
        event_data["metadata"]["error_message"] = random.choice(["Cartão Recusado", "Transação Não Autorizada", "Limite Excedido", "Falha de Comunicação"])
        event_data["metadata"]["region"] = random.choice(REGIONS)
    elif event_type == "page_view":
        event_data["metadata"]["page_url"] = random.choice(["/home", "/products", "/cart", "/checkout", "/about"])
        event_data["metadata"]["referrer"] = random.choice(["google", "facebook", "direct", "email"])
    return event_data

# --- 5. Loop Principal (ATUALIZADO com Token) ---
def run_simulator(token: str):
    """Roda o simulador usando o token de acesso."""
    print(f"Simulador de eventos iniciado. A enviar para {BACKEND_URL_EVENT}")
    
    # --- MUDANÇA: Cria o cabeçalho de autorização ---
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        while True:
            event = generate_event()
            try:
                # --- MUDANÇA: Envia o cabeçalho em cada pedido ---
                response = requests.post(BACKEND_URL_EVENT, json=event, headers=headers, timeout=1)
                
                if response.status_code == 200:
                    pass
                elif response.status_code == 401:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Erro 401: Token expirou ou é inválido. A parar simulador.")
                    break # Para o loop
                else:
                    print(f"Erro ao enviar evento: {response.status_code} - {response.text}")
            
            except requests.exceptions.ConnectionError:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Erro de conexão: O backend pode não estar a funcionar.")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Ocorreu um erro inesperado: {e}")

            time.sleep(random.uniform(0.5, 1.5))

    except KeyboardInterrupt:
        print("\nSimulador parado pelo utilizador.")

# --- 6. Ponto de Entrada (ATUALIZADO) ---
if __name__ == "__main__":
    # 1. Primeiro, faz login
    access_token = get_auth_token()
    
    # 2. Se o login funcionar, começa a simulação
    if access_token:
        run_simulator(access_token)
    else:
        print("Não foi possível obter o token. O simulador não vai arrancar.")