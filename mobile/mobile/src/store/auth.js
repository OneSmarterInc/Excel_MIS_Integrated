import AsyncStorage from '@react-native-async-storage/async-storage';
import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';

import api from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const [token, saved] = await Promise.all([
        AsyncStorage.getItem('access'),
        AsyncStorage.getItem('user'),
      ]);
      if (token && saved) setUser(JSON.parse(saved));
      setLoading(false);
    })();
  }, []);

  const persist = async (payload) => {
    await AsyncStorage.multiSet([
      ['access', payload.access],
      ['refresh', payload.refresh],
      ['user', JSON.stringify(payload.user)],
    ]);
    setUser(payload.user);
  };

  const value = useMemo(
    () => ({
      user,
      loading,
      login: async (email, password, role) => {
        const { data } = await api.post('/auth/login/', { email, password, role });
        await persist(data);
        return data.user;
      },
      register: async (name, email, password, role) => {
        const { data } = await api.post('/auth/register/', { name, email, password, role });
        await persist(data);
        return data.user;
      },
      signOut: async () => {
        await AsyncStorage.multiRemove(['access', 'refresh', 'user']);
        setUser(null);
      },
      refreshProfile: async () => {
        const { data } = await api.get('/auth/profile/');
        await AsyncStorage.setItem('user', JSON.stringify(data));
        setUser(data);
      },
    }),
    [user, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
