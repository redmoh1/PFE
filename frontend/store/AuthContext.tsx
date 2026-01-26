
import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, UserRole } from '../types';

interface AuthContextType {
  user: User | null;
  login: (email: string, company: string) => void;
  register: (email: string, company: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const savedUser = localStorage.getItem('insight_pro_user');
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }
  }, []);

  const login = (email: string, company: string) => {
    const newUser: User = {
      id: btoa(email),
      email,
      company,
      role: UserRole.ADMIN,
      avatar: `https://picsum.photos/seed/${email}/200`
    };
    setUser(newUser);
    localStorage.setItem('insight_pro_user', JSON.stringify(newUser));
  };

  const register = (email: string, company: string) => {
    login(email, company);
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('insight_pro_user');
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};
