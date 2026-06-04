import { publishCampaign, pauseCampaign } from '../api/campaigns'

const STATUS_COLORS = {
  DRAFT: '#6b7280',
  PUBLISHED: '#16a34a',
  PAUSED: '#ca8a04',
  FAILED: '#dc2626',
}

function StatusBadge({ status }) {
  return (
    <span style={{
      background: STATUS_COLORS[status] || '#6b7280',
      color: '#fff',
      padding: '2px 10px',
      borderRadius: '12px',
      fontSize: '0.75rem',
      fontWeight: 600,
      letterSpacing: '0.05em',
    }}>
      {status}
    </span>
  )
}

export default function CampaignList({ campaigns, loading, onRefresh }) {
  const handlePublish = async (id) => {
    try {
      await publishCampaign(id)
      onRefresh()
    } catch (err) {
      alert(err.response?.data?.error?.message || 'Publish failed')
    }
  }

  const handlePause = async (id) => {
    try {
      await pauseCampaign(id)
      onRefresh()
    } catch (err) {
      alert(err.response?.data?.error?.message || 'Pause failed')
    }
  }

  if (loading) return <p className="muted">Loading campaigns…</p>

  if (campaigns.length === 0) return (
    <div className="card">
      <p className="muted">No campaigns yet. Create one above.</p>
    </div>
  )

  return (
    <div className="card">
      <h2>Campaigns</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Objective</th>
              <th>Budget/day</th>
              <th>Start</th>
              <th>Status</th>
              <th>Google ID</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {campaigns.map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
                <td>{c.objective}</td>
                <td>${c.daily_budget}</td>
                <td>{c.start_date}</td>
                <td><StatusBadge status={c.status} /></td>
                <td className="muted">{c.google_campaign_id || '—'}</td>
                <td>
                  {c.status === 'DRAFT' && (
                    <button className="btn btn-success" onClick={() => handlePublish(c.id)}>
                      Publish
                    </button>
                  )}
                  {c.status === 'PUBLISHED' && (
                    <button className="btn btn-warn" onClick={() => handlePause(c.id)}>
                      Pause
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
