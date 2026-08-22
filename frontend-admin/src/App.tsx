import React, { useState, useEffect } from 'react'
import './index.css'

const BACKEND_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' ? 'http://localhost:8085' : '';

const TAB_LABELS: Record<string, { icon: string; label: string; desc: string }> = {
  faqs:    { icon: '📋', label: 'Preguntas Frecuentes', desc: 'Administra el banco de conocimiento y sincronización vectorial' },
  sellers: { icon: '👥', label: 'Asesores',            desc: 'Estado y disponibilidad del equipo de asesores' },
  chats:   { icon: '💬', label: 'Supervisar Chats',      desc: 'Monitorea las conversaciones de todos los cajeros en tiempo real' },
  test:    { icon: '🔬', label: 'Probar Qdrant RAG',     desc: 'Prueba de búsqueda semántica y similitud coseno' },
}

export default function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('admin_token'))
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Dashboard states
  const [activeTab, setActiveTab] = useState<'faqs' | 'sellers' | 'test' | 'chats'>('faqs')
  const [faqs, setFaqs] = useState<any[]>([])
  const [sellers, setSellers] = useState<any[]>([])

  // Supervisor Chats states
  const [monitoredChats, setMonitoredChats] = useState<any[]>([])
  const [activeMonitoredChat, setActiveMonitoredChat] = useState<any | null>(null)
  const [monitoredMessages, setMonitoredMessages] = useState<any[]>([])
  const [supervisorReplyInput, setSupervisorReplyInput] = useState('')

  // FAQ Form states
  const [faqId, setFaqId] = useState<string | null>(null)
  const [faqTitle, setFaqTitle] = useState('')
  const [faqContent, setFaqContent] = useState('')
  const [faqKeywords, setFaqKeywords] = useState('')
  const [faqPriority, setFaqPriority] = useState(0)

  // Test Chat states
  const [chatInput, setChatInput] = useState('')
  const [chatMessages, setChatMessages] = useState<any[]>([
    { role: 'bot', text: '¡Hola! Escribe cualquier pregunta para probar las FAQs en vivo con Qdrant.' }
  ])
  const [similarityResults, setSimilarityResults] = useState<any[]>([])
  const [toast, setToast] = useState<{ message: string; isError?: boolean } | null>(null)

  useEffect(() => {
    if (token) {
      loadFAQs()
      loadSellers()
      loadMonitoredChats()
    }
  }, [token])

  const showToast = (message: string, isError = false) => {
    setToast({ message, isError })
    setTimeout(() => setToast(null), 3500)
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/admin/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })
      const result = await response.json()
      if (result.success) {
        localStorage.setItem('admin_token', result.token)
        setToken(result.token)
        showToast('Sesión iniciada con éxito.')
      } else {
        setError(result.message || 'Credenciales inválidas. Verifica tu email y contraseña.')
      }
    } catch (err) {
      setError('No se pudo conectar con el servidor. Verifica que el sistema esté activo.')
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('admin_token')
    setToken(null)
  }

  const loadFAQs = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/admin/faqs?active_only=false&token=${token}`)
      const result = await response.json()
      if (result.success) setFaqs(result.data)
    } catch (err) {
      showToast('Error al cargar preguntas frecuentes.', true)
    }
  }

  const loadSellers = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/admin/sellers?token=${token}`)
      const result = await response.json()
      if (result.success) setSellers(result.data)
    } catch (err) {
      showToast('Error al cargar vendedores.', true)
    }
  }

  const loadMonitoredChats = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/admin/chats?token=${token}`)
      const result = await response.json()
      if (result.success) {
        setMonitoredChats(result.data)
        // If there's an active chat, refresh its messages too
        if (activeMonitoredChat) {
          const updatedChat = result.data.find((c: any) => c.id === activeMonitoredChat.id)
          if (updatedChat) {
            loadMonitoredMessages(updatedChat)
          }
        }
      }
    } catch (err) {
      console.error('Error loading monitored chats:', err)
    }
  }

  const loadMonitoredMessages = async (chat: any) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/admin/chats/${chat.id}/messages?token=${token}`)
      const result = await response.json()
      if (result.success) {
        setMonitoredMessages(result.data)
      }
    } catch (err) {
      console.error('Error loading monitored messages:', err)
    }
  }

  const handleSelectMonitoredChat = (chat: any) => {
    setActiveMonitoredChat(chat)
    loadMonitoredMessages(chat)
  }

  const handleSendSupervisorMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!supervisorReplyInput.trim() || !activeMonitoredChat) return
    const text = supervisorReplyInput.trim()
    setSupervisorReplyInput('')

    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/admin/chats/${activeMonitoredChat.id}/messages?token=${token}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: text })
      })
      const result = await response.json()
      if (result.success) {
        showToast('Mensaje de supervisor entregado.')
        loadMonitoredMessages(activeMonitoredChat)
      } else {
        showToast('Error al enviar mensaje.', true)
      }
    } catch (err) {
      showToast('Error de red.', true)
    }
  }

  // Polling hook for Chats tab
  useEffect(() => {
    let interval: any = null
    if (token && activeTab === 'chats') {
      loadMonitoredChats()
      interval = setInterval(() => {
        loadMonitoredChats()
      }, 3000)
    }
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [token, activeTab, activeMonitoredChat ? activeMonitoredChat.id : null])

  const handleSaveFAQ = async (e: React.FormEvent) => {
    e.preventDefault()
    const payload = {
      title: faqTitle,
      content: faqContent,
      keywords: faqKeywords.split(',').map(k => k.trim()).filter(Boolean),
      priority: faqPriority
    }
    const url = faqId
      ? `${BACKEND_URL}/api/v1/admin/faqs/${faqId}?token=${token}`
      : `${BACKEND_URL}/api/v1/admin/faqs?token=${token}`
    const method = faqId ? 'PUT' : 'POST'
    try {
      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      const result = await response.json()
      if (result.success) {
        showToast(faqId ? 'FAQ actualizada y sincronizada con Qdrant. ✓' : 'FAQ creada y sincronizada. ✓')
        resetFAQForm()
        loadFAQs()
      } else {
        showToast(result.message || 'Error al guardar.', true)
      }
    } catch (err) {
      showToast('Error de red al guardar FAQ.', true)
    }
  }

  const handleDeleteFAQ = async (id: string, physical = false) => {
    if (!confirm(physical ? '¿Eliminar físicamente de forma permanente? Esta acción no se puede deshacer.' : '¿Confirmas la eliminación lógica de esta FAQ?')) return
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/admin/faqs/${id}?physical=${physical}&token=${token}`, {
        method: 'DELETE'
      })
      const result = await response.json()
      if (result.success) {
        showToast('FAQ eliminada con éxito.')
        loadFAQs()
      } else {
        showToast(result.message, true)
      }
    } catch (err) {
      showToast('Error de red al eliminar.', true)
    }
  }

  const handleSyncAll = async () => {
    showToast('Sincronizando base de conocimiento completa...')
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/admin/faqs/sync-all?token=${token}`, { method: 'POST' })
      const result = await response.json()
      showToast(result.success ? result.message : result.message, !result.success)
      if (result.success) loadFAQs()
    } catch (err) {
      showToast('Error de red al sincronizar.', true)
    }
  }

  const handleImportCSV = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return
    const file = e.target.files[0]
    const formData = new FormData()
    formData.append('file', file)
    showToast('Importando archivo CSV...')
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/admin/faqs/import?token=${token}`, {
        method: 'POST',
        body: formData
      })
      const result = await response.json()
      showToast(result.success ? result.message : result.message, !result.success)
      if (result.success) loadFAQs()
    } catch (err) {
      showToast('Error al importar.', true)
    }
  }

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!chatInput.trim()) return
    const text = chatInput.trim()
    setChatInput('')
    setChatMessages(prev => [...prev, { role: 'user', text }])
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/admin/faqs/test?token=${token}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text })
      })
      const result = await response.json()
      if (result.success && result.results.length > 0) {
        const topMatch = result.results[0]
        setChatMessages(prev => [...prev, { role: 'bot', text: topMatch.text }])
        setSimilarityResults(result.results)
      } else {
        setChatMessages(prev => [...prev, { role: 'bot', text: 'No se encontraron coincidencias en Qdrant.' }])
        setSimilarityResults([])
      }
    } catch (err) {
      setChatMessages(prev => [...prev, { role: 'bot', text: 'Error al conectar con Qdrant.' }])
    }
  }

  const resetFAQForm = () => {
    setFaqId(null)
    setFaqTitle('')
    setFaqContent('')
    setFaqKeywords('')
    setFaqPriority(0)
  }

  const handleEditFAQ = (faq: any) => {
    setFaqId(faq.id)
    setFaqTitle(faq.title)
    setFaqContent(faq.content)
    setFaqKeywords(faq.keywords ? faq.keywords.join(', ') : '')
    setFaqPriority(faq.priority || 0)
    setActiveTab('faqs')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const switchTab = (tab: 'faqs' | 'sellers' | 'chats' | 'test') => {
    setActiveTab(tab)
    setSidebarOpen(false)
  }

  // Stats computed
  const availableSellers = sellers.filter(s => s.status === 'available').length
  const busySellers = sellers.filter(s => s.status === 'busy').length
  const offlineSellers = sellers.filter(s => s.status === 'offline').length

  /* ===========================
     LOGIN VIEW
  =========================== */
  if (!token) {
    return (
      <div className="login-page">
        <div className="login-wrapper">
          <div className="login-card">
            <div className="login-logo">
              <span className="login-logo-icon">🦫</span>
              <h1>Castor Admin</h1>
              <p>Panel de Administración — Ferretería Enterprise</p>
            </div>

            <h2>Iniciar Sesión</h2>

            {error && (
              <div className="error-banner">
                <span>⚠️</span>
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleLogin}>
              <div className="form-group">
                <label className="form-label">Correo Electrónico</label>
                <input
                  type="email"
                  className="form-input"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="admin@ferreteria.com"
                  required
                />
              </div>
              <div className="form-group" style={{ marginBottom: '1.75rem' }}>
                <label className="form-label">Contraseña</label>
                <input
                  type="password"
                  className="form-input"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                />
              </div>
              <button type="submit" className="btn btn-primary btn-primary-full">
                Ingresar al Panel →
              </button>
            </form>

            <p style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              admin@ferreteria.com / admin_pass
            </p>
          </div>
        </div>
      </div>
    )
  }

  /* ===========================
     MAIN DASHBOARD VIEW
  =========================== */
  return (
    <div className="app-layout">
      {/* Toast */}
      {toast && (
        <div className={`toast ${toast.isError ? 'error' : ''}`}>
          <span className="toast-icon">{toast.isError ? '❌' : '✅'}</span>
          <span>{toast.message}</span>
        </div>
      )}

      {/* Mobile overlay */}
      <div
        className={`sidebar-overlay ${sidebarOpen ? 'open' : ''}`}
        onClick={() => setSidebarOpen(false)}
      />

      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-brand">
          <div className="sidebar-brand-name">🦫 Castor Admin</div>
          <div className="sidebar-brand-sub">Ferretería Enterprise</div>
        </div>

        <nav className="sidebar-nav">
          <div className="sidebar-nav-label" style={{ marginBottom: '0.75rem' }}>Navegación</div>
          {(Object.keys(TAB_LABELS) as ('faqs' | 'sellers' | 'chats' | 'test')[]).map(tab => (
            <button
              key={tab}
              className={`sidebar-nav-item ${activeTab === tab ? 'active' : ''}`}
              onClick={() => switchTab(tab)}
            >
              <span className="nav-icon">{TAB_LABELS[tab].icon}</span>
              <span>{TAB_LABELS[tab].label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <button className="btn btn-danger-outline" style={{ width: '100%', justifyContent: 'center' }} onClick={handleLogout}>
            Cerrar Sesión
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        {/* Top Header */}
        <header className="top-header">
          <button className="hamburger-btn" onClick={() => setSidebarOpen(!sidebarOpen)}>☰</button>
          <div className="top-header-title">
            <h2>{TAB_LABELS[activeTab].icon} {TAB_LABELS[activeTab].label}</h2>
            <p>{TAB_LABELS[activeTab].desc}</p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ textAlign: 'right', display: 'none' }} className="top-user-info">
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>Administrador</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>admin@ferreteria.com</div>
            </div>
            <div style={{ width: 36, height: 36, borderRadius: '50%', background: 'linear-gradient(135deg, var(--orange-400), var(--orange-600))', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 700, fontSize: '0.9rem', cursor: 'pointer' }}>
              A
            </div>
          </div>
        </header>

        {/* Page Body */}
        <div className="page-body">

          {/* ===========================
              FAQs TAB
          =========================== */}
          {activeTab === 'faqs' && (
            <div>
              <div className="page-header">
                <h1 className="page-title">Base de Conocimiento</h1>
                <p className="page-subtitle">{faqs.length} preguntas frecuentes registradas</p>
              </div>

              {/* FAQ Form Card */}
              <div className="card" style={{ marginBottom: '1.5rem' }}>
                <div className="card-header">
                  <h3>{faqId ? '✏️ Editar FAQ' : '➕ Nueva FAQ'}</h3>
                  {faqId && (
                    <button className="btn btn-ghost btn-sm" onClick={resetFAQForm}>
                      Cancelar Edición
                    </button>
                  )}
                </div>
                <div className="card-body">
                  <form onSubmit={handleSaveFAQ}>
                    <div className="faq-form-grid">
                      <div className="form-group">
                        <label className="form-label">Pregunta</label>
                        <input
                          type="text"
                          className="form-input"
                          value={faqTitle}
                          onChange={e => setFaqTitle(e.target.value)}
                          required
                          placeholder="¿Cuál es la política de garantías?"
                        />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Palabras Clave (separadas por comas)</label>
                        <input
                          type="text"
                          className="form-input"
                          value={faqKeywords}
                          onChange={e => setFaqKeywords(e.target.value)}
                          placeholder="garantía, cambio, devolver, producto"
                        />
                      </div>
                      <div className="form-group faq-form-grid-full">
                        <label className="form-label">Respuesta</label>
                        <textarea
                          className="form-input"
                          value={faqContent}
                          onChange={e => setFaqContent(e.target.value)}
                          required
                          placeholder="Todos nuestros productos eléctricos y maquinaria cuentan con al menos 1 año de garantía..."
                        />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Prioridad</label>
                        <input
                          type="number"
                          className="form-input"
                          value={faqPriority}
                          onChange={e => setFaqPriority(Number(e.target.value))}
                          min={0}
                          max={100}
                        />
                      </div>
                    </div>
                    <div className="faq-form-actions">
                      <button type="submit" className="btn btn-primary">
                        {faqId ? '💾 Actualizar y Sincronizar' : '✓ Guardar y Sincronizar con Qdrant'}
                      </button>
                      {faqId && (
                        <button type="button" className="btn btn-ghost" onClick={resetFAQForm}>
                          Cancelar
                        </button>
                      )}
                    </div>
                  </form>
                </div>
              </div>

              {/* Actions Bar */}
              <div className="action-bar">
                <div className="action-bar-left">
                  <button className="btn btn-success" onClick={handleSyncAll}>
                    🔄 Sincronizar Todo con Qdrant
                  </button>
                  <label className="csv-label">
                    📂 Importar CSV
                    <input type="file" accept=".csv" onChange={handleImportCSV} style={{ display: 'none' }} />
                  </label>
                </div>
                <span className="badge badge-orange" style={{ padding: '0.4rem 0.85rem', fontSize: '0.85rem' }}>
                  {faqs.filter(f => f.qdrant_synced).length} / {faqs.length} sincronizadas
                </span>
              </div>

              {/* FAQ List */}
              <div className="faq-list">
                {faqs.length === 0 && (
                  <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                    <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>📭</div>
                    <p>Aún no hay preguntas frecuentes. Agrega la primera usando el formulario de arriba.</p>
                  </div>
                )}
                {faqs.map(faq => (
                  <div key={faq.id} className="faq-item">
                    <div className="faq-item-body">
                      <div className="faq-item-badges">
                        {!faq.active && <span className="badge badge-red">● Inactiva</span>}
                        {faq.qdrant_synced
                          ? <span className="badge badge-green">✓ Sincronizada</span>
                          : <span className="badge badge-yellow">⏳ Pendiente</span>
                        }
                        {faq.priority > 0 && (
                          <span className="badge badge-gray">Prioridad {faq.priority}</span>
                        )}
                      </div>
                      <div className="faq-item-title">{faq.title}</div>
                      <div className="faq-item-content">{faq.content}</div>
                    </div>
                    <div className="faq-item-actions">
                      <button className="btn btn-secondary btn-sm" onClick={() => handleEditFAQ(faq)}>
                        ✏️ Editar
                      </button>
                      <button className="btn btn-danger-outline btn-sm" onClick={() => handleDeleteFAQ(faq.id, false)}>
                        Deshabilitar
                      </button>
                      <button className="btn btn-danger btn-sm" onClick={() => handleDeleteFAQ(faq.id, true)}>
                        Eliminar
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ===========================
              SELLERS TAB
          =========================== */}
          {activeTab === 'sellers' && (
            <div>
              <div className="page-header">
                <h1 className="page-title">Equipo de Asesores</h1>
                <p className="page-subtitle">{sellers.length} asesores registrados en el sistema</p>
              </div>
 
              {/* Stats Cards */}
              <div className="stats-grid">
                <div className="stat-card">
                  <span className="stat-label">Total</span>
                  <span className="stat-value orange">{sellers.length}</span>
                </div>
                <div className="stat-card">
                  <span className="stat-label">Disponibles</span>
                  <span className="stat-value green">{availableSellers}</span>
                </div>
                <div className="stat-card">
                  <span className="stat-label">Ocupados</span>
                  <span className="stat-value orange">{busySellers}</span>
                </div>
                <div className="stat-card">
                  <span className="stat-label">Desconectados</span>
                  <span className="stat-value red">{offlineSellers}</span>
                </div>
                <div className="stat-card">
                  <span className="stat-label">Chats Activos</span>
                  <span className="stat-value">{sellers.reduce((s, v) => s + (v.active_chats || 0), 0)}</span>
                </div>
              </div>
 
              {/* Table */}
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Asesor</th>
                      <th>Email</th>
                      <th>WhatsApp</th>
                      <th>Estado</th>
                      <th>Chats</th>
                      <th>Límite</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sellers.map(s => {
                      const initials = s.name.split(' ').map((n: string) => n[0]).join('').substring(0, 2).toUpperCase()
                      const pct = s.max_chats ? Math.round((s.active_chats / s.max_chats) * 100) : 0
                      return (
                        <tr key={s.id}>
                          <td>
                            <div className="seller-name-cell">
                              <div className="seller-avatar">{initials}</div>
                              <div>
                                <div className="seller-name">{s.name}</div>
                                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                  {s.team_zone ? `Sucursal: ${s.team_zone}` : 'Sin sucursal'}
                                </div>
                              </div>
                            </div>
                          </td>
                          <td style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>{s.email}</td>
                          <td style={{ fontSize: '0.875rem', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>{s.whatsapp_phone}</td>
                          <td>
                            <span className={`badge ${s.status === 'available' ? 'badge-green' : s.status === 'busy' ? 'badge-yellow' : 'badge-gray'}`}>
                              {s.status === 'available' ? '● Disponible' : s.status === 'busy' ? '● Ocupado' : '● Desconectado'}
                            </span>
                          </td>
                          <td>
                            <div className="chat-bar-wrapper">
                              <span style={{ fontSize: '0.9rem', fontWeight: 600, minWidth: '24px' }}>{s.active_chats}</span>
                              <div className="chat-bar">
                                <div className="chat-bar-fill" style={{ width: `${pct}%` }} />
                              </div>
                            </div>
                          </td>
                          <td>
                            <span className="badge badge-orange">{s.max_chats}</span>
                          </td>
                        </tr>
                      )
                    })}
                    {sellers.length === 0 && (
                      <tr>
                        <td colSpan={6} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                          No hay asesores registrados.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
 
          {/* ===========================
              SUPERVISOR CHATS TAB
          =========================== */}
          {activeTab === 'chats' && (
            <div>
              <div className="page-header">
                <h1 className="page-title">Supervisión de Chats</h1>
                <p className="page-subtitle">Visualiza y controla las conversaciones de tus {sellers.length} asesores en tiempo real</p>
              </div>

              <div className="supervisor-chats-layout">
                {/* Left Column: Chat list */}
                <div className="supervisor-chats-sidebar">
                  <div className="sidebar-list-header">
                    <h4>Todas las Conversaciones ({monitoredChats.length})</h4>
                  </div>
                  <div className="supervisor-chats-list">
                    {monitoredChats.length === 0 && (
                      <div className="chats-empty-msg">No hay chats activos registrados.</div>
                    )}
                    {monitoredChats.map(c => {
                      const isActive = activeMonitoredChat && activeMonitoredChat.id === c.id
                      return (
                        <div
                          key={c.id}
                          className={`monitored-chat-item ${isActive ? 'active' : ''}`}
                          onClick={() => handleSelectMonitoredChat(c)}
                        >
                          <div className="chat-item-phone">📞 {c.session_id.replace('sess_', '').substring(0, 12)}...</div>
                          <div className="chat-item-badges-row">
                            <span className={`badge ${c.status === 'human_active' ? 'badge-orange' : c.status === 'waiting_agent' ? 'badge-red' : 'badge-green'}`}>
                              {c.status === 'human_active' ? '👤 Cajero' : c.status === 'waiting_agent' ? '⏳ En espera' : '🤖 Bot / Auto'}
                            </span>
                            {c.assigned_seller && (
                              <span className="badge badge-gray">
                                Asesor: {c.assigned_seller.name}
                              </span>
                            )}
                          </div>
                          {c.last_activity && (
                            <div className="chat-item-time">Última act: {c.last_activity.substring(11, 16)}</div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* Right Column: Chat messages pane */}
                <div className="supervisor-chat-pane">
                  {activeMonitoredChat ? (
                    <div className="chat-pane-wrapper">
                      {/* Top status bar */}
                      <div className="chat-pane-header">
                        <div>
                          <h3>Chat ID: {activeMonitoredChat.session_id}</h3>
                          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                            Estado actual: <strong>{activeMonitoredChat.status}</strong> 
                            {activeMonitoredChat.assigned_seller && ` | Cajero: ${activeMonitoredChat.assigned_seller.name}`}
                          </span>
                        </div>
                      </div>

                      {/* Messages body */}
                      <div className="chat-pane-messages">
                        {monitoredMessages.map((m, idx) => {
                          const isOutbound = m.direction === 'outbound'
                          return (
                            <div
                              key={m.id || idx}
                              className={`chat-bubble-wrapper ${isOutbound ? 'outbound' : 'inbound'}`}
                            >
                              <div className={`chat-bubble ${m.direction}`}>
                                <div className="bubble-content">{m.content}</div>
                                <div className="bubble-role">
                                  {m.role === 'seller' ? '👤 Asesor' : m.role === 'assistant' ? '🦫 Bot Castor' : '📱 Cliente'}
                                </div>
                              </div>
                            </div>
                          )
                        })}
                      </div>

                      {/* Outbound supervision reply bar */}
                      <div className="chat-pane-input-bar">
                        <form onSubmit={handleSendSupervisorMessage} style={{ display: 'flex', width: '100%', gap: '0.75rem' }}>
                          <input
                            type="text"
                            value={supervisorReplyInput}
                            onChange={e => setSupervisorReplyInput(e.target.value)}
                            placeholder="Intervenir y responder directamente al WhatsApp del cliente..."
                            className="form-input"
                            style={{ flexGrow: 1 }}
                          />
                          <button type="submit" className="btn btn-primary" style={{ padding: '0 1.5rem' }}>
                            Enviar ➤
                          </button>
                        </form>
                      </div>
                    </div>
                  ) : (
                    <div className="chat-pane-placeholder">
                      <span>💬</span>
                      <p>Selecciona una conversación de la lista de la izquierda para ver su historial y supervisarla.</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ===========================
              TEST RAG TAB
          =========================== */}
          {activeTab === 'test' && (
            <div>
              <div className="page-header">
                <h1 className="page-title">Prueba Semántica RAG</h1>
                <p className="page-subtitle">Consulta en tiempo real contra los vectores de Qdrant y visualiza la similitud coseno</p>
              </div>

              <div className="rag-grid">
                {/* Chat Panel */}
                <div>
                  <div className="card" style={{ marginBottom: '0.75rem' }}>
                    <div className="card-header">
                      <h3>💬 Consulta de Prueba</h3>
                    </div>
                  </div>
                  <div className="rag-chat-panel">
                    <div className="rag-chat-messages">
                      {chatMessages.map((m, idx) => (
                        <div key={idx} className={`chat-bubble ${m.role}`}>
                          {m.text}
                        </div>
                      ))}
                    </div>
                    <form className="rag-chat-input-bar" onSubmit={handleSendMessage}>
                      <input
                        type="text"
                        className="rag-chat-input"
                        value={chatInput}
                        onChange={e => setChatInput(e.target.value)}
                        placeholder="Ej: ¿Cuál es el horario de atención?"
                      />
                      <button type="submit" className="btn btn-primary btn-sm">
                        Enviar →
                      </button>
                    </form>
                  </div>
                </div>

                {/* Results Panel */}
                <div>
                  <div className="card" style={{ marginBottom: '0.75rem' }}>
                    <div className="card-header">
                      <h3>📊 Resultados Qdrant</h3>
                    </div>
                  </div>
                  <div className="rag-results-panel">
                    <div className="rag-results-body">
                      {similarityResults.length === 0 && (
                        <div className="rag-empty">
                          <span className="rag-empty-icon">🔍</span>
                          <p>Realiza una consulta en el panel izquierdo para ver las métricas de similitud coseno.</p>
                        </div>
                      )}
                      {similarityResults.map((r, idx) => (
                        <div key={idx} className="rag-result-item">
                          <div className="rag-result-meta">
                            <span className="rag-score">{(r.score * 100).toFixed(1)}%</span>
                            <span className="badge badge-gray" style={{ fontSize: '0.72rem' }}>{r.category || 'general'}</span>
                          </div>
                          <div className="rag-score-bar-wrapper">
                            <div className="rag-score-bar" style={{ width: `${r.score * 100}%` }} />
                          </div>
                          <p className="rag-result-text">{r.text}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

        </div>
      </main>
    </div>
  )
}
