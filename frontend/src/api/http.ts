import axios from 'axios'
import { setupInterceptors } from './interceptors'

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 20000,
})

setupInterceptors(http)
