// centralized axios client
// gives the frontend one shared HTTP client
// future API services will import this instance rather than creating their own Axios config

import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

export default api
