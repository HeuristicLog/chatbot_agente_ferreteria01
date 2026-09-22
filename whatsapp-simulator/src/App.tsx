import { useState, useEffect } from 'react'

const GATEWAY_URL = 'http://localhost:8095';

export default function App() {
  const [phone, setPhone] = useState('593984407038')
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState<any[]>([])
  const [showWebview, setShowWebview] = useState(false)
  const [catalogEngine, setCatalogEngine] = useState<'flutter' | 'yelow'>('yelow')
  const [toast, setToast] = useState<string | null>(null)

  const catalogUrl = catalogEngine === 'flutter' 
    ? 'http://localhost:8092' 
    : `http://localhost:8085/catalogo?phone=${phone}&sucursal=Centro`;

  useEffect(() => {
    // Load local chat history
    const stored = localStorage.getItem(`chat_history:${phone}`)
    if (stored) {
      setMessages(JSON.parse(stored))
    } else {
      setMessages([
        { 
          id: 'welcome', 
          direction: 'outbound', 
          message: '¡Hola! 👋 Soy Castor 🦫, el asistente virtual de Ferretería Castor.\n\n¿En qué podemos ayudarte hoy? Explora nuestro catálogo interactivo sin salir de WhatsApp.',
          buttons: ['🛍️ Ver Catálogo y Comprar', '📦 Consultar mi Pedido', '👨‍💼 Hablar con Asesor']
        }
      ])
    }
  }, [phone])

  // Listen to postMessage from in-app catalog iframe
  useEffect(() => {
    const handleFrameMessage = (event: MessageEvent) => {
      try {
        if (event.data && typeof event.data === 'object') {
          if (event.data.type === 'ORDER_PLACED' || event.data.order_number) {
            setShowWebview(false);
            const orderNum = event.data.order_number || '#CAST-2026-DEMO';
            const total = event.data.total ? `$${event.data.total}` : '';
            const confirmMsg = `✅ *¡Pedido Confirmado!* 🎉\n\nTu orden *${orderNum}* por un valor de *${total}* ha sido registrada exitosamente en Ferretería Castor.\n\nEn breve un asesor despachará tu solicitud.`;
            setMessages(prev => {
              const updated = [...prev, {
                id: `order-conf-${Date.now()}`,
                direction: 'outbound',
                message: confirmMsg,
                timestamp: new Date().toISOString()
              }];
              localStorage.setItem(`chat_history:${phone}`, JSON.stringify(updated));
              return updated;
            });
            showToast(`¡Orden ${orderNum} registrada!`);
          }
        }
      } catch (e) {
        console.error(e);
      }
    };

    window.addEventListener('message', handleFrameMessage);
    return () => window.removeEventListener('message', handleFrameMessage);
  }, [phone]);

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
              let btns: string[] = []
              if (m.message.includes('Catálogo') || m.message.includes('Castor') || m.message.includes('Hola')) {
                btns = ['🛍️ Ver Catálogo y Comprar', '📦 Consultar mi Pedido', '👨‍💼 Hablar con Asesor']
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
        // Gateway polling
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
    
    // Si el usuario presiona el botón del catálogo, abrimos el In-App Webview integrado en WhatsApp
    if (text.includes('Catálogo') || text.includes('Carrito') || text.includes('Comprar') || text.toLowerCase().includes('catalogo')) {
      setShowWebview(true)
    }

    const payload = {
      phone,
      message: text,
      message_id: msgId,
      metadata: { 
        provider: "meta",
        interactive_id: text.includes('Catálogo') ? 'flow_catalogo' : (text.includes('Pedido') ? 'flow_pedido' : (text.includes('Asesor') ? 'flow_asesor' : undefined))
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
      showToast('Enviando a WhatsApp...')
      const response = await fetch(`${GATEWAY_URL}/webhooks/whatsapp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      const result = await response.json()
      if (result.status === 'received' || result.status === 'processed') {
        showToast('Mensaje entregado.')
      }
    } catch {
      showToast('Error de conexión.')
    }
  }

  const handleClearHistory = () => {
    localStorage.removeItem(`chat_history:${phone}`)
    setMessages([
      { 
        id: 'welcome', 
        direction: 'outbound', 
        message: '¡Hola! 👋 Soy Castor 🦫, el asistente virtual de Ferretería Castor.\n\n¿En qué podemos ayudarte hoy? Explora nuestro catálogo interactivo sin salir de WhatsApp.',
        buttons: ['🛍️ Ver Catálogo y Comprar', '📦 Consultar mi Pedido', '👨‍💼 Hablar con Asesor']
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
      <div style={{ width: '360px', background: '#111b21', borderRight: '1px solid #222e35', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.25rem', overflowY: 'auto' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.5rem' }}>🦫</span>
            <div>
              <h2 style={{ color: '#00a884', fontSize: '1.1rem', margin: 0, fontWeight: 700 }}>Ferretería Castor</h2>
              <p style={{ fontSize: '0.75rem', color: '#8696a0', margin: 0 }}>Simulador Oficial WhatsApp & In-App</p>
            </div>
          </div>
        </div>

        {/* Acceso Rápido al Webview */}
        <div style={{ background: 'linear-gradient(135deg, #0f766e, #065f46)', padding: '1rem', borderRadius: '0.75rem', color: 'white', boxShadow: '0 4px 12px rgba(15,118,110,0.25)' }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span>🛍️</span> In-App Browser (Navegación Interna)
          </div>
          <p style={{ fontSize: '0.72rem', opacity: 0.9, marginBottom: '0.75rem', lineHeight: 1.3 }}>
            Abre la tienda interactiva directamente dentro de WhatsApp sin salir de la conversación.
          </p>
          <button 
            onClick={() => setShowWebview(prev => !prev)} 
            style={{ width: '100%', padding: '0.6rem', background: 'white', color: '#0f766e', border: 'none', borderRadius: '0.5rem', fontWeight: 700, fontSize: '0.8rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.4rem' }}
          >
            {showWebview ? '✕ Cerrar Catálogo In-App' : '✨ Abrir Catálogo In-App'}
          </button>
        </div>

        {/* Selector de Motor de Catálogo */}
        <div style={{ background: '#202c33', padding: '0.85rem', borderRadius: '0.5rem', border: '1px solid #222e35' }}>
          <label style={{ display: 'block', fontSize: '0.75rem', color: '#8696a0', marginBottom: '0.4rem', fontWeight: 600 }}>Motor del Catálogo In-App</label>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button 
              onClick={() => setCatalogEngine('yelow')} 
              style={{ flex: 1, padding: '0.5rem', borderRadius: '0.35rem', border: catalogEngine === 'yelow' ? '2px solid #00a884' : '1px solid #3b4a54', background: catalogEngine === 'yelow' ? '#005c4b' : '#2a3942', color: 'white', fontSize: '0.72rem', fontWeight: 700, cursor: 'pointer' }}
            >
              ⚡ In-App Webview
            </button>
            <button 
              onClick={() => setCatalogEngine('flutter')} 
              style={{ flex: 1, padding: '0.5rem', borderRadius: '0.35rem', border: catalogEngine === 'flutter' ? '2px solid #00a884' : '1px solid #3b4a54', background: catalogEngine === 'flutter' ? '#005c4b' : '#2a3942', color: 'white', fontSize: '0.72rem', fontWeight: 700, cursor: 'pointer' }}
            >
              🦫 Flutter Web
            </button>
          </div>
        </div>
        
        {/* Selector de Teléfono */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: '#8696a0', marginBottom: '0.4rem', fontWeight: 600 }}>Número del Cliente</label>
            <select 
              value={phone} 
              onChange={e => setPhone(e.target.value)} 
              style={{ width: '100%', padding: '0.65rem', borderRadius: '0.5rem', border: '1px solid #222e35', background: '#202c33', color: 'white', outline: 'none', fontSize: '0.8rem' }}
            >
              <option value="593984407038">+593 98 440 7038 (Kevin - Teléfono)</option>
              <option value="593988921136">+593 98 892 1136 (WhatsApp Demo)</option>
              <option value="593988888888">+593 98 888 8888 (Cliente Demo)</option>
            </select>
          </div>

          {/* Botones de Acción Rápida */}
          <div style={{ background: '#202c33', padding: '0.85rem', borderRadius: '0.5rem', border: '1px solid #222e35' }}>
            <span style={{ fontSize: '0.75rem', color: '#8696a0', fontWeight: 600, display: 'block', marginBottom: '0.5rem' }}>Acciones Rápidas</span>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem' }}>
              <button onClick={() => handleSendMessage('hola')} style={{ padding: '0.5rem', background: '#2a3942', color: '#e9edef', border: '1px solid #3b4a54', borderRadius: '0.35rem', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}>"hola"</button>
              <button onClick={() => handleSendMessage('🛍️ Ver Catálogo y Comprar')} style={{ padding: '0.5rem', background: '#2a3942', color: '#00a884', border: '1px solid #3b4a54', borderRadius: '0.35rem', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}>"🛍️ Catálogo"</button>
              <button onClick={() => handleSendMessage('📦 Consultar mi Pedido')} style={{ padding: '0.5rem', background: '#2a3942', color: '#e9edef', border: '1px solid #3b4a54', borderRadius: '0.35rem', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}>"📦 Pedido"</button>
              <button onClick={() => handleSendMessage('👨‍💼 Hablar con Asesor')} style={{ padding: '0.5rem', background: '#2a3942', color: '#e9edef', border: '1px solid #3b4a54', borderRadius: '0.35rem', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}>"👨‍💼 Asesor"</button>
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

      {/* Frame del Teléfono Móvil (Mockup Realista) */}
      <div style={{ flexGrow: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1.5rem', background: '#080d10' }}>
        <div style={{ 
          width: '390px', 
          height: '780px', 
          maxHeight: '94vh', 
          background: '#0b141a', 
          borderRadius: '44px', 
          border: '10px solid #202c33', 
          boxShadow: '0 25px 60px -15px rgba(0,0,0,0.8), 0 0 0 2px #3b4a54', 
          display: 'flex', 
          flexDirection: 'column', 
          position: 'relative', 
          overflow: 'hidden' 
        }}>
          
          {/* Dynamic Island / Barra Superior del Móvil */}
          <div style={{ height: '36px', background: '#202c33', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 1.25rem', fontSize: '0.72rem', color: '#e9edef', fontWeight: 600, zIndex: 110 }}>
            <span>9:41</span>
            <div style={{ width: '90px', height: '18px', background: '#0b141a', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#1e293b', marginRight: '4px' }}></div>
              <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#0ea5e9' }}></div>
            </div>
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
              <span style={{ fontSize: '0.7rem', color: '#00a884' }}>Cuenta de empresa oficial • En línea</span>
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

                  {/* WhatsApp Interactive Buttons */}
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
              placeholder="Escribe un mensaje o 'catálogo'..." 
              style={{ flexGrow: 1, padding: '0.65rem 0.9rem', borderRadius: '18px', border: '1px solid #2a3942', background: '#2a3942', color: 'white', outline: 'none', fontSize: '0.82rem' }} 
            />
            <button 
              type="submit" 
              style={{ width: '36px', height: '36px', borderRadius: '50%', background: '#00a884', border: 'none', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.9rem', cursor: 'pointer' }}
            >
              ➤
            </button>
          </form>

          {/* 🪟 IN-APP BROWSER SLIDE-UP SHEET (Navegación Interna sin salir de WhatsApp) */}
          <div style={{
            position: 'absolute',
            inset: 0,
            background: '#f8fafc',
            zIndex: 100,
            transform: showWebview ? 'translateY(0)' : 'translateY(100%)',
            transition: 'transform 0.35s cubic-bezier(0.16, 1, 0.3, 1)',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 -10px 40px rgba(0,0,0,0.5)'
          }}>
            {/* Top Bar del Visor Interno de WhatsApp */}
            <div style={{ 
              height: '46px', 
              background: '#111b21', 
              color: '#e9edef', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between', 
              padding: '0 1rem', 
              borderBottom: '1px solid #222e35',
              fontSize: '0.8rem',
              boxShadow: '0 2px 8px rgba(0,0,0,0.2)'
            }}>
              <button 
                onClick={() => setShowWebview(false)} 
                style={{ background: 'transparent', border: 'none', color: '#8696a0', fontSize: '1.2rem', cursor: 'pointer', padding: '0.25rem' }}
                title="Cerrar Catálogo"
              >
                ✕
              </button>
              
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <span style={{ fontWeight: 700, fontSize: '0.78rem', color: '#e9edef' }}>WhatsApp Business</span>
                <span style={{ fontSize: '0.65rem', color: '#00a884', display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                  🔒 catalogo.ferreteriacastor.com
                </span>
              </div>

              <button 
                onClick={() => setShowWebview(false)} 
                style={{ background: '#202c33', border: '1px solid #3b4a54', color: '#00a884', fontSize: '0.7rem', borderRadius: '4px', padding: '0.2rem 0.5rem', cursor: 'pointer', fontWeight: 600 }}
              >
                Listo
              </button>
            </div>

            {/* Iframe del Catálogo Oficial */}
            <iframe 
              src={catalogUrl}
              style={{ width: '100%', flexGrow: 1, border: 'none', background: '#f8fafc' }}
              title="Catálogo In-App Castor"
              allow="camera; microphone; geolocation"
            />
          </div>

        </div>
      </div>
    </div>
  )
}
