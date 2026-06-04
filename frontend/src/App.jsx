import { useState, useEffect, useCallback } from 'react'
import CampaignForm from './components/CampaignForm'
import CampaignList from './components/CampaignList'
import { getCampaigns } from './api/campaigns'

export default function App() {
  const [campaigns, setCampaigns] = useState([])
  const [listLoading, setListLoading] = useState(true)
  const [listError, setListError] = useState('')

  const fetchCampaigns = useCallback(async () => {
    setListLoading(true)
    setListError('')
    try {
      const res = await getCampaigns()
      setCampaigns(res.data.data)
    } catch {
      setListError('Could not load campaigns. Is the backend running?')
    } finally {
      setListLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchCampaigns()
  }, [fetchCampaigns])

  return (
    <div className="container">
      <header>
        <h1>Marketing Campaign Assistant</h1>
      </header>

      <CampaignForm onSaved={fetchCampaigns} />

      {listError && <p className="error">{listError}</p>}
      <CampaignList
        campaigns={campaigns}
        loading={listLoading}
        onRefresh={fetchCampaigns}
      />
    </div>
  )
}
