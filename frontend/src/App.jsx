import React, { createContext, useState, useContext, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';


import DashboardPage from './pages/Dashboard.jsx';
import LoginPage from './pages/Login.jsx';


const AuthContext = createContext(null);

export function useAuth() {

    return useContext(AuthContext);
}


function AuthProvider({ children }) {
    const [token, setToken] = useState(null);
    const [isAuthLoading, setIsAuthLoading] = useState(true);

    useEffect(() => {

        try {
            const storedToken = localStorage.getItem('authToken');
            if (storedToken) {
                setToken(storedToken);
            }
        } catch (error) {
            console.error("Não foi possível carregar o token:", error);
        } finally {
            setIsAuthLoading(false);
        }
    }, []);

    const login = (newToken) => {
        setToken(newToken);
        localStorage.setItem('authToken', newToken);
    };

    const logout = () => {
        setToken(null);
        localStorage.removeItem('authToken');
    };


    const value = {
        token,
        login,
        logout,
        isAuthenticated: !!token,
    };


    if (isAuthLoading) {
        return <div className="loading-screen">A carregar...</div>;
    }

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}


function ProtectedRoute() {
    const { isAuthenticated } = useAuth();

    if (!isAuthenticated) {

        return <Navigate to="/login" replace />;
    }


    return <Outlet />;
}


function App() {
    return (
        <AuthProvider>
            <Routes>
                {/* Rota 1: A Página de Login */}
                <Route path="/login" element={<LoginPage />} />

                {/* Rota 2: O Dashboard (Protegido) */}
                <Route element={<ProtectedRoute />}>
                    <Route path="/" element={<DashboardPage />} />
                </Route>

                {/* Rota 3: Se o utilizador se enganar no URL */}
                <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
        </AuthProvider>
    );
}

export default App;