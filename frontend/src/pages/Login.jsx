import React, { useState } from 'react';
import { useAuth } from '../App.jsx'; 
import { useNavigate } from 'react-router-dom';

const API_URL = "http://127.0.0.1:8000";

function LoginPage() {
  const [isLogin, setIsLogin] = useState(true); 
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  
  const { login } = useAuth(); 
  const navigate = useNavigate(); 

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null); 
    if (isLogin) {
      
      try {
        
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch(`${API_URL}/auth/token`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: formData.toString(),
        });

        if (!response.ok) {
          const errData = await response.json();
          throw new Error(errData.detail || 'Falha ao fazer login');
        }

        const data = await response.json(); 
        login(data.access_token); 
        navigate('/'); 
        
      } catch (err) {
        setError(err.message);
      }
    } else {
      
      try {
        const response = await fetch(`${API_URL}/auth/register`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ username, password }),
        });

        if (!response.ok) {
          const errData = await response.json();
          throw new Error(errData.detail || 'Falha ao registar');
        }

       
        alert('Registo com sucesso! Faça login agora.');
        setIsLogin(true); 
        setError(null);
        
      } catch (err) {
        setError(err.message);
      }
    }
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <h2>{isLogin ? 'Login' : 'Registo'}</h2>
        <p>Painel de Operações em Tempo Real</p>
        
        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label htmlFor="username">Utilizador</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
          <div className="input-group">
            <label htmlFor="password">Senha</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          
          {error && <div className="error-message">{error}</div>}
          
          <button type="submit" className="login-button">
            {isLogin ? 'Entrar' : 'Registar'}
          </button>
        </form>
        
        <button 
          onClick={() => setIsLogin(!isLogin)} 
          className="toggle-button"
        >
          {isLogin ? 'Não tem conta? Registe-se' : 'Já tem conta? Faça login'}
        </button>
      </div>
    </div>
  );
}

export default LoginPage;