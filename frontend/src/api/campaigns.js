import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000',
})

export const getCampaigns = () => api.get('/api/campaigns')
export const createCampaign = (data) => api.post('/api/campaigns', data)
export const publishCampaign = (id) => api.post(`/api/campaigns/${id}/publish`)
export const pauseCampaign = (id) => api.post(`/api/campaigns/${id}/pause`)
export const resumeCampaign = (id) => api.post(`/api/campaigns/${id}/resume`)
