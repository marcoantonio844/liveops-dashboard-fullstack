🚀 Painel de Controlo LiveOps (Full-Stack)

Um dashboard analítico completo para monitoramento de operações em tempo real, construído com Python (FastAPI), React e MongoDB.

Este projeto demonstra um pipeline de dados completo, desde a simulação de eventos até à visualização de Business Intelligence (BI) e deteção de anomalias por IA, protegido por autenticação JWT.

🔗 Link da Aplicação (Deploy):

Frontend (Dashboard): [EM BREVE - Link do Vercel]

Backend (API Docs): [EM BREVE - Link do Render]

(Nota: O backend está protegido. Para testar a aplicação "ao vivo", é necessário criar uma conta na página de registo.)

✨ Funcionalidades Principais

Este dashboard não é apenas uma "cara bonita"; ele é um sistema de análise de dados complexo com várias funcionalidades de nível profissional:

Backend (FastAPI & MongoDB)

API Segura: Endpoints protegidos com autenticação JWT (Tokens).

Autenticação: Sistema completo de Registo (com hashing de senhas bcrypt) e Login.

Base de Dados: Persistência de todos os eventos num cluster MongoDB Atlas (na nuvem).

Tempo Real (Push): Utiliza WebSockets para "empurrar" dados ao vivo para todos os utilizadores conectados.

Motor de BI: Endpoints de agregação complexos ($facet, $group, $match) que calculam KPIs históricos diretamente no MongoDB.

Deteção de Anomalias (IA): Um worker que monitoriza o fluxo de eventos e dispara alertas (via WebSocket) se um pico de erros é detetado.

Frontend (React)

Design Moderno: UI "Premium" responsiva, construída com CSS puro num tema dark mode.

Gestão de Estado: Controlo de autenticação global através de React Context e localStorage.

Navegação: Múltiplas páginas (Login, Dashboard) geridas com React Router.

Visualização de Dados (BI):

KPIs históricos (Receita 24h, Pedidos, Erros) com auto-refresh (Polling).

Gráfico de barras histórico (Vendas por Hora).

Gráfico de pizza (Top 5 Produtos).

Visualização em Tempo Real (WebSockets):

Gráfico de linha dinâmico (Últimas 20 Vendas).

Gráfico de barras dinâmico (Erros por Região).

Feed de eventos ao vivo.

Interatividade Total (UX):

Filtros: Clicar num gráfico (Erros por Região) filtra o Feed de Eventos.

"Drill-Down": Clicar num user_id no feed abre um pop-up (Modal) com o histórico completo daquele utilizador.

🛠️ Tecnologias Utilizadas

Categoria

Tecnologia

Frontend

React (Hooks, Context), React Router, Recharts

Backend

Python 3, FastAPI, Uvicorn

Base de Dados

MongoDB (com MongoDB Atlas)

Tempo Real

WebSockets

Autenticação

JWT (Tokens), Passlib (bcrypt)

Simulador

Python (Requests)

🚀 Como Executar Localmente

Pré-requisitos:

Python 3.10+

Node.js 18+

Uma conta gratuita no MongoDB Atlas

1. Backend (Terminal 1)

# Navegue para a pasta backend
cd backend

# Crie e ative um ambiente virtual
python -m venv venv
.\venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt 
# (Nota: Teríamos de criar um requirements.txt, mas por agora está OK)

# Defina a sua chave secreta do MongoDB (PowerShell)
$env:MONGO_CONNECTION_URL="SUA_STRING_DE_CONEXAO_DO_ATLAS_AQUI"

# Rode o servidor
uvicorn main:app --reload --port 8000


2. Frontend (Terminal 2)

# Navegue para a pasta frontend
cd frontend

# Instale as dependências
npm install

# Rode o servidor de desenvolvimento
npm run dev


3. Simulador (Terminal 3)
O simulador só funciona se o Backend estiver a funcionar e se você criar um utilizador (ex: 'admin'/'1234') e atualizar as credenciais no simulador.py.

# Navegue para a pasta principal
cd .. 

# Ative o venv do backend (para usar o 'requests')
.\backend\venv\Scripts\activate

# Rode o simulador
python simulador.py
