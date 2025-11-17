import React, { useState, useEffect, useRef } from 'react';
import { format } from 'date-fns';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, BarChart, Bar, Cell,
  PieChart, Pie
} from 'recharts';
import { useAuth } from '../App.jsx';

// --- 1. COMPONENTES DE GRÁFICO (Sem mudanças) ---
const COLORS = ['#ff5555', '#ffb86c', '#f1fa8c', '#8be9fd', '#bd93f9', '#ff79c6', '#50fa7b'];
function SalesChart({ data }) {
  return (
    <div className="chart-container">
      <h3>Últimos 20 Eventos de Venda</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#343536" />
          <XAxis dataKey="name" tick={false} />
          <YAxis stroke="#d7dadc" />
          <Tooltip contentStyle={{ backgroundColor: '#272729', border: '1px solid #343536' }} itemStyle={{ color: '#50fa7b' }} />
          <Legend />
          <Line type="monotone" dataKey="Vendas" stroke="#50fa7b" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 8 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
function ErrorChart({ data, onBarClick }) {
  return (
    <div className="chart-container">
      <h3>Erros por Região (Clique para filtrar)</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} layout="vertical" margin={{ left: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#343536" />
          <XAxis type="number" stroke="#d7dadc" />
          <YAxis dataKey="name" type="category" stroke="#d7dadc" fontSize={12} />
          <Tooltip contentStyle={{ backgroundColor: '#272729', border: '1px solid #343536' }} itemStyle={{ color: '#ff5555' }} />
          <Bar dataKey="Erros" fill="#ff5555" onClick={onBarClick} className="clickable-bar">
            {data.map((entry, index) => (<Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
function HistoricalSalesChart({ data }) {
  return (
    <div className="chart-container">
      <h3>Vendas nas Últimas 24 Horas</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#343536" />
          <XAxis dataKey="name" stroke="#d7dadc" fontSize={12} />
          <YAxis stroke="#d7dadc" />
          <Tooltip 
            contentStyle={{ backgroundColor: '#272729', border: '1px solid #343536' }} 
            itemStyle={{ color: '#50fa7b' }}
          />
          <Bar dataKey="Vendas" fill="#50fa7b" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
function TopProductsChart({ data }) {
  const PIE_COLORS = ['#8be9fd', '#50fa7b', '#f1fa8c', '#ffb86c', '#ff79c6'];
  return (
    <div className="chart-container">
      <h3>Top 5 Produtos (24h)</h3>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80}
            label={(entry) => `${entry.name} (${entry.value})`}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip contentStyle={{ backgroundColor: '#272729', border: '1px solid #343536' }}/>
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

// --- 3. Componentes de Feed e Alerta ---
function AlertBanner({ alertMessage, onDismiss }) {
  if (!alertMessage) return null;
  return (
    <div className="alert-banner">
      <span>
        🚨 <strong style={{fontWeight: 900}}>ALERTA DE ANOMALIA (IA):</strong> {alertMessage}
      </span>
      <button onClick={onDismiss} className="dismiss-button">X</button>
    </div>
  );
}
function EventFeed({ events, regionFilter, onUserClick }) {
  
  const filteredEvents = events.filter(event => {
    if (!regionFilter) return true; 
    return event.metadata && event.metadata.region === regionFilter;
  });
  
  const formatEventData = (event) => {
    const time = new Date(event.timestamp).toLocaleTimeString();
    
    // Torna o UserID um botão
    const userButton = (
      <button 
        onClick={() => onUserClick(event.user_id)} 
        className="user-id-button"
      >
        {event.user_id}
      </button>
    );

    let details;
    if (event.event_type === 'purchase_complete') {
      details = <>-&gt; {event.event_type} (R$ {event.metadata.total_amount.toFixed(2)} em {event.metadata.region})</>;
    } else if (event.event_type === 'payment_error') {
      details = <>-&gt; {event.event_type} ({event.metadata.error_message} em {event.metadata.region})</>;
    } else if (event.event_type === 'add_to_cart') {
      details = <>-&gt; {event.event_type} ({event.metadata.product_name})</>;
    } else if (event.event_type === 'page_view') {
      details = <>-&gt; {event.event_type} ({event.metadata.page_url})</>;
    } else {
      details = <>-&gt; {event.event_type}</>;
    }
    
    return (
      <>
        <span className="feed-time">[{time}]</span>
        {userButton}
        {details}
      </>
    );
  };
  
  const getEventClass = (eventType) => {
    if (eventType === 'IA_ALERT') return 'event-alert';
    if (eventType === 'purchase_complete') return 'event-purchase';
    if (eventType === 'payment_error') return 'event-error';
    if (eventType.includes('cart')) return 'event-cart';
    if (eventType === 'page_view') return 'event-view';
    return 'event-default';
  };
  
  return (
    <div className="feed-container">
      {filteredEvents.length === 0 && regionFilter && (
        <p>Nenhum evento em tempo real para a região: {regionFilter}</p>
      )}
      {filteredEvents.length === 0 && !regionFilter && (
        <p>Aguardando eventos do backend...</p>
      )}
      
      {filteredEvents.map((event, index) => (
        <div key={index} className={`feed-item ${getEventClass(event.event_type)}`}>
          {event.event_type === 'IA_ALERT' ? `🚨 [ALERTA IA] ${event.message}` : formatEventData(event)}
        </div>
      ))}
    </div>
  );
}

// --- 4. Componente de KPIs ---
const formatCurrency = (value) => {
  return (value || 0).toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  });
};
const formatNumber = (value) => {
  return (value || 0).toLocaleString('pt-BR');
};
function KpiCards({ data }) {
  if (!data) {
    return <div className="kpi-container">Carregando KPIs...</div>;
  }
  return (
    <div className="kpi-container">
      <div className="kpi-card sales">
        <span className="kpi-title">Receita (24h)</span>
        <span className="kpi-value">{formatCurrency(data.total_sales)}</span>
      </div>
      <div className="kpi-card orders">
        <span className="kpi-title">Pedidos (24h)</span>
        <span className="kpi-value">{formatNumber(data.total_orders)}</span>
      </div>
      <div className="kpi-card errors">
        <span className="kpi-title">Erros (24h)</span>
        <span className="kpi-value">{formatNumber(data.total_errors)}</span>
      </div>
    </div>
  );
}

// --- 5. NOVO COMPONENTE: O Modal de Histórico (CSS Puro) ---
function UserHistoryModal({ userId, open, onOpenChange, token, logout }) {
  const [history, setHistory] = useState(null); // { summary: [], recent_events: [] }
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || !userId) {
      setHistory(null);
      return;
    }

    const fetchUserHistory = async () => {
      setLoading(true);
      try {
        const data = await fetchWithToken(
          `${API_URL}/api/history/user/${userId}`,
          token,
          logout
        );
        setHistory(data);
      } catch (error) {
        console.error(`Erro ao buscar histórico para ${userId}:`, error.message);
      } finally {
        setLoading(false);
      }
    };

    fetchUserHistory();
  }, [open, userId, token, logout]);

  // Formata o sumário
  const renderSummary = () => {
    if (!history || !history.summary) return null;
    let totalSales = 0;
    let totalErrors = 0;
    history.summary.forEach(item => {
      if (item._id === 'purchase_complete') {
        totalSales = item.total_value || 0;
      }
      if (item._id === 'payment_error') {
        totalErrors = item.count || 0;
      }
    });
    return (
      <div className="user-summary-kpis">
        <div className="kpi-card sales">
          <span className="kpi-title">Receita Total</span>
          <span className="kpi-value">{formatCurrency(totalSales)}</span>
        </div>
        <div className="kpi-card errors">
          <span className="kpi-title">Erros de Pagamento</span>
          <span className="kpi-value">{formatNumber(totalErrors)}</span>
        </div>
      </div>
    );
  };
  
  // Formata a lista de eventos
  const renderRecentEvents = () => {
    if (!history || !history.recent_events || history.recent_events.length === 0) {
      return <p className="modal-text">Nenhum evento recente encontrado para este utilizador.</p>;
    }
    return history.recent_events.map((event, index) => (
      <div key={index} className="modal-event-item">
        <span className="modal-event-time">{format(new Date(event.timestamp), 'dd/MM/yyyy HH:mm:ss')}</span>
        <span className="modal-event-type">{event.event_type}</span>
      </div>
    ));
  };
  
  if (!open) {
    return null;
  }

  // Renderiza o Modal
  return (
    <div className="modal-overlay" onClick={() => onOpenChange(false)}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Histórico do Utilizador</h2>
          <button onClick={() => onOpenChange(false)} className="modal-close-button">X</button>
        </div>
        <p className="modal-desc">A analisar: {userId}</p>
        
        <div className="modal-body">
          {loading && <p className="modal-text">A carregar histórico...</p>}
          {!loading && (
            <>
              {renderSummary()}
              <h4 className="modal-subtitle">Eventos Recentes (Máx. 100)</h4>
              <div className="modal-event-list">
                {renderRecentEvents()}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}


// --- 6. COMPONENTE PRINCIPAL (DashboardPage) ---

const WEBSOCKET_URL = "wss://liveops-dashboard-fullstack.onrender.com/ws/live";
const API_URL = "https://liveops-dashboard-fullstack.onrender.com";

async function fetchWithToken(url, token, logout) {
  const response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  if (response.status === 401) {
    logout();
    throw new Error('Token inválido ou expirado');
  }
  if (!response.ok) {
    throw new Error('Falha na resposta da rede');
  }
  return await response.json();
}

function DashboardPage() {
  // Estados
  const [events, setEvents] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [salesData, setSalesData] = useState([]);
  const [errorData, setErrorData] = useState([]);
  const [iaAlert, setIaAlert] = useState(null);
  const [summaryData, setSummaryData] = useState(null);
  const [hourlySalesData, setHourlySalesData] = useState([]);
  const [topProductsData, setTopProductsData] = useState([]);
  const [regionFilter, setRegionFilter] = useState(null);
  const [selectedUserId, setSelectedUserId] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  // Refs
  const websocket = useRef(null);
  const reconnectTimer = useRef(null);
  const isUnmounting = useRef(false);
  
  const { token, logout } = useAuth();

  // Funções de atualização dos gráficos
  const updateSalesChart = (event) => {
    const time = format(new Date(event.timestamp), 'HH:mm:ss');
    const saleAmount = event.metadata.total_amount;
    setSalesData(currentData => {
      const newData = [...currentData, { name: time, Vendas: saleAmount }];
      if (newData.length > 20) {
        return newData.slice(newData.length - 20);
      }
      return newData;
    });
  };
  const updateErrorChart = (event) => {
    const region = event.metadata.region || "Desconhecida";
    setErrorData(currentData => {
      const newData = [...currentData];
      const regionIndex = newData.findIndex(item => item.name === region);
      if (regionIndex !== -1) {
        const updatedItem = { ...newData[regionIndex], Erros: (newData[regionIndex].Erros || 0) + 1 };
        newData[regionIndex] = updatedItem;
      } else {
        newData.push({ name: region, Erros: 1 });
      }
      return newData.sort((a, b) => b.Erros - a.Erros);
    });
  };
  
  // Funções de clique
  const handleRegionClick = (data) => {
    if (data && data.name) {
      console.log(`A filtrar por região: ${data.name}`);
      setRegionFilter(data.name);
    }
  };
  
  const handleUserClick = (userId) => {
    console.log(`A abrir histórico para o utilizador: ${userId}`);
    setSelectedUserId(userId);
    setIsModalOpen(true);
  };

  // --- USE EFFECT 1: CONEXÃO WEBSOCKET ---
  useEffect(() => {
    if (!token) return; 
    isUnmounting.current = false;
    function connect() {
      if (websocket.current) return;
      const wsUrl = `${WEBSOCKET_URL}?token=${encodeURIComponent(token)}`;
      websocket.current = new WebSocket(wsUrl);
      websocket.current.onopen = () => setIsConnected(true);
      websocket.current.onclose = (event) => {
        if (isUnmounting.current) return; 
        if (event.code === 1008 || event.code === 4003) {
            console.log("Token inválido ou expirado. A fazer logout.");
            logout();
            return;
        }
        if (event.code !== 1000) setIsConnected(false);
        websocket.current = null;
        clearTimeout(reconnectTimer.current);
        reconnectTimer.current = setTimeout(connect, 3000);
      };
      websocket.current.onerror = (error) => console.error("Erro no WebSocket:", error);
      websocket.current.onmessage = (message) => {
        const eventData = JSON.parse(message.data);
        setEvents(prevEvents => [eventData, ...prevEvents.slice(0, 100)]);
        if (eventData.event_type === 'purchase_complete') {
          updateSalesChart(eventData);
        } else if (eventData.event_type === 'payment_error') {
          updateErrorChart(eventData);
        } else if (eventData.event_type === 'IA_ALERT') {
          setIaAlert(eventData.message);
        }
      };
    }
    connect();
    return () => {
      isUnmounting.current = true;
      clearTimeout(reconnectTimer.current);
      if (websocket.current) {
        websocket.current.onopen = null;
        websocket.current.onclose = null;
        websocket.current.onerror = null;
        websocket.current.onmessage = null;
        websocket.current.close(1000, "Desmontagem do React");
        websocket.current = null;
      }
    };
  }, [token, logout]);

  // --- USE EFFECT 2: BUSCA DADOS HISTÓRICOS ---
  useEffect(() => {
    if (!token) return;
    const fetchHourlyData = async () => {
      try {
        const data = await fetchWithToken(`${API_URL}/api/history/sales-hourly-24h`, token, logout);
        setHourlySalesData(data);
      } catch (error) {
        console.error("Erro ao carregar gráfico histórico:", error.message);
      }
    };
    fetchHourlyData();
  }, [token, logout]);
  useEffect(() => {
    if (!token) return;
    const fetchSummaryData = async () => {
      try {
        const data = await fetchWithToken(`${API_URL}/api/history/summary-24h`, token, logout);
        setSummaryData(data);
        console.log("KPIs Históricos Atualizados!");
      } catch (error) {
        console.error("Erro ao recarregar KPIs:", error.message);
      }
    };
    const fetchTopProducts = async () => {
      try {
        const data = await fetchWithToken(`${API_URL}/api/history/top-products-24h`, token, logout);
        setTopProductsData(data);
        console.log("Top Produtos Atualizados!");
      } catch (error) {
        console.error("Erro ao carregar Top Produtos:", error.message);
      }
    };
    fetchSummaryData(); 
    fetchTopProducts();
    const intervalId = setInterval(() => {
        fetchSummaryData();
        fetchTopProducts();
    }, 30000);
    return () => {
      clearInterval(intervalId);
    };
  }, [token, logout]);


  // --- RENDERIZAÇÃO ---
  return (
    <div>
      <AlertBanner 
        alertMessage={iaAlert} 
        onDismiss={() => setIaAlert(null)}
      />

      <div className='header'>
        <h1>Painel de Operações em Tempo Real</h1>
        <div className="header-controls">
          <h3>
            Status da Conexão: 
            <span style={{ color: isConnected ? '#50fa7b' : '#ff5555' }}>
              {isConnected ? " CONECTADO" : " DESCONECTADO"}
            </span>
          </h3>
          <button onClick={logout} className="logout-button">Sair</button>
        </div>
      </div>
      
      <KpiCards data={summaryData} />

      <h2 className="section-title">Análise Histórica (Últimas 24h)</h2>
      <div className="historical-section">
        <HistoricalSalesChart data={hourlySalesData} />
      </div>

      <h2 className="section-title">Monitoramento em Tempo Real</h2>
      <div className="realtime-layout">
        
        <div className="realtime-charts-col">
          <SalesChart data={salesData} />
          <ErrorChart data={errorData} onBarClick={handleRegionClick} />
          <TopProductsChart data={topProductsData} />
        </div>
        
        <div className="feed-section">
          <div className="feed-header">
            <h2>Feed de Eventos</h2>
            {regionFilter && (
              <button onClick={() => setRegionFilter(null)} className="clear-filter-button">
                A filtrar por: {regionFilter} (Limpar)
              </button>
            )}
          </div>
          <EventFeed 
            events={events} 
            regionFilter={regionFilter} 
            onUserClick={handleUserClick} 
          />
        </div>
        
      </div>
      
      {/* --- O Modal (Pop-up) --- */}
      <UserHistoryModal
        userId={selectedUserId}
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
        token={token}
        logout={logout}
      />
      
    </div>
  );
}

export default DashboardPage;