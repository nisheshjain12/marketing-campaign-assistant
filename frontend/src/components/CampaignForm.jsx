import { useState } from 'react'
import { createCampaign } from '../api/campaigns'

const EMPTY_FORM = {
  name: '',
  objective: 'TRAFFIC',
  campaign_type: 'SEARCH',
  daily_budget: '',
  start_date: '',
  end_date: '',
  ad_group_name: '',
  ad_headline: '',
  ad_description: '',
  asset_url: '',
}

export default function CampaignForm({ onSaved }) {
  const [form, setForm] = useState(EMPTY_FORM)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const payload = {
        ...form,
        daily_budget: Number(form.daily_budget),
        end_date: form.end_date || null,
        asset_url: form.asset_url || null,
      }
      await createCampaign(payload)
      setForm(EMPTY_FORM)
      onSaved()
    } catch (err) {
      const msg = err.response?.data?.error?.message || 'Failed to save campaign'
      const details = err.response?.data?.error?.details || []
      setError(details.length ? details.join(', ') : msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card">
      <h2>New Campaign</h2>
      {error && <p className="error">{error}</p>}
      <form onSubmit={handleSubmit}>
        <div className="form-row">
          <div className="field">
            <label>Campaign Name *</label>
            <input name="name" value={form.name} onChange={handleChange} placeholder="e.g. Summer Sale" required />
          </div>
          <div className="field">
            <label>Objective *</label>
            <select name="objective" value={form.objective} onChange={handleChange}>
              <option value="TRAFFIC">Traffic</option>
              <option value="LEADS">Leads</option>
              <option value="SALES">Sales</option>
              <option value="AWARENESS">Awareness</option>
            </select>
          </div>
        </div>

        <div className="form-row">
          <div className="field">
            <label>Campaign Type *</label>
            <select name="campaign_type" value={form.campaign_type} onChange={handleChange}>
              <option value="SEARCH">Search</option>
            </select>
          </div>
          <div className="field">
            <label>Daily Budget ($) *</label>
            <input name="daily_budget" type="number" min="1" value={form.daily_budget} onChange={handleChange} placeholder="e.g. 10" required />
          </div>
        </div>

        <div className="form-row">
          <div className="field">
            <label>Start Date *</label>
            <input name="start_date" type="date" value={form.start_date} onChange={handleChange} required />
          </div>
          <div className="field">
            <label>End Date</label>
            <input name="end_date" type="date" value={form.end_date} onChange={handleChange} />
          </div>
        </div>

        <div className="form-row">
          <div className="field">
            <label>Ad Group Name *</label>
            <input name="ad_group_name" value={form.ad_group_name} onChange={handleChange} placeholder="e.g. Main Group" required />
          </div>
          <div className="field">
            <label>Asset URL</label>
            <input name="asset_url" value={form.asset_url} onChange={handleChange} placeholder="https://example.com" />
          </div>
        </div>

        <div className="field">
          <label>Ad Headline *</label>
          <input name="ad_headline" value={form.ad_headline} onChange={handleChange} placeholder="e.g. Shop now – great deals" required />
        </div>

        <div className="field">
          <label>Ad Description *</label>
          <textarea name="ad_description" value={form.ad_description} onChange={handleChange} placeholder="e.g. Limited offer, sign up today" rows={3} required />
        </div>

        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? 'Saving…' : 'Save Locally'}
        </button>
      </form>
    </div>
  )
}
