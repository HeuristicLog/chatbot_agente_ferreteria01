import { useState, useEffect } from 'react'

const GATEWAY_URL = 'http://localhost:8095';
const CATALOG_WEBVIEW_URL = 'http://localhost:8085/catalogo';

export default function App() {
  const [phone, setPhone] = useState('593984407038')
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState<any[]>([])
  const [showWebview, setShowWebview] = useState(false)
  const [toast, setToast] = useState<string | null>(null)

  useEffect(() => {
    // Load local inbound history
    const stored = localStorage.getItem(`chat_history:${phone}`)
    if (stored) {
      setMessages(JSON.parse(stored))
    } else {
      setMessages([
        { 
          id: 'welcome', 
          direction: 'outbound', 
          message: '¡Hola! 👋 Soy Castor 🦫, el asistente virtual de Ferretería Castor.\n\nEstoy aquí para ayudarte con catálogo interactivo, pedidos y asesoría.',
          buttons: ['🛍️ Catálogo y Carrito', '📦 Mi pedido', '👨‍💼 Hablar con asesor']
        }
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
          setMessages(prev => {
            const inboundList = prev.filter(m => m.direction === 'inbound')
            const outboundList = result.data.map((m: any, idx: number) => {
              // Extract buttons if standard menu
              let btns: string[] = []
              if (m.message.includes('Catálogo') || m.message.includes('Castor')) {
                btns = ['🛍️ Catálogo y Carrito', '📦 Mi pedido', '👨‍💼 Hablar con asesor']
              }
              return {
                id: `out-${idx}-${m.timestamp}`,
                direction: 'outbound',
                message: m.message,
                buttons: btns,
                timestamp: m.timestamp
              }
            })
            
            const combined = [...inboundList, ...outboundList]
            const seen = new Set()
            const unique = combined.filter(m => {
              const key = `${m.direction}:${m.message}`
              if (seen.has(key)) return false
              seen.add(key)
              return true
            })
            
            localStorage.setItem(`chat_history:${phone}`, JSON.stringify(unique))
            return unique
          })
        }
      } catch {
        // Gateway might be offline during build
      }
    }, 1500)
    
    return () => clearInterval(interval)
  }, [phone])

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(null), 3000)
  }

  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || message).trim()
    if (!text) return
    setMessage('')
    
    const msgId = `sim-msg-${Math.random().toString(36).substring(2, 9)}`
    
    // Check if clicking catalog button
    if (text.includes('Catálogo') || text.includes('Carrito') || text.includes('Tienda')) {
      // Auto trigger In-App Webview sheet for high-end demo
      setShowWebview(true)
    }

    const payload = {
      phone,
      message: text,
      message_id: msgId,
      metadata: { 
        provider: "meta",
        interactive_id: text.includes('Catálogo') ? 'flow_catalogo' : (text.includes('pedido') ? 'flow_pedido' : (text.includes('asesor') ? 'flow_asesor' : undefined))
      }
    }
    
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
      if (result.status === 'received' || result.status === 'processed') {
        showToast('Mensaje procesado.')
      }
    } catch {
      showToast('Error al conectar con la Gateway.')
    }
  }

  const handleClearHistory = () => {
    localStorage.removeItem(`chat_history:${phone}`)
    setMessages([
      { 
        id: 'welcome', 
        direction: 'outbound', 
        message: '¡Hola! 👋 Soy Castor 🦫, el asistente virtual de Ferretería Castor.\n\nEstoy aquí para ayudarte con catálogo interactivo, pedidos y asesoría.',
        buttons: ['🛍️ Catálogo y Carrito', '📦 Mi pedido', '👨‍💼 Hablar con asesor']
      }
    ])
    setShowWebview(false)
  }

  return (
    <div style={{ display: 'flex', width: '100%', height: '100vh', background: '#0b141a', color: '#e9edef', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      {toast && (
        <div style={{ position: 'fixed', top: '1.5rem', right: '1.5rem', background: '#00a884', color: 'white', padding: '0.75rem 1.25rem', borderRadius: '0.5rem', zIndex: 9999, fontWeight: 600, boxShadow: '0 4px 12px rgba(0,0,0,0.3)' }}>
          {toast}
        </div>
      )}
      
      {/* Control Panel Lateral */}
      <div style={{ width: '360px', background: '#111b21', borderRight: '1px solid #222e35', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.5rem', overflowY: 'auto' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.5rem' }}>🦫</span>
            <div>
              <h2 style={{ color: '#00a884', fontSize: '1.1rem', margin: 0, fontWeight: 700 }}>Ferretería Castor</h2>
              <p style={{ fontSize: '0.75rem', color: '#8696a0', margin: 0 }}>Simulador Móvil WhatsApp</p>
            </div>
          </div>
        </div>

        {/* Acceso Rápido al Webview */}
        <div style={{ background: 'linear-gradient(135deg, #0f766e, #065f46)', padding: '1rem', borderRadius: '0.75rem', color: 'white', boxShadow: '0 4px 12px rgba(15,118,110,0.25)' }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span>🛍️</span> In-App Browser (Jelou.ia Style)
          </div>
          <p style={{ fontSize: '0.72rem', opacity: 0.9, marginBottom: '0.75rem', lineHeight: 1.3 }}>
            Abre la ventana emergente interna de productos y compras directamente en el visor del teléfono.
          </p>
          <button 
            onClick={() => setShowWebview(prev => !prev)} 
            style={{ width: '100%', padding: '0.6rem', background: 'white', color: '#0f766e', border: 'none', borderRadius: '0.5rem', fontWeight: 700, fontSize: '0.8rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.4rem' }}
          >
            {showWebview ? '✕ Cerrar In-App Webview' : '✨ Abrir In-App Webview'}
          </button>
        </div>
        
        {/* Selector de Teléfono */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: '#8696a0', marginBottom: '0.4rem', fontWeight: 600 }}>Número del Cliente en Simulación</label>
            <select 
              value={phone} 
              onChange={e => setPhone(e.target.value)} 
              style={{ width: '100%', padding: '0.65rem', borderRadius: '0.5rem', border: '1px solid #222e35', background: '#202c33', color: 'white', outline: 'none', fontSize: '0.8rem' }}
            >
              <option value="593984407038">+593 98 440 7038 (Kevin - Teléfono Principal)</option>
              <option value="593988888888">+593 98 888 8888 (Cliente Demo 1)</option>
              <option value="593987654321">+593 98 765 4321 (Cliente Demo 2)</option>
            </select>
          </div>

          {/* Botones de Prueba Rápida */}
          <div style={{ background: '#202c33', padding: '0.85rem', borderRadius: '0.5rem', border: '1px solid #222e35' }}>
            <span style={{ fontSize: '0.75rem', color: '#8696a0', fontWeight: 600, display: 'block', marginBottom: '0.5rem' }}>Mensajes Rápidos</span>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem' }}>
              <button onClick={() => handleSendMessage('hola')} style={{ padding: '0.5rem', background: '#2a3942', color: '#e9edef', border: '1px solid #3b4a54', borderRadius: '0.35rem', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}>"hola"</button>
              <button onClick={() => handleSendMessage('🛍️ Catálogo y Carrito')} style={{ padding: '0.5rem', background: '#2a3942', color: '#00a884', border: '1px solid #3b4a54', borderRadius: '0.35rem', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}>"🛍️ Catálogo"</button>
              <button onClick={() => handleSendMessage('📦 Mi pedido')} style={{ padding: '0.5rem', background: '#2a3942', color: '#e9edef', border: '1px solid #3b4a54', borderRadius: '0.35rem', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}>"📦 Mi pedido"</button>
              <button onClick={() => handleSendMessage('👨‍💼 Hablar con asesor')} style={{ padding: '0.5rem', background: '#2a3942', color: '#e9edef', border: '1px solid #3b4a54', borderRadius: '0.35rem', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}>"👨‍💼 Asesor"</button>
            </div>
          </div>
        </div>

        <button 
          onClick={handleClearHistory} 
          style={{ marginTop: 'auto', padding: '0.65rem', background: 'transparent', border: '1px solid #f15c6d', color: '#f15c6d', borderRadius: '0.5rem', fontWeight: 600, fontSize: '0.8rem', cursor: 'pointer' }}
        >
          Borrar Historial
        </button>
      </div>

      {/* Frame del Teléfono Móvil (Mockup) */}
      <div style={{ flexGrow: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1.5rem', background: '#080d10' }}>
        <div style={{ 
          width: '390px', 
          height: '780px', 
          maxHeight: '94vh', 
          background: '#0b141a', 
          borderRadius: '42px', 
          border: '10px solid #202c33', 
          boxShadow: '0 25px 60px -15px rgba(0,0,0,0.8), 0 0 0 2px #3b4a54', 
          display: 'flex', 
          flexDirection: 'column', 
          position: 'relative', 
          overflow: 'hidden' 
        }}>
          
          {/* Barra de Estado del Móvil */}
          <div style={{ height: '34px', background: '#202c33', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 1.25rem', fontSize: '0.72rem', color: '#e9edef', fontWeight: 600 }}>
            <span>9:41</span>
            <div style={{ width: '80px', height: '14px', background: '#0b141a', borderRadius: '10px' }}></div>
            <div style={{ display: 'flex', gap: '0.3rem', alignItems: 'center' }}>
              <span>5G</span>
              <span>100%</span>
            </div>
          </div>

          {/* WhatsApp Header */}
          <div style={{ padding: '0.65rem 1rem', background: '#202c33', display: 'flex', gap: '0.75rem', alignItems: 'center', borderBottom: '1px solid #2a3942' }}>
            <div style={{ width: '36px', height: '36px', borderRadius: '50%', background: 'linear-gradient(135deg, #0f766e, #10b981)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.1rem', fontWeight: 700, color: 'white', boxShadow: '0 2px 6px rgba(0,0,0,0.2)' }}>
              🦫
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#e9edef', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                Ferretería Castor
                <span style={{ fontSize: '0.7rem', color: '#00a884' }}>✓</span>
              </div>
              <span style={{ fontSize: '0.7rem', color: '#00a884' }}>Cuenta de empresa • En línea</span>
            </div>
          </div>

          {/* Chat Messages Thread */}
          <div style={{ flexGrow: 1, padding: '1rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.6rem', backgroundImage: 'radial-gradient(circle, #182229 10%, transparent 11%)', backgroundSize: '14px 14px' }}>
            {messages.map((m, idx) => {
              const isUser = m.direction === 'inbound'
              return (
                <div key={m.id || idx} style={{ alignSelf: isUser ? 'flex-end' : 'flex-start', maxWidth: '82%', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <div style={{
                    padding: '0.6rem 0.85rem',
                    borderRadius: isUser ? '12px 0 12px 12px' : '0 12px 12px 12px',
                    background: isUser ? '#005c4b' : '#202c33',
                    color: '#e9edef',
                    fontSize: '0.82rem',
                    lineHeight: 1.4,
                    boxShadow: '0 1px 2px rgba(0,0,0,0.2)',
                    whiteSpace: 'pre-line'
                  }}>
                    {m.message}
                  </div>

                  {/* Interactive WhatsApp Buttons */}
                  {!isUser && m.buttons && m.buttons.length > 0 && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', marginTop: '0.15rem' }}>
                      {m.buttons.map((btnText: string, bIdx: number) => (
                        <button
                          key={bIdx}
                          onClick={() => handleSendMessage(btnText)}
                          style={{
                            width: '100%',
                            padding: '0.55rem',
                            background: '#202c33',
                            border: '1px solid #2a3942',
                            color: '#00a884',
                            borderRadius: '8px',
                            fontSize: '0.78rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '0.35rem',
                            boxShadow: '0 1px 2px rgba(0,0,0,0.15)',
                            transition: 'all 0.15s ease'
                          }}
                        >
                          {btnText}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Chat Footer Input */}
          <form 
            onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }} 
            style={{ padding: '0.6rem 0.75rem', background: '#202c33', display: 'flex', gap: '0.5rem', alignItems: 'center', borderTop: '1px solid #2a3942' }}
          >
            <input 
              type="text" 
              value={message} 
              onChange={e => setMessage(e.target.value)} 
              placeholder="Escribe un mensaje..." 
              style={{ flexGrow: 1, padding: '0.65rem 0.9rem', borderRadius: '18px', border: '1px solid #2a3942', background: '#2a3942', color: 'white', outline: 'none', fontSize: '0.82rem' }} 
            />
            <button 
              type="submit" 
              style={{ width: '36px', height: '36px', borderRadius: '50%', background: '#00a884', border: 'none', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.9rem', cursor: 'pointer' }}
            >
              ➤
            </button>
          </form>

          {/* 🪟 IN-APP BROWSER SLIDE-UP SHEET (Jelou.ia Style) */}
          <div style={{
            position: 'absolute',
            inset: 0,
            background: 'white',
            zIndex: 100,
            transform: showWebview ? 'translateY(0)' : 'translateY(100%)',
            transition: 'transform 0.35s cubic-bezier(0.16, 1, 0.3, 1)',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 -10px 40px rgba(0,0,0,0.5)'
          }}>
            {/* Top Bar del Visor Interno de WhatsApp */}
            <div style={{ 
              height: '48px', 
              background: '#111b21', 
              color: '#e9edef', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between', 
              padding: '0 1rem', 
              borderBottom: '1px solid #222e35',
              fontSize: '0.8rem'
            }}>
              <button 
                onClick={() => setShowWebview(false)} 
                style={{ background: 'transparent', border: 'none', color: '#8696a0', fontSize: '1.2rem', cursor: 'pointer', padding: '0.25rem' }}
              >
                ✕
              </button>
              
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <span style={{ fontWeight: 700, fontSize: '0.78rem', color: '#e9edef' }}>WhatsApp</span>
                <span style={{ fontSize: '0.65rem', color: '#8696a0', display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                  🔒 catalogo.ferreteriacastor.com
                </span>
              </div>

              <div style={{ color: '#8696a0', fontSize: '1rem' }}>⋮</div>
            </div>

            {/* Iframe del Catálogo Oficial */}
            <iframe 
              src={`${CATALOG_WEBVIEW_URL}?phone=${phone}&sucursal=Centro`}
              style={{ width: '100%', flexGrow: 1, border: 'none' }}
              title="Catálogo In-App Castor"
            />
          </div>

        </div>
      </div>
    </div>
  )
}
