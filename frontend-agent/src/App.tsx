import React, { useState, useEffect, useRef } from 'react'

const BACKEND_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' ? 'http://localhost:8085' : '';

export default function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('agent_token'))
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  
  // Chat lists
  const [assignedChats, setAssignedChats] = useState<any[]>([])
  const [waitingChats, setWaitingChats] = useState<any[]>([])
  const [activeChat, setActiveChat] = useState<any | null>(null)
  const [messages, setMessages] = useState<any[]>([])
  const [messageInput, setMessageInput] = useState('')
  
  // Note states
  const [noteInput, setNoteInput] = useState('')
  const [sellers, setSellers] = useState<any[]>([])
  const [showTransfer, setShowTransfer] = useState(false)
  const [toast, setToast] = useState<{ message: string; isError?: boolean } | null>(null)
  
  const sseSourceRef = useRef<EventSource | null>(null)
  const messagesEndRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (token) {
      loadChats()
      loadSellers()
      connectSSE()
    }
    return () => {
      if (sseSourceRef.current) {
        sseSourceRef.current.close()
      }
    }
  }, [token])

  useEffect(() => {
    // Scroll chat to bottom
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  const showToast = (message: string, isError = false) => {
    setToast({ message, isError })
    setTimeout(() => setToast(null), 3000)
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
        localStorage.setItem('agent_token', result.token)
        setToken(result.token)
        showToast('Sesión de agente iniciada.')
      } else {
        setError(result.message || 'Credenciales inválidas.')
      }
    } catch (err) {
      setError('Error al conectar con el servidor.')
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('agent_token')
    setToken(null)
    if (sseSourceRef.current) {
      sseSourceRef.current.close()
    }
  }

  const loadChats = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/agent/chats?token=${token}`)
      const result = await response.json()
      if (result.success) {
        setAssignedChats(result.assigned)
        setWaitingChats(result.waiting)
      }
    } catch (err) {
      showToast('Error al cargar conversaciones.', true)
    }
  }

  const loadSellers = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/admin/sellers?token=${token}`)
      const result = await response.json()
      if (result.success) {
        setSellers(result.data.filter((s: any) => s.status === 'available'))
      }
    } catch (err) {
      console.error("Failed to load active sellers list.")
    }
  }

  const connectSSE = () => {
    if (sseSourceRef.current) {
      sseSourceRef.current.close()
    }
    
    const source = new EventSource(`${BACKEND_URL}/api/v1/agent/chats/realtime-sse?token=${token}`)
    sseSourceRef.current = source
    
    source.onmessage = (event) => {
      const payload = JSON.parse(event.data)
      if (payload.type === 'new_message') {
        const msg = payload.data
        // If this message belongs to active chat, append it
        if (activeChat && activeChat.id === msg.conversation_id) {
          setMessages(prev => [...prev, msg])
        }
        // Reload chats list to update recent status
        loadChats()
      } else if (payload.type === 'chat_accepted' || payload.type === 'chat_rejected' || payload.type === 'chat_transferred' || payload.type === 'chat_closed') {
        loadChats()
        if (activeChat && activeChat.id === payload.data.conversation_id) {
          if (payload.type === 'chat_closed' || payload.type === 'chat_rejected') {
            setActiveChat(null)
            setMessages([])
          }
        }
      }
    }

    source.onerror = () => {
      console.warn("SSE connection closed. Reconnecting...")
    }
  }

  const loadMessages = async (chat: any) => {
    setActiveChat(chat)
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/agent/chats/${chat.id}/messages?token=${token}`)
      const result = await response.json()
      if (result.success) {
        setMessages(result.data)
      }
    } catch (err) {
      showToast('Error al cargar mensajes.', true)
    }
  }

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!messageInput.trim() || !activeChat) return
    const text = messageInput.trim()
    setMessageInput('')
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/agent/chats/${activeChat.id}/messages?token=${token}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: text })
      })
      const result = await response.json()
      if (!result.success) {
        showToast('Error al entregar el mensaje en WhatsApp.', true)
      }
    } catch (err) {
      showToast('Error de conexión al enviar.', true)
    }
  }

  const handleAcceptChat = async (chatId: string) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/agent/chats/${chatId}/accept?token=${token}`, {
        method: 'POST'
      })
      const result = await response.json()
      if (result.success) {
        showToast('Chat aceptado. Iniciando conversación.')
        loadChats()
      }
    } catch (err) {
      showToast('Error al aceptar conversación.', true)
    }
  }

  const handleCloseChat = async () => {
    if (!activeChat) return
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/agent/chats/${activeChat.id}/close?token=${token}`, {
        method: 'POST'
      })
      const result = await response.json()
      if (result.success) {
        showToast('Conversación finalizada con éxito.')
        setActiveChat(null)
        setMessages([])
        loadChats()
      }
    } catch (err) {
      showToast('Error al cerrar conversación.', true)
    }
  }

  const handleRejectChat = async () => {
    if (!activeChat) return
    const reason = prompt('Indica el motivo del rechazo:')
    if (!reason) return
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/agent/chats/${activeChat.id}/reject?token=${token}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason })
      })
      const result = await response.json()
      if (result.success) {
        showToast('Conversación rechazada.')
        setActiveChat(null)
        setMessages([])
        loadChats()
      }
    } catch (err) {
      showToast('Error al rechazar.', true)
    }
  }

  const handleTransferChat = async (targetId: string) => {
    if (!activeChat) return
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/agent/chats/${activeChat.id}/transfer?token=${token}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_seller_id: targetId })
      })
      const result = await response.json()
      if (result.success) {
        showToast('Conversación transferida.')
        setActiveChat(null)
        setMessages([])
        loadChats()
        setShowTransfer(false)
      } else {
        showToast(result.message, true)
      }
    } catch (err) {
      showToast('Error al transferir.', true)
    }
  }

  const handleSaveNote = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!noteInput.trim() || !activeChat) return
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/agent/chats/${activeChat.id}/notes?token=${token}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: noteInput })
      })
      const result = await response.json()
      if (result.success) {
        showToast('Nota guardada.')
        setNoteInput('')
      }
    } catch (err) {
      showToast('Error al guardar nota.', true)
    }
  }

  if (!token) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', width: '100%', minHeight: '100vh', background: '#0b141a' }}>
        <form onSubmit={handleLogin} style={{ background: '#202c33', padding: '2.5rem', borderRadius: '1rem', width: '400px', boxShadow: '0 10px 25px rgba(0,0,0,0.5)', border: '1px solid #222e35' }}>
          <h2 style={{ fontFamily: 'Outfit, sans-serif', color: '#00a884', marginBottom: '1.5rem', textAlign: 'center', fontSize: '1.75rem' }}>📞 Agente de Ventas</h2>
          {error && <div style={{ background: '#fef2f2', color: '#f15c6d', padding: '0.75rem', borderRadius: '0.5rem', marginBottom: '1rem', fontSize: '0.85rem' }}>{error}</div>}
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#8696a0', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Email del Agente</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="juan@ferreteria.com" required style={{ width: '100%', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid #222e35', background: '#111b21', color: 'white', outline: 'none' }} />
          </div>
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#8696a0', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Contraseña</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" required style={{ width: '100%', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid #222e35', background: '#111b21', color: 'white', outline: 'none' }} />
          </div>
          <button type="submit" style={{ width: '100%', padding: '0.85rem', borderRadius: '0.5rem', border: 'none', background: 'linear-gradient(135deg, #00a884, #008069)', color: 'white', fontWeight: 'bold', cursor: 'pointer', transition: 'all 0.3s' }}>Ingresar al Consola</button>
        </form>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', width: '100%', height: '100vh', background: '#0b141a', color: '#e9edef' }}>
      {toast && <div style={{ position: 'fixed', top: '2rem', right: '2rem', background: toast.isError ? '#f15c6d' : '#00a884', color: 'white', padding: '1rem 1.5rem', borderRadius: '0.5rem', boxShadow: '0 4px 15px rgba(0,0,0,0.4)', zIndex: 1000 }}>{toast.message}</div>}
      
      {/* Sidebar - Chats list */}
      <div style={{ width: '350px', background: '#111b21', borderRight: '1px solid #222e35', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '1.5rem', background: '#202c33', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #222e35' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', color: '#00a884', fontWeight: 'bold' }}>Consola Agente</h3>
            <span style={{ fontSize: '0.75rem', color: '#8696a0' }}>Disponible</span>
          </div>
          <button onClick={handleLogout} style={{ padding: '0.4rem 0.8rem', background: 'transparent', border: '1px solid #f15c6d', color: '#f15c6d', borderRadius: '0.25rem', fontSize: '0.8rem', cursor: 'pointer', fontWeight: 'bold' }}>Salir</button>
        </div>
        
        {/* Chats queue */}
        <div style={{ flexGrow: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '1rem', borderBottom: '1px solid #222e35' }}>
            <h4 style={{ fontSize: '0.85rem', color: '#8696a0', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>Mis Chats Activos ({assignedChats.length})</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {assignedChats.map(c => (
                <div key={c.id} onClick={() => loadMessages(c)} style={{
                  padding: '1rem',
                  borderRadius: '0.5rem',
                  background: activeChat && activeChat.id === c.id ? '#2a3942' : '#202c33',
                  cursor: 'pointer',
                  border: '1px solid #222e35',
                  transition: 'background 0.2s'
                }}>
                  <div style={{ fontWeight: 'bold', fontSize: '0.95rem' }}>+{c.phone}</div>
                  <div style={{ fontSize: '0.75rem', color: '#8696a0', marginTop: '0.25rem' }}>Estado: {c.status}</div>
                </div>
              ))}
              {assignedChats.length === 0 && <p style={{ fontSize: '0.8rem', color: '#8696a0', textAlign: 'center', padding: '1rem' }}>No tienes chats asignados.</p>}
            </div>
          </div>
          
          <div style={{ padding: '1rem' }}>
            <h4 style={{ fontSize: '0.85rem', color: '#8696a0', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>Cola de Espera ({waitingChats.length})</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {waitingChats.map(c => (
                <div key={c.id} style={{
                  padding: '1rem',
                  borderRadius: '0.5rem',
                  background: '#202c33',
                  border: '1px solid #222e35',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <div>
                    <div style={{ fontWeight: 'bold', fontSize: '0.95rem' }}>+{c.phone}</div>
                    <div style={{ fontSize: '0.7rem', color: '#8696a0' }}>Esperando en cola</div>
                  </div>
                  <button onClick={() => handleAcceptChat(c.id)} style={{ padding: '0.4rem 0.8rem', background: '#00a884', color: 'white', border: 'none', borderRadius: '0.25rem', fontWeight: 'bold', fontSize: '0.8rem', cursor: 'pointer' }}>Atender</button>
                </div>
              ))}
              {waitingChats.length === 0 && <p style={{ fontSize: '0.8rem', color: '#8696a0', textAlign: 'center', padding: '1rem' }}>No hay chats en espera.</p>}
            </div>
          </div>
        </div>
      </div>

      {/* Main Chat Panel */}
      <div style={{ flexGrow: 1, display: 'flex', flexDirection: 'column', background: '#0b141a' }}>
        {activeChat ? (
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            {/* Top Bar */}
            <div style={{ padding: '1rem 1.5rem', background: '#202c33', borderBottom: '1px solid #222e35', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 'bold' }}>+{activeChat.phone}</h3>
                <span style={{ fontSize: '0.75rem', color: '#00a884' }}>Atención Humana Activa</span>
              </div>
              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <button onClick={() => setShowTransfer(!showTransfer)} style={{ padding: '0.5rem 1rem', background: 'transparent', border: '1px solid #00a884', color: '#00a884', borderRadius: '0.25rem', fontSize: '0.85rem', cursor: 'pointer', fontWeight: 'bold' }}>Transferir</button>
                <button onClick={handleRejectChat} style={{ padding: '0.5rem 1rem', background: 'transparent', border: '1px solid #f15c6d', color: '#f15c6d', borderRadius: '0.25rem', fontSize: '0.85rem', cursor: 'pointer', fontWeight: 'bold' }}>Rechazar</button>
                <button onClick={handleCloseChat} style={{ padding: '0.5rem 1rem', background: '#00a884', border: 'none', color: 'white', borderRadius: '0.25rem', fontSize: '0.85rem', cursor: 'pointer', fontWeight: 'bold' }}>Cerrar Chat</button>
              </div>
            </div>

            {/* Transfer options overlay */}
            {showTransfer && (
              <div style={{ background: '#202c33', padding: '1rem', borderBottom: '1px solid #222e35', display: 'flex', gap: '1rem', alignItems: 'center' }}>
                <span style={{ fontSize: '0.85rem', color: '#8696a0' }}>Transferir a:</span>
                <select onChange={e => handleTransferChat(e.target.value)} defaultValue="" style={{ padding: '0.5rem', background: '#111b21', color: 'white', border: '1px solid #222e35', borderRadius: '0.25rem', outline: 'none' }}>
                  <option value="" disabled>Selecciona un vendedor...</option>
                  {sellers.filter(s => s.id !== activeChat.current_seller_id).map(s => (
                    <option key={s.id} value={s.id}>{s.name} ({s.team_zone})</option>
                  ))}
                </select>
                <button onClick={() => setShowTransfer(false)} style={{ padding: '0.4rem 0.8rem', background: 'transparent', border: 'none', color: '#8696a0', cursor: 'pointer' }}>Cancelar</button>
              </div>
            )}

            {/* Chat Pane */}
            <div style={{ flexGrow: 1, padding: '2rem', overflowY: 'auto', background: '#0b141a', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {messages.map((m, idx) => {
                const isOutbound = m.direction === 'outbound'
                return (
                  <div key={m.id || idx} style={{
                    maxWidth: '65%',
                    padding: '0.75rem 1rem',
                    borderRadius: '0.5rem',
                    alignSelf: isOutbound ? 'flex-end' : 'flex-start',
                    background: isOutbound ? '#005c4b' : '#202c33',
                    color: '#e9edef',
                    boxShadow: '0 1px 2px rgba(0,0,0,0.15)',
                    position: 'relative'
                  }}>
                    <div style={{ fontSize: '0.95rem' }}>{m.content}</div>
                    <div style={{ fontSize: '0.65rem', color: '#8696a0', marginTop: '0.25rem', textAlign: 'right' }}>
                      {m.role === 'seller' ? 'Asesor' : m.role === 'assistant' ? 'Bot' : 'Usuario'}
                    </div>
                  </div>
                )
              })}
              <div ref={messagesEndRef} />
            </div>

            {/* Note taking and Message input bar */}
            <div style={{ background: '#202c33', borderTop: '1px solid #222e35', padding: '1rem' }}>
              {/* Internal Notes form */}
              <form onSubmit={handleSaveNote} style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem', paddingBottom: '0.75rem', borderBottom: '1px solid #222e35' }}>
                <input type="text" value={noteInput} onChange={e => setNoteInput(e.target.value)} placeholder="Agregar nota interna sobre esta conversación..." style={{ flexGrow: 1, padding: '0.5rem 1rem', borderRadius: '0.25rem', border: '1px solid #222e35', background: '#111b21', color: 'white', outline: 'none', fontSize: '0.85rem' }} />
                <button type="submit" style={{ padding: '0.5rem 1rem', background: '#64748b', color: 'white', border: 'none', borderRadius: '0.25rem', fontWeight: 'bold', fontSize: '0.85rem', cursor: 'pointer' }}>Guardar Nota</button>
              </form>

              {/* Chat form */}
              <form onSubmit={handleSendMessage} style={{ display: 'flex', gap: '0.75rem' }}>
                <input type="text" value={messageInput} onChange={e => setMessageInput(e.target.value)} placeholder="Escribe un mensaje de respuesta para WhatsApp..." style={{ flexGrow: 1, padding: '0.85rem 1.25rem', borderRadius: '20px', border: '1px solid #222e35', background: '#2a3942', color: 'white', outline: 'none' }} />
                <button type="submit" style={{ width: '45px', height: '45px', background: '#00a884', border: 'none', borderRadius: '50%', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', fontSize: '1.2rem' }}>➤</button>
              </form>
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', color: '#8696a0', flexDirection: 'column', gap: '1rem' }}>
            <span style={{ fontSize: '4rem' }}>🦫</span>
            <h3>Consola de Atención al Cliente</h3>
            <p>Selecciona una conversación asignada o atiende un cliente en cola para comenzar.</p>
          </div>
        )}
      </div>
    </div>
  )
}
