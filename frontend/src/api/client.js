import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json'
  }
});

// Interceptor para manejo global de errores (opcional)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const getDocuments = async () => {
  const { data } = await api.get('/documents');
  return data;
};

export const getEvents = async () => {
  const { data } = await api.get('/events');
  return data;
};

export const getTimeline = async (country) => {
  const { data } = await api.get(`/timeline/${country}`);
  return data.timeline || [];
};

export const getCountryStats = async (country) => {
  const { data } = await api.get(`/countries/${country}`);
  return data;
};

export const getDocument = async (id) => {
  const { data } = await api.get(`/documents/${id}`);
  return data;
};

export const queryAI = async (queryData) => {
  const { data } = await api.post('/ai/query', queryData);
  return data;
};

export default api;
