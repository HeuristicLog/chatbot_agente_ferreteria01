import { useState, useEffect } from 'react'

const GATEWAY_URL = 'http://localhost:8095';

export default function App() {
  const [phone, setPhone] = useState('593988921136')
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState<any[]>([])
  const [showWebview, setShowWebview] = useState(false)
  const [toast, setToast] = useState<string | null>(null)

  const catalogUrl = `http://localhost:8085/catalogo-autos?phone=${phone}&sucursal=Centro`;

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
          message: '¡Hola! 👋 Te damos la bienvenida a *AutoEcuador Motors* 🇪🇨.\n\nSoy *Alex*, tu asesor comercial inteligente para vehículos nuevos y seminuevos 2026.\n\n¿En qué podemos ayudarte hoy? Explora nuestra vitrina virtual interactiva, simula tu crédito bancario o habla con un asesor:',
          buttons: ['🚘 Explorar Vitrina', '🛻 Camionetas 4x4', '⚡ Híbridos (0 Pico y Placa)', '🚙 SUVs Familiares', '🔄 Plan Retoma (Usado)', '👨‍💼 Hablar con Asesor']
        }
      ])
    }
  }, [phone])

  // Escuchar eventos postMessage desde la pantalla emergente (In-App Browser Webview)
  useEffect(() => {
    const handleFrameMessage = (event: MessageEvent) => {
      try {
        if (!event.data || typeof event.data !== 'object') return;
        const data = event.data;

        // 1. Cotización Formal Generada
        if (data.type === 'QUOTE_CONFIRMED') {
          setShowWebview(false);
          const qCode = data.quote_code || 'COT-AUTO-2026';
          const veh = data.vehicle_name || 'Vehículo 0 km';
          const down = data.down_payment ? `$${Number(data.down_payment).toLocaleString()} USD` : '';
          const fee = data.monthly_fee ? `$${Number(data.monthly_fee).toLocaleString()} / mes` : '';

          const quoteMsg = `✅ *¡Cotización Oficial Generada con Éxito!*\n\n📋 *Código:* \`${qCode}\`\n🚘 *Vehículo:* ${veh}\n💰 *Entrada:* ${down}\n📊 *Cuota:* ${fee}\n\n*Alex:* Tu solicitud de crédito ha sido registrada en el sistema de AutoEcuador Motors.\n\n👨‍💼 *Un asesor comercial de nuestra sede Quito Centro se ha conectado a este chat para continuar tu atención por aquí.* ¿Te gustaría coordinar un Test Drive a domicilio para este sábado?`;

          setMessages(prev => {
            const updated = [...prev, {
              id: `quote-conf-${Date.now()}`,
              direction: 'outbound',
              message: quoteMsg,
              timestamp: new Date().toISOString(),
              buttons: ['🏎️ Agendar Test Drive', '📍 Ver Showrooms', '👨‍💼 Hablar con Asesor']
            }];
            localStorage.setItem(`chat_history:${phone}`, JSON.stringify(updated));
            return updated;
          });
          showToast(`¡Cotización ${qCode} procesada! Volviendo a WhatsApp...`);
        }

        // 2. Solicitud de Test Drive
        if (data.type === 'TEST_DRIVE_REQUESTED') {
          setShowWebview(false);
          const leadCode = data.lead_code || 'LEAD-AUTO';
          const veh = data.vehicle_name || 'Vehículo';

          const driveMsg = `🏎️ *¡Test Drive Agendado con Éxito!*\n\n📋 *Código de Solicitud:* \`${leadCode}\`\n🚘 *Vehículo:* ${veh}\n\n*Alex:* Tu prueba de manejo (100% gratuita y sin compromiso) fue registrada.\n\n👨‍💼 Un asesor comercial coordinará contigo por este mismo chat de WhatsApp el día, la hora y si prefieres la prueba a domicilio o en nuestro showroom.`;

          setMessages(prev => {
            const updated = [...prev, {
              id: `testdrive-conf-${Date.now()}`,
              direction: 'outbound',
              message: driveMsg,
              timestamp: new Date().toISOString()
            }];
            localStorage.setItem(`chat_history:${phone}`, JSON.stringify(updated));
            return updated;
          });
          showToast('¡Prueba de manejo agendada! Volviendo a WhatsApp...');
        }

        // 3. Garaje Completo Enviado
        if (data.type === 'GARAGE_BATCH_SUBMITTED') {
          setShowWebview(false);
          const batchMsg = `🏠 *¡Garaje Virtual Enviado para Aprobación Bancaria!*\n\n*Alex:* Recibimos los modelos de tu garaje virtual. Nuestro departamento de crédito está evaluando la mejor tasa con Banco Pichincha y Banco Guayaquil.\n\n👨‍💼 Tu asesor comercial asignado te presentará el comparativo por aquí.`;

          setMessages(prev => {
            const updated = [...prev, {
              id: `garage-conf-${Date.now()}`,
              direction: 'outbound',
              message: batchMsg,
              timestamp: new Date().toISOString()
            }];
            localStorage.setItem(`chat_history:${phone}`, JSON.stringify(updated));
            return updated;
          });
          showToast('Garaje enviado. Volviendo a WhatsApp...');
        }

        // 4. Solicitar Asesor Humano desde la vitrina
        if (data.type === 'CONNECT_ADVISOR') {
          setShowWebview(false);
          const advisorMsg = `👨‍💼 *Conectando con un Asesor Comercial de AutoEcuador Motors...*\n\n*Alex:* He puesto a nuestro equipo de ventas de Quito Centro al tanto de tu solicitud. Un asesor comercial humano se comunicará contigo por este mismo chat en breves instantes.`;

          setMessages(prev => {
            const updated = [...prev, {
              id: `advisor-conf-${Date.now()}`,
              direction: 'outbound',
              message: advisorMsg,
              timestamp: new Date().toISOString()
            }];
            localStorage.setItem(`chat_history:${phone}`, JSON.stringify(updated));
            return updated;
          });
          showToast('Conectando con asesor en WhatsApp...');
        }

        // 5. Cerrar Webview y volver a WhatsApp
        if (data.type === 'CLOSE_WEBVIEW') {
          setShowWebview(false);
          const closeMsg = `✕ *Vitrina virtual cerrada.*\n\n*Alex:* Continuamos por aquí por WhatsApp. ¿Deseas consultar detalles de camionetas 4x4, SUVs familiares, autos híbridos o simular tu crédito?`;

          setMessages(prev => {
            const updated = [...prev, {
              id: `close-conf-${Date.now()}`,
              direction: 'outbound',
              message: closeMsg,
              timestamp: new Date().toISOString(),
              buttons: ['🚘 Explorar Vitrina', '🛻 Camionetas 4x4', '⚡ Híbridos', '👨‍💼 Hablar con Asesor']
            }];
            localStorage.setItem(`chat_history:${phone}`, JSON.stringify(updated));
            return updated;
          });
          showToast('Regresando a WhatsApp...');
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
              if (m.message.includes('Vitrina') || m.message.includes('AutoEcuador') || m.message.includes('Hola')) {
                btns = ['🚘 Explorar Vitrina', '🛻 Camionetas 4x4', '⚡ Híbridos', '🚙 SUVs Familiares', '👨‍💼 Hablar con Asesor']
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
    
    // Si el usuario presiona el botón de la vitrina, abrimos la pantalla emergente
    if (text.includes('Vitrina') || text.includes('Catálogo') || text.includes('Explorar') || text.toLowerCase() === 'catalogo') {
      setShowWebview(true)
    }

    let interactiveId: string | undefined = undefined;
    if (text.includes('Vitrina') || text.includes('Catálogo')) interactiveId = 'flow_catalogo';
    else if (text.includes('Asesor')) interactiveId = 'flow_asesor';

    const payload = {
      phone,
      message: text,
      message_id: msgId,
      metadata: { 
        provider: "meta",
        interactive_id: interactiveId
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
      showToast('Error de conexión con WhatsApp.')
    }
  }

  const handleClearHistory = () => {
    localStorage.removeItem(`chat_history:${phone}`)
    setMessages([
      { 
        id: 'welcome', 
        direction: 'outbound', 
        message: '¡Hola! 👋 Te damos la bienvenida a *AutoEcuador Motors* 🇪🇨.\n\nSoy *Alex*, tu asesor comercial inteligente para vehículos nuevos y seminuevos 2026.\n\n¿En qué podemos ayudarte hoy? Explora nuestra vitrina virtual interactiva, simula tu crédito bancario o habla con un asesor:',
        buttons: ['🚘 Explorar Vitrina', '🛻 Camionetas 4x4', '⚡ Híbridos (0 Pico y Placa)', '🚙 SUVs Familiares', '🔄 Plan Retoma (Usado)', '👨‍💼 Hablar con Asesor']
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
            <span style={{ fontSize: '1.6rem' }}>🚗</span>
            <div>
              <h2 style={{ color: '#00a884', fontSize: '1.1rem', margin: 0, fontWeight: 800 }}>AutoEcuador Motors</h2>
              <p style={{ fontSize: '0.75rem', color: '#8696a0', margin: 0 }}>Simulador Oficial WhatsApp 2026 🇪🇨</p>
            </div>
          </div>
        </div>

        {/* Acceso Rápido al In-App Webview */}
        <div style={{ background: 'linear-gradient(135deg, #b45309, #d97706)', padding: '1rem', borderRadius: '0.75rem', color: 'white', boxShadow: '0 4px 12px rgba(217,119,6,0.25)' }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 800, marginBottom: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span>🚘</span> Pantalla Emergente (In-App Browser)
          </div>
          <p style={{ fontSize: '0.72rem', opacity: 0.95, marginBottom: '0.75rem', lineHeight: 1.35 }}>
            Abre la vitrina virtual interactiva, simula crédito con cuotas reales y guarda en Mi Garaje sin salir de WhatsApp.
          </p>
          <button 
            onClick={() => setShowWebview(prev => !prev)} 
            style={{ width: '100%', padding: '0.65rem', background: 'white', color: '#b45309', border: 'none', borderRadius: '0.5rem', fontWeight: 800, fontSize: '0.8rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.4rem', boxShadow: '0 2px 6px rgba(0,0,0,0.2)' }}
          >
            {showWebview ? '✕ Cerrar Vitrina Emergente' : '✨ Abrir Vitrina Emergente'}
          </button>
        </div>
        
        {/* Selector de Teléfono */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: '#8696a0', marginBottom: '0.4rem', fontWeight: 600 }}>Número del Cliente en WhatsApp</label>
            <select 
              value={phone} 
              onChange={e => setPhone(e.target.value)} 
              style={{ width: '100%', padding: '0.65rem', borderRadius: '0.5rem', border: '1px solid #222e35', background: '#202c33', color: 'white', outline: 'none', fontSize: '0.8rem' }}
            >
              <option value="593988921136">+593 98 892 1136 (Tu Número para Pruebas)</option>
              <option value="593984407038">+593 98 440 7038 (Línea Alterna)</option>
            </select>
          </div>

          {/* Botones de Acción Rápida Comercial */}
          <div style={{ background: '#202c33', padding: '0.85rem', borderRadius: '0.5rem', border: '1px solid #222e35' }}>
            <span style={{ fontSize: '0.75rem', color: '#8696a0', fontWeight: 700, display: 'block', marginBottom: '0.5rem' }}>Flujos Comerciales Automotrices</span>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem' }}>
              <button onClick={() => handleSendMessage('hola')} style={{ padding: '0.5rem', background: '#2a3942', color: '#e9edef', border: '1px solid #3b4a54', borderRadius: '0.35rem', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}>"hola"</button>
              <button onClick={() => handleSendMessage('🚘 Explorar Vitrina')} style={{ padding: '0.5rem', background: '#2a3942', color: '#f59e0b', border: '1px solid #3b4a54', borderRadius: '0.35rem', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 700 }}>"🚘 Vitrina"</button>
              <button onClick={() => handleSendMessage('Qué camionetas 4x4 tienen?')} style={{ padding: '0.5rem', background: '#2a3942', color: '#e9edef', border: '1px solid #3b4a54', borderRadius: '0.35rem', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}>"🛻 4x4"</button>
              <button onClick={() => handleSendMessage('Quiero un auto híbrido sin pico y placa')} style={{ padding: '0.5rem', background: '#2a3942', color: '#10b981', border: '1px solid #3b4a54', borderRadius: '0.35rem', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}>"⚡ Híbridos"</button>
              <button onClick={() => handleSendMessage('Tengo un auto usado como parte de pago')} style={{ padding: '0.5rem', background: '#2a3942', color: '#e9edef', border: '1px solid #3b4a54', borderRadius: '0.35rem', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}>"🔄 Plan Retoma"</button>
              <button onClick={() => handleSendMessage('Tengo 5000 de entrada qué me alcanza?')} style={{ padding: '0.5rem', background: '#2a3942', color: '#e9edef', border: '1px solid #3b4a54', borderRadius: '0.35rem', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}>"💰 $5.000"</button>
              <button onClick={() => handleSendMessage('Cómo agendo un test drive?')} style={{ padding: '0.5rem', background: '#2a3942', color: '#e9edef', border: '1px solid #3b4a54', borderRadius: '0.35rem', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}>"🏎️ Test Drive"</button>
              <button onClick={() => handleSendMessage('👨‍💼 Hablar con Asesor')} style={{ padding: '0.5rem', background: '#2a3942', color: '#00a884', border: '1px solid #3b4a54', borderRadius: '0.35rem', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 700 }}>"👨‍💼 Asesor"</button>
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

      {/* Frame del Teléfono Móvil (Mockup Realista de WhatsApp) */}
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
          
          {/* Barra Superior del Móvil */}
          <div style={{ height: '36px', background: '#202c33', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 1.25rem', fontSize: '0.72rem', color: '#e9edef', fontWeight: 600, zIndex: 110 }}>
            <span>9:41</span>
            <div style={{ width: '90px', height: '18px', background: '#0b141a', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#1e293b', marginRight: '4px' }}></div>
              <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#f59e0b' }}></div>
            </div>
            <div style={{ display: 'flex', gap: '0.3rem', alignItems: 'center' }}>
              <span>5G</span>
              <span>100%</span>
            </div>
          </div>

          {/* WhatsApp Header */}
          <div style={{ padding: '0.65rem 1rem', background: '#202c33', display: 'flex', gap: '0.75rem', alignItems: 'center', borderBottom: '1px solid #2a3942' }}>
            <div style={{ width: '36px', height: '36px', borderRadius: '50%', background: 'linear-gradient(135deg, #d97706, #b45309)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.2rem', fontWeight: 700, color: 'white', boxShadow: '0 2px 6px rgba(0,0,0,0.2)' }}>
              🚗
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '0.9rem', fontWeight: 800, color: '#e9edef', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                AutoEcuador Motors
                <span style={{ fontSize: '0.7rem', color: '#00a884' }}>✓</span>
              </div>
              <span style={{ fontSize: '0.7rem', color: '#00a884' }}>Asesor Alex • Concesionario Oficial • En línea</span>
            </div>
          </div>

          {/* Chat Messages Thread */}
          <div style={{ flexGrow: 1, padding: '1rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.6rem', backgroundImage: 'radial-gradient(circle, #182229 10%, transparent 11%)', backgroundSize: '14px 14px' }}>
            {messages.map((m, idx) => {
              const isUser = m.direction === 'inbound'
              return (
                <div key={m.id || idx} style={{ alignSelf: isUser ? 'flex-end' : 'flex-start', maxWidth: '85%', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <div style={{
                    padding: '0.65rem 0.9rem',
                    borderRadius: isUser ? '14px 0 14px 14px' : '0 14px 14px 14px',
                    background: isUser ? '#005c4b' : '#202c33',
                    color: '#e9edef',
                    fontSize: '0.82rem',
                    lineHeight: 1.45,
                    boxShadow: '0 1px 2px rgba(0,0,0,0.2)',
                    whiteSpace: 'pre-line'
                  }}>
                    {m.message}
                  </div>

                  {/* WhatsApp Interactive Buttons */}
                  {!isUser && m.buttons && m.buttons.length > 0 && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', marginTop: '0.2rem' }}>
                      {m.buttons.map((btnText: string, bIdx: number) => (
                        <button
                          key={bIdx}
                          onClick={() => handleSendMessage(btnText)}
                          style={{
                            width: '100%',
                            padding: '0.6rem',
                            background: '#202c33',
                            border: '1px solid #2a3942',
                            color: btnText.includes('Vitrina') ? '#f59e0b' : '#00a884',
                            borderRadius: '10px',
                            fontSize: '0.78rem',
                            fontWeight: 700,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '0.35rem',
                            boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
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
              placeholder="Pregunta sobre 4x4, cuotas, autos o escribe 'vitrina'..." 
              style={{ flexGrow: 1, padding: '0.65rem 0.9rem', borderRadius: '18px', border: '1px solid #2a3942', background: '#2a3942', color: 'white', outline: 'none', fontSize: '0.82rem' }} 
            />
            <button 
              type="submit" 
              style={{ width: '36px', height: '36px', borderRadius: '50%', background: '#00a884', border: 'none', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.9rem', cursor: 'pointer' }}
            >
              ➤
            </button>
          </form>

          {/* 🪟 PANTALLA EMERGENTE IN-APP BROWSER (Navegación Interna sin salir de WhatsApp) */}
          <div style={{
            position: 'absolute',
            inset: 0,
            background: '#090d16',
            zIndex: 100,
            transform: showWebview ? 'translateY(0)' : 'translateY(100%)',
            transition: 'transform 0.35s cubic-bezier(0.16, 1, 0.3, 1)',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 -10px 40px rgba(0,0,0,0.7)'
          }}>
            {/* Top Bar del Visor Emergente de WhatsApp */}
            <div style={{ 
              height: '46px', 
              background: '#0f172a', 
              color: '#e9edef', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between', 
              padding: '0 1rem', 
              borderBottom: '1px solid #1e293b',
              fontSize: '0.8rem',
              boxShadow: '0 2px 8px rgba(0,0,0,0.3)'
            }}>
              <button 
                onClick={() => setShowWebview(false)} 
                style={{ background: 'transparent', border: 'none', color: '#f43f5e', fontSize: '1.2rem', cursor: 'pointer', padding: '0.25rem', fontWeight: 900 }}
                title="Cerrar Vitrina"
              >
                ✕
              </button>
              
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <span style={{ fontWeight: 800, fontSize: '0.78rem', color: '#f8fafc' }}>WhatsApp In-App Browser</span>
                <span style={{ fontSize: '0.65rem', color: '#10b981', display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                  🔒 autoecuador.com/catalogo
                </span>
              </div>

              <button 
                onClick={() => setShowWebview(false)} 
                style={{ background: '#1e293b', border: '1px solid #334155', color: '#38bdf8', fontSize: '0.7rem', borderRadius: '6px', padding: '0.25rem 0.6rem', cursor: 'pointer', fontWeight: 700 }}
              >
                Volver
              </button>
            </div>

            {/* Iframe de la Vitrina Oficial */}
            <iframe 
              src={catalogUrl}
              style={{ width: '100%', flexGrow: 1, border: 'none', background: '#020617' }}
              title="Vitrina Virtual AutoEcuador Motors"
              allow="camera; microphone; geolocation"
            />
          </div>

        </div>
      </div>
    </div>
  )
}
