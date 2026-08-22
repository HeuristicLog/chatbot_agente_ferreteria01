import React, { useState, useEffect } from 'react'

const GATEWAY_URL = 'http://localhost:8095';

export default function App() {
  const [phone, setPhone] = useState('593988888888')
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState<any[]>([])
  
  // Simulation helpers
  const [duplicateMessageId, setDuplicateMessageId] = useState<string | null>(null)
  const [lastMessageText, setLastMessageText] = useState('')
  const [mediaUrl, setMediaUrl] = useState('')
  const [mediaType, setMediaType] = useState('')
  const [toast, setToast] = useState<string | null>(null)

  useEffect(() => {
    // Load local inbound history
    const stored = localStorage.getItem(`chat_history:${phone}`)
    if (stored) {
      setMessages(JSON.parse(stored))
    } else {
      setMessages([
        { id: 'welcome', direction: 'outbound', message: '¡Hola! Escribe un mensaje para conversar con Castor.' }
      ])
    }
  }, [phone])

  // Poll gateway for outbound messages sent by chatbot
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${GATEWAY_URL}/outbound?phone=${phone}`)
        const result = await response.json()
        if (result.success && result.data.length > 0) {
          // Merge local inbound and fetched outbound messages
          setMessages(prev => {
            const inboundList = prev.filter(m => m.direction === 'inbound')
            const outboundList = result.data.map((m: any, idx: number) => ({
              id: `out-${idx}-${m.timestamp}`,
              direction: 'outbound',
              message: m.message,
              timestamp: m.timestamp
            }))
            
            // Combine and sort by timestamp
            const combined = [...inboundList, ...outboundList]
            // Simple deduplication based on text & direction if timestamps are off
            const seen = new Set()
            const unique = combined.filter(m => {
              const key = `${m.direction}:${m.message}`
              if (seen.has(key)) return false
              seen.add(key)
              return true
            })
            
            // Save to local storage
            localStorage.setItem(`chat_history:${phone}`, JSON.stringify(unique))
            return unique
          })
        }
      } catch (err) {
        // Gateway might be offline during build
      }
    }, 1500)
    
    return () => clearInterval(interval)
  }, [phone])

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(null), 3000)
  }

  const handleSendMessage = async (e?: React.FormEvent, customId?: string) => {
    if (e) e.preventDefault()
    if (!message.trim()) return
    const text = message.trim()
    setMessage('')
    setLastMessageText(text)
    
    const msgId = customId || `sim-msg-${Math.random().toString(36).substring(2, 9)}`
    if (!customId) {
      setDuplicateMessageId(msgId)
    }
    
    const payload = {
      phone,
      message: text,
      message_id: msgId,
      media_url: mediaUrl || null,
      media_type: mediaType || null,
      metadata: { provider: "mock" }
    }
    
    // Add to local messages list
    const newMsgObj = {
      id: msgId,
      direction: 'inbound',
      message: text,
      timestamp: new Date().toISOString()
    }
    
    setMessages(prev => {
      const updated = [...prev, newMsgObj]
      localStorage.setItem(`chat_history:${phone}`, JSON.stringify(updated))
      return updated
    })
    
    try {
      showToast('Enviando mensaje...')
      const response = await fetch(`${GATEWAY_URL}/webhooks/whatsapp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      const result = await response.json()
      if (result.status === 'received') {
        showToast('Mensaje recibido por la Gateway.')
      } else if (result.status === 'duplicate') {
        showToast('Webhook detectó mensaje duplicado (idempotencia ok).')
      }
    } catch (err) {
      showToast('Error al conectar con la Gateway.')
    }
  }

  const handleSimulateDuplicate = () => {
    if (!duplicateMessageId || !lastMessageText) {
      showToast('Envía un mensaje primero.')
      return
    }
    // Resend the exact same message with the exact same ID
    setMessage(lastMessageText)
    setTimeout(() => {
      handleSendMessage(undefined, duplicateMessageId)
    }, 200)
  }

  const handleClearHistory = () => {
    localStorage.removeItem(`chat_history:${phone}`)
    setMessages([
      { id: 'welcome', direction: 'outbound', message: 'Historial borrado. Conversación reiniciada.' }
    ])
  }

  return (
    <div style={{ display: 'flex', width: '100%', height: '100vh', background: '#0c1317', color: '#e9edef' }}>
      {toast && <div style={{ position: 'fixed', top: '2rem', right: '2rem', background: '#00a884', color: 'white', padding: '1rem 1.5rem', borderRadius: '0.5rem', zIndex: 1000 }}>{toast}</div>}
      
      {/* Control Panel */}
      <div style={{ width: '380px', background: '#111b21', borderRight: '1px solid #222e35', padding: '2rem 1.5rem', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
        <div>
          <h2 style={{ color: '#00a884', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>💬 WhatsApp Sandbox</h2>
          <p style={{ fontSize: '0.75rem', color: '#8696a0', marginTop: '0.25rem' }}>Simulador de Cliente</p>
        </div>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#8696a0', marginBottom: '0.5rem', fontWeight: 'bold' }}>Número de Teléfono</label>
            <select value={phone} onChange={e => setPhone(e.target.value)} style={{ width: '100%', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid #222e35', background: '#202c33', color: 'white', outline: 'none' }}>
              <option value="593988888888">Cliente 1 (+593 98 888 8888) - PED-12345</option>
              <option value="593987654321">Cliente 2 (+593 98 765 4321) - PED-1001</option>
              <option value="593999888777">Cliente 3 (+593 99 988 8777) - PED-1002</option>
            </select>
          </div>

          <div style={{ background: '#202c33', padding: '1rem', borderRadius: '0.5rem', border: '1px solid #222e35' }}>
            <h4 style={{ fontSize: '0.85rem', color: '#00a884', marginBottom: '0.75rem' }}>Simulación Avanzada</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <button onClick={handleSimulateDuplicate} disabled={!duplicateMessageId} style={{ width: '100%', padding: '0.6rem', background: duplicateMessageId ? '#00a884' : '#475569', color: 'white', border: 'none', borderRadius: '0.25rem', cursor: duplicateMessageId ? 'pointer' : 'not-allowed', fontWeight: 'bold', fontSize: '0.8rem' }}>Re-enviar Último (Duplicar ID)</button>
              
              <div style={{ borderTop: '1px solid #222e35', marginTop: '0.5rem', paddingTop: '0.5rem' }}>
                <label style={{ display: 'block', fontSize: '0.75rem', color: '#8696a0', marginBottom: '0.25rem' }}>URL del Archivo (Opcional)</label>
                <input type="text" value={mediaUrl} onChange={e => setMediaUrl(e.target.value)} placeholder="https://example.com/evidence.jpg" style={{ width: '100%', padding: '0.5rem', background: '#111b21', color: 'white', border: '1px solid #222e35', borderRadius: '0.25rem', fontSize: '0.8rem', marginBottom: '0.5rem', outline: 'none' }} />
                
                <label style={{ display: 'block', fontSize: '0.75rem', color: '#8696a0', marginBottom: '0.25rem' }}>Tipo del Archivo (image/pdf)</label>
                <input type="text" value={mediaType} onChange={e => setMediaType(e.target.value)} placeholder="image/jpeg" style={{ width: '100%', padding: '0.5rem', background: '#111b21', color: 'white', border: '1px solid #222e35', borderRadius: '0.25rem', fontSize: '0.8rem', outline: 'none' }} />
              </div>
            </div>
          </div>
        </div>

        <button onClick={handleClearHistory} style={{ marginTop: 'auto', padding: '0.75rem', background: 'transparent', border: '1px solid #f15c6d', color: '#f15c6d', borderRadius: '0.5rem', fontWeight: 'bold', cursor: 'pointer' }}>Borrar Historial Local</button>
      </div>

      {/* WhatsApp Chat Pane */}
      <div style={{ flexGrow: 1, display: 'flex', flexDirection: 'column', background: '#0b141a' }}>
        {/* Top Header */}
        <div style={{ padding: '1rem 1.5rem', background: '#202c33', display: 'flex', gap: '1rem', alignItems: 'center', borderBottom: '1px solid #222e35' }}>
          <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: '#00a884', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.25rem', fontWeight: 'bold', color: 'white' }}>C</div>
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 'bold' }}>Ferretería Castor Chatbot</h3>
            <span style={{ fontSize: '0.75rem', color: '#8696a0' }}>Online</span>
          </div>
        </div>

        {/* Message Area */}
        <div style={{ flexGrow: 1, padding: '2rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.75rem', backgroundImage: 'radial-gradient(circle, #0c151c 10%, transparent 11%)', backgroundSize: '15px 15px' }}>
          {messages.map((m, idx) => {
            const isUser = m.direction === 'inbound'
            return (
              <div key={m.id || idx} style={{
                maxWidth: '65%',
                padding: '0.75rem 1rem',
                borderRadius: '0.5rem',
                alignSelf: isUser ? 'flex-end' : 'flex-start',
                background: isUser ? '#005c4b' : '#202c33',
                color: '#e9edef',
                boxShadow: '0 1px 2px rgba(0,0,0,0.15)',
                whiteSpace: 'pre-line'
              }}>
                <div>{m.message}</div>
                {m.id && isUser && <div style={{ fontSize: '0.6rem', color: '#8696a0', marginTop: '0.25rem', textAlign: 'right' }}>ID: {m.id.substring(0, 10)}...</div>}
              </div>
            )
          })}
        </div>

        {/* Footer Chat Form */}
        <form onSubmit={handleSendMessage} style={{ padding: '1rem', background: '#202c33', display: 'flex', gap: '1rem', borderTop: '1px solid #222e35' }}>
          <input type="text" value={message} onChange={e => setMessage(e.target.value)} required placeholder="Escribe un mensaje..." style={{ flexGrow: 1, padding: '0.85rem 1.25rem', borderRadius: '20px', border: '1px solid #222e35', background: '#2a3942', color: 'white', outline: 'none' }} />
          <button type="submit" style={{ width: '45px', height: '45px', borderRadius: '50%', background: '#00a884', border: 'none', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.2rem', cursor: 'pointer' }}>➤</button>
        </form>
      </div>
    </div>
  )
}
