import { useState, useEffect, useRef } from 'react'

const GATEWAY_URL = 'http://localhost:8095';

interface ChatMessage {
  id: string;
  direction: 'inbound' | 'outbound';
  message: string;
  buttons?: string[];
  timestamp: string;
}

const INITIAL_WELCOME: ChatMessage = {
  id: 'welcome-001',
  direction: 'outbound',
  message: '¡Hola! 👋 Te damos la bienvenida a *AutoEcuador Motors* 🇪🇨, concesionario multimarca oficial.\n\nSoy *Alex*, tu asesor comercial inteligente para vehículos nuevos y seminuevos 2026.\n\n¿En qué podemos ayudarte hoy? Toca una de las opciones abajo o escríbeme directamente tu consulta:',
  buttons: ['🚘 Explorar Vitrina', '🛻 Camionetas 4x4', '⚡ Híbridos (0 Pico y Placa)', '🚙 SUVs Familiares', '💰 Asesoría Crédito', '👨‍💼 Hablar con Asesor'],
  timestamp: new Date().toISOString()
};

export default function App() {
  const [phone, setPhone] = useState('593988921136')
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [showWebview, setShowWebview] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const [activeStep, setActiveStep] = useState<number>(1)
  
  const chatEndRef = useRef<HTMLDivElement>(null)
  const knownOutboundRef = useRef<Set<string>>(new Set())

  const catalogUrl = `${GATEWAY_URL}/catalogo-autos?phone=${phone}&sucursal=Centro`;

  // Inicializar o cargar historial
  useEffect(() => {
    const stored = localStorage.getItem(`chat_history:${phone}`)
    if (stored) {
      try {
        const parsed = JSON.parse(stored)
        setMessages(parsed)
        parsed.forEach((m: ChatMessage) => {
          if (m.direction === 'outbound') {
            knownOutboundRef.current.add(m.message.trim())
          }
        })
      } catch {
        setMessages([INITIAL_WELCOME])
        knownOutboundRef.current.add(INITIAL_WELCOME.message.trim())
      }
    } else {
      setMessages([INITIAL_WELCOME])
      knownOutboundRef.current.add(INITIAL_WELCOME.message.trim())
    }
  }, [phone])

  // Scroll automático hacia el mensaje más reciente
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(null), 3500)
  }

  // Escuchar eventos postMessage desde la vitrina emergente (In-App Browser Webview)
  useEffect(() => {
    const handleFrameMessage = (event: MessageEvent) => {
      try {
        if (!event.data || typeof event.data !== 'object') return;
        const data = event.data;

        // 1. Cotización Formal Generada desde la vitrina
        if (data.type === 'QUOTE_CONFIRMED') {
          setShowWebview(false);
          const qCode = data.quote_code || 'COT-AUTO-2026';
          const veh = data.vehicle_name || 'Vehículo 0 km';
          const down = data.down_payment ? `$${Number(data.down_payment).toLocaleString()} USD` : '';
          const fee = data.monthly_fee ? `$${Number(data.monthly_fee).toLocaleString()} / mes` : '';

          const quoteMsg = `✅ *¡Cotización Oficial Generada con Éxito!*\n\n📋 *Código:* \`${qCode}\`\n🚘 *Vehículo:* ${veh}\n💰 *Entrada:* ${down}\n📊 *Cuota:* ${fee}\n\n*Alex:* Tu solicitud de crédito bancario fue registrada en el sistema de AutoEcuador Motors.\n\n👨‍💼 *Un asesor comercial de Quito Centro se ha conectado a este chat para continuar tu atención por aquí.* ¿Te gustaría coordinar un Test Drive a domicilio para este sábado?`;

          appendMessage({
            id: `quote-conf-${Date.now()}`,
            direction: 'outbound',
            message: quoteMsg,
            buttons: ['🏎️ Agendar Test Drive', '📍 Ver Showrooms', '👨‍💼 Hablar con Asesor'],
            timestamp: new Date().toISOString()
          });
          setActiveStep(5);
          showToast(`¡Cotización ${qCode} procesada! Volviendo a WhatsApp...`);
        }

        // 2. Solicitud de Test Drive desde la vitrina
        if (data.type === 'TEST_DRIVE_REQUESTED') {
          setShowWebview(false);
          const leadCode = data.lead_code || 'LEAD-AUTO';
          const veh = data.vehicle_name || 'Vehículo';

          const driveMsg = `🏎️ *¡Test Drive Agendado con Éxito!*\n\n📋 *Código de Solicitud:* \`${leadCode}\`\n🚘 *Vehículo:* ${veh}\n\n*Alex:* Tu prueba de manejo (100% gratuita y sin compromiso) fue registrada.\n\n👨‍💼 Un asesor comercial coordinará contigo por este mismo chat de WhatsApp el día, la hora y si prefieres la prueba a domicilio o en nuestro showroom.`;

          appendMessage({
            id: `testdrive-conf-${Date.now()}`,
            direction: 'outbound',
            message: driveMsg,
            timestamp: new Date().toISOString()
          });
          setActiveStep(5);
          showToast('¡Prueba de manejo agendada! Volviendo a WhatsApp...');
        }

        // 3. Garaje Completo Enviado
        if (data.type === 'GARAGE_BATCH_SUBMITTED') {
          setShowWebview(false);
          const batchMsg = `🏠 *¡Garaje Virtual Enviado para Aprobación Bancaria!*\n\n*Alex:* Recibimos los modelos de tu garaje virtual. Nuestro departamento de crédito está evaluando la mejor tasa con Banco Pichincha y Banco Guayaquil.\n\n👨‍💼 Tu asesor comercial asignado te presentará el comparativo por aquí.`;

          appendMessage({
            id: `garage-conf-${Date.now()}`,
            direction: 'outbound',
            message: batchMsg,
            timestamp: new Date().toISOString()
          });
          showToast('Garaje enviado. Volviendo a WhatsApp...');
        }

        // 4. Conectar con Asesor Humano desde la vitrina
        if (data.type === 'CONNECT_ADVISOR') {
          setShowWebview(false);
          const advisorMsg = `👨‍💼 *Conectando con un Asesor Comercial de AutoEcuador Motors...*\n\n*Alex:* He puesto a nuestro equipo de ventas de Quito Centro al tanto de tu solicitud. Un asesor comercial humano se comunicará contigo por este mismo chat en breves instantes.`;

          appendMessage({
            id: `advisor-conf-${Date.now()}`,
            direction: 'outbound',
            message: advisorMsg,
            timestamp: new Date().toISOString()
          });
          setActiveStep(6);
          showToast('Conectando con asesor en WhatsApp...');
        }

        // 5. Cerrar Webview y volver a WhatsApp
        if (data.type === 'CLOSE_WEBVIEW') {
          setShowWebview(false);
          const closeMsg = `✕ *Vitrina virtual cerrada.*\n\n*Alex:* Continuamos por aquí por WhatsApp. ¿Deseas consultar detalles de camionetas 4x4, SUVs familiares, autos híbridos o simular tu crédito?`;

          appendMessage({
            id: `close-conf-${Date.now()}`,
            direction: 'outbound',
            message: closeMsg,
            buttons: ['🚘 Explorar Vitrina', '🛻 Camionetas 4x4', '⚡ Híbridos', '👨‍💼 Hablar con Asesor'],
            timestamp: new Date().toISOString()
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

  const appendMessage = (newMsg: ChatMessage) => {
    setMessages(prev => {
      const updated = [...prev, newMsg];
      localStorage.setItem(`chat_history:${phone}`, JSON.stringify(updated));
      return updated;
    });
    if (newMsg.direction === 'outbound') {
      knownOutboundRef.current.add(newMsg.message.trim());
    }
  };

  // Polling periódico para recibir respuestas del backend en orden estricto
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${GATEWAY_URL}/outbound?phone=${phone}`);
        const result = await response.json();
        if (result.success && Array.isArray(result.data)) {
          // Filtrar los que no conocemos todavía (ordenados de más viejo a más nuevo)
          const newOutbounds = [...result.data].reverse().filter((item: any) => {
            const trimmed = (item.message || '').trim();
            return trimmed && !knownOutboundRef.current.has(trimmed);
          });

          if (newOutbounds.length > 0) {
            setIsTyping(false);
            newOutbounds.forEach((item: any, idx: number) => {
              let btns: string[] = [];
              const msg = item.message || '';
              if (msg.includes('Vitrina') || msg.includes('AutoEcuador') || msg.includes('Hola')) {
                btns = ['🚘 Explorar Vitrina', '🛻 Camionetas 4x4', '⚡ Híbridos', '🚙 SUVs Familiares', '👨‍💼 Hablar con Asesor'];
              } else if (msg.includes('Camionetas 4x4') || msg.includes('D-Max')) {
                btns = ['🚘 Explorar Vitrina', '🏎️ Agendar Test Drive', '💰 Simular Crédito'];
              } else if (msg.includes('Híbrido') || msg.includes('Yaris')) {
                btns = ['🚘 Explorar Vitrina', '🏎️ Test Drive Híbrido'];
              } else if (msg.includes('entrada') || msg.includes('crédito') || msg.includes('cuota')) {
                btns = ['🚘 Explorar Vitrina', '🏎️ Agendar Test Drive', '👨‍💼 Hablar con Asesor'];
              }

              appendMessage({
                id: `out-poll-${Date.now()}-${idx}`,
                direction: 'outbound',
                message: msg,
                buttons: btns,
                timestamp: item.timestamp || new Date().toISOString()
              });
            });
          }
        }
      } catch {
        // En caso de corte momentáneo
      }
    }, 1200);

    return () => clearInterval(interval);
  }, [phone]);

  const handleSendMessage = async (textToSend?: string, stepNumber?: number) => {
    const text = (textToSend || message).trim();
    if (!text) return;
    setMessage('');

    if (stepNumber) {
      setActiveStep(stepNumber);
    }

    // Si el usuario presiona explícitamente abrir vitrina
    if (text.includes('Explorar Vitrina') || text.includes('Abrir Vitrina') || text.toLowerCase() === 'vitrina') {
      setShowWebview(true);
    }

    const msgId = `sim-user-${Date.now()}`;
    const userMsgObj: ChatMessage = {
      id: msgId,
      direction: 'inbound',
      message: text,
      timestamp: new Date().toISOString()
    };

    // 1. Agregar de inmediato el mensaje del usuario al chat
    appendMessage(userMsgObj);
    setIsTyping(true);

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
    };

    try {
      const response = await fetch(`${GATEWAY_URL}/webhooks/whatsapp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      await response.json();

      // Consultar de inmediato las respuestas generadas
      setTimeout(async () => {
        try {
          const outRes = await fetch(`${GATEWAY_URL}/outbound?phone=${phone}`);
          const outJson = await outRes.json();
          if (outJson.success && Array.isArray(outJson.data)) {
            const newOutbounds = [...outJson.data].reverse().filter((item: any) => {
              const trimmed = (item.message || '').trim();
              return trimmed && !knownOutboundRef.current.has(trimmed);
            });
            if (newOutbounds.length > 0) {
              setIsTyping(false);
              newOutbounds.forEach((item: any, idx: number) => {
                let btns: string[] = [];
                const msg = item.message || '';
                if (msg.includes('Vitrina') || msg.includes('AutoEcuador') || msg.includes('Hola')) {
                  btns = ['🚘 Explorar Vitrina', '🛻 Camionetas 4x4', '⚡ Híbridos', '🚙 SUVs Familiares', '👨‍💼 Hablar con Asesor'];
                } else if (msg.includes('Camionetas 4x4') || msg.includes('D-Max')) {
                  btns = ['🚘 Explorar Vitrina', '🏎️ Agendar Test Drive', '💰 Simular Crédito'];
                } else if (msg.includes('Híbrido') || msg.includes('Yaris')) {
                  btns = ['🚘 Explorar Vitrina', '🏎️ Test Drive Híbrido'];
                } else if (msg.includes('entrada') || msg.includes('crédito') || msg.includes('cuota')) {
                  btns = ['🚘 Explorar Vitrina', '🏎️ Agendar Test Drive', '👨‍💼 Hablar con Asesor'];
                }
                appendMessage({
                  id: `out-immediate-${Date.now()}-${idx}`,
                  direction: 'outbound',
                  message: msg,
                  buttons: btns,
                  timestamp: item.timestamp || new Date().toISOString()
                });
              });
            }
          }
        } catch {
          // Fallback a polling
        }
      }, 700);

    } catch {
      setIsTyping(false);
      showToast('Error de conexión con el gateway local.');
    }
  };

  const handleClearHistory = async () => {
    try {
      await fetch(`${GATEWAY_URL}/outbound`, { method: 'DELETE' });
    } catch {
      // Ignorar si falla endpoint
    }
    localStorage.removeItem(`chat_history:${phone}`);
    knownOutboundRef.current.clear();
    knownOutboundRef.current.add(INITIAL_WELCOME.message.trim());
    setMessages([INITIAL_WELCOME]);
    setShowWebview(false);
    setIsTyping(false);
    setActiveStep(1);
    showToast('Historial reiniciado.');
  };

  return (
    <div style={{ display: 'flex', width: '100%', height: '100vh', background: '#070b0e', color: '#e9edef', fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', overflow: 'hidden' }}>
      
      {/* Toast Notification */}
      {toast && (
        <div style={{ position: 'fixed', top: '1.25rem', right: '1.5rem', background: '#00a884', color: 'white', padding: '0.75rem 1.25rem', borderRadius: '0.6rem', zIndex: 9999, fontWeight: 700, fontSize: '0.85rem', boxShadow: '0 8px 24px rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span>✨</span> {toast}
        </div>
      )}

      {/* 🧭 PANEL LATERAL: GUÍA COMPLETA DEL FLUJO AUTOMOTRIZ */}
      <div style={{ width: '450px', minWidth: '380px', maxWidth: '480px', background: '#0f171c', borderRight: '1px solid #1f2c34', display: 'flex', flexDirection: 'column', height: '100vh' }}>
        
        {/* Cabecera del Panel */}
        <div style={{ padding: '1.25rem', borderBottom: '1px solid #1f2c34', background: '#111b21' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ width: '42px', height: '42px', borderRadius: '10px', background: 'linear-gradient(135deg, #f59e0b, #d97706)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.4rem', boxShadow: '0 4px 12px rgba(245,158,11,0.3)' }}>
              🚗
            </div>
            <div>
              <h2 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.01em' }}>
                AutoEcuador Motors 🇪🇨
              </h2>
              <p style={{ margin: 0, fontSize: '0.74rem', color: '#00a884', fontWeight: 600 }}>
                Guía Interactiva de Simulación de Flujos
              </p>
            </div>
          </div>
        </div>

        {/* Lista de Pasos del Flujo */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          
          <div style={{ padding: '0.65rem 0.85rem', background: '#182229', borderRadius: '0.5rem', border: '1px solid #222e35', fontSize: '0.75rem', color: '#8696a0', lineHeight: 1.4 }}>
            💡 <strong style={{ color: '#e9edef' }}>¿Cómo funciona?</strong> Puedes hacer click en cada paso de esta guía para probarlo al instante, o escribir libremente en el chat del teléfono.
          </div>

          {/* PASO 1 */}
          <div style={{ background: activeStep === 1 ? '#1a2730' : '#111b21', border: `1px solid ${activeStep === 1 ? '#00a884' : '#1f2c34'}`, borderRadius: '0.75rem', padding: '0.85rem', transition: 'all 0.2s' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#00a884', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Paso 1 • Bienvenida & Menú
              </span>
              <span style={{ fontSize: '0.7rem', background: '#1f2c34', padding: '0.15rem 0.4rem', borderRadius: '4px', color: '#94a3b8' }}>Inicio</span>
            </div>
            <p style={{ fontSize: '0.75rem', color: '#cbd5e1', margin: '0 0 0.6rem 0', lineHeight: 1.35 }}>
              Saluda al bot. Alex se presenta como asesor inteligente multimarca y despliega las opciones comerciales.
            </p>
            <button 
              onClick={() => handleSendMessage('Hola buenas tardes', 1)}
              style={{ width: '100%', padding: '0.55rem', background: '#00a884', color: 'white', border: 'none', borderRadius: '0.45rem', fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.35rem' }}
            >
              <span>👋</span> Probar: "Hola buenas tardes"
            </button>
          </div>

          {/* PASO 2 */}
          <div style={{ background: activeStep === 2 ? '#1a2730' : '#111b21', border: `1px solid ${activeStep === 2 ? '#00a884' : '#1f2c34'}`, borderRadius: '0.75rem', padding: '0.85rem', transition: 'all 0.2s' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#f59e0b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Paso 2 • Búsqueda por Categoría
              </span>
              <span style={{ fontSize: '0.7rem', background: '#1f2c34', padding: '0.15rem 0.4rem', borderRadius: '4px', color: '#94a3b8' }}>Catálogo</span>
            </div>
            <p style={{ fontSize: '0.75rem', color: '#cbd5e1', margin: '0 0 0.6rem 0', lineHeight: 1.35 }}>
              Consulta modelos específicos según el uso en Ecuador: trabajo 4x4, SUVs familiares o híbridos sin pico y placa.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
              <button 
                onClick={() => handleSendMessage('Qué camionetas 4x4 tienen?', 2)}
                style={{ width: '100%', padding: '0.5rem', background: '#202c33', color: '#f59e0b', border: '1px solid #374151', borderRadius: '0.45rem', fontSize: '0.74rem', fontWeight: 700, cursor: 'pointer', textAlign: 'left', paddingLeft: '0.75rem' }}
              >
                🛻 "Qué camionetas 4x4 tienen?" (D-Max, Hilux, Poer)
              </button>
              <button 
                onClick={() => handleSendMessage('Busco un SUV familiar espacioso', 2)}
                style={{ width: '100%', padding: '0.5rem', background: '#202c33', color: '#38bdf8', border: '1px solid #374151', borderRadius: '0.45rem', fontSize: '0.74rem', fontWeight: 700, cursor: 'pointer', textAlign: 'left', paddingLeft: '0.75rem' }}
              >
                🚙 "Busco un SUV familiar espacioso" (Sportage, Tucson, Tracker)
              </button>
              <button 
                onClick={() => handleSendMessage('Quiero un auto híbrido sin pico y placa', 2)}
                style={{ width: '100%', padding: '0.5rem', background: '#202c33', color: '#10b981', border: '1px solid #374151', borderRadius: '0.45rem', fontSize: '0.74rem', fontWeight: 700, cursor: 'pointer', textAlign: 'left', paddingLeft: '0.75rem' }}
              >
                ⚡ "Quiero un híbrido sin pico y placa" (Yaris Cross)
              </button>
            </div>
          </div>

          {/* PASO 3 */}
          <div style={{ background: activeStep === 3 ? '#1a2730' : '#111b21', border: `1px solid ${activeStep === 3 ? '#00a884' : '#1f2c34'}`, borderRadius: '0.75rem', padding: '0.85rem', transition: 'all 0.2s' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#38bdf8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Paso 3 • Presupuesto & Crédito
              </span>
              <span style={{ fontSize: '0.7rem', background: '#1f2c34', padding: '0.15rem 0.4rem', borderRadius: '4px', color: '#94a3b8' }}>Financiamiento</span>
            </div>
            <p style={{ fontSize: '0.75rem', color: '#cbd5e1', margin: '0 0 0.6rem 0', lineHeight: 1.35 }}>
              El cliente indica su dinero disponible de entrada ($5.000). Alex calcula qué autos alcanzan con el 20% y estima cuotas mensuales con bancos.
            </p>
            <button 
              onClick={() => handleSendMessage('Tengo 5000 de entrada qué me alcanza?', 3)}
              style={{ width: '100%', padding: '0.55rem', background: '#0284c7', color: 'white', border: 'none', borderRadius: '0.45rem', fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.35rem' }}
            >
              <span>💰</span> Probar: "Tengo $5.000 de entrada"
            </button>
          </div>

          {/* PASO 4 */}
          <div style={{ background: activeStep === 4 ? '#1a2730' : '#111b21', border: `1px solid ${activeStep === 4 ? '#00a884' : '#1f2c34'}`, borderRadius: '0.75rem', padding: '0.85rem', transition: 'all 0.2s' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#ec4899', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Paso 4 • Pantalla Emergente Webview
              </span>
              <span style={{ fontSize: '0.7rem', background: '#1f2c34', padding: '0.15rem 0.4rem', borderRadius: '4px', color: '#94a3b8' }}>In-App Browser</span>
            </div>
            <p style={{ fontSize: '0.75rem', color: '#cbd5e1', margin: '0 0 0.6rem 0', lineHeight: 1.35 }}>
              Abre la vitrina virtual interactiva dentro de WhatsApp. Permite mover sliders de meses/entrada, ver fotos reales y cotizar en tiempo real.
            </p>
            <button 
              onClick={() => { setShowWebview(true); setActiveStep(4); }}
              style={{ width: '100%', padding: '0.55rem', background: 'linear-gradient(135deg, #d97706, #b45309)', color: 'white', border: 'none', borderRadius: '0.45rem', fontSize: '0.75rem', fontWeight: 800, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.35rem', boxShadow: '0 4px 10px rgba(217,119,6,0.25)' }}
            >
              <span>✨</span> Abrir Vitrina Virtual Emergente
            </button>
          </div>

          {/* PASO 5 */}
          <div style={{ background: activeStep === 5 ? '#1a2730' : '#111b21', border: `1px solid ${activeStep === 5 ? '#00a884' : '#1f2c34'}`, borderRadius: '0.75rem', padding: '0.85rem', transition: 'all 0.2s' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#a855f7', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Paso 5 • Test Drive & Retorno
              </span>
              <span style={{ fontSize: '0.7rem', background: '#1f2c34', padding: '0.15rem 0.4rem', borderRadius: '4px', color: '#94a3b8' }}>Cierre y Lead</span>
            </div>
            <p style={{ fontSize: '0.75rem', color: '#cbd5e1', margin: '0 0 0.6rem 0', lineHeight: 1.35 }}>
              Al cotizar o solicitar test drive en la vitrina (o en el chat), se genera un código oficial registrado en PostgreSQL y se cierra la pantalla emergente.
            </p>
            <button 
              onClick={() => handleSendMessage('Cómo agendo un test drive a domicilio?', 5)}
              style={{ width: '100%', padding: '0.55rem', background: '#7c3aed', color: 'white', border: 'none', borderRadius: '0.45rem', fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.35rem' }}
            >
              <span>🏎️</span> Probar: "Cómo agendo un test drive?"
            </button>
          </div>

          {/* PASO 6 */}
          <div style={{ background: activeStep === 6 ? '#1a2730' : '#111b21', border: `1px solid ${activeStep === 6 ? '#00a884' : '#1f2c34'}`, borderRadius: '0.75rem', padding: '0.85rem', transition: 'all 0.2s' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#10b981', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Paso 6 • Traspaso a Asesor Humano
              </span>
              <span style={{ fontSize: '0.7rem', background: '#1f2c34', padding: '0.15rem 0.4rem', borderRadius: '4px', color: '#94a3b8' }}>Handoff</span>
            </div>
            <p style={{ fontSize: '0.75rem', color: '#cbd5e1', margin: '0 0 0.6rem 0', lineHeight: 1.35 }}>
              El bot Alex transfiere la conversación en vivo a un ejecutivo de ventas de Quito Centro en Chatwoot.
            </p>
            <button 
              onClick={() => handleSendMessage('Quiero hablar con un asesor comercial humano', 6)}
              style={{ width: '100%', padding: '0.55rem', background: '#059669', color: 'white', border: 'none', borderRadius: '0.45rem', fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.35rem' }}
            >
              <span>👨‍💼</span> Probar: "Hablar con Asesor"
            </button>
          </div>

        </div>

        {/* Footer del Panel */}
        <div style={{ padding: '0.85rem 1rem', borderTop: '1px solid #1f2c34', background: '#111b21', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <label style={{ fontSize: '0.72rem', color: '#8696a0', fontWeight: 600 }}>Número WhatsApp:</label>
            <select
              value={phone}
              onChange={e => setPhone(e.target.value)}
              style={{ background: '#182229', color: '#00a884', border: '1px solid #222e35', borderRadius: '4px', fontSize: '0.72rem', padding: '0.2rem 0.4rem', fontWeight: 700, outline: 'none' }}
            >
              <option value="593988921136">+593 98 892 1136</option>
              <option value="593984407038">+593 98 440 7038</option>
            </select>
          </div>
          <button 
            onClick={handleClearHistory}
            style={{ width: '100%', padding: '0.45rem 0.75rem', background: 'transparent', border: '1px solid #f43f5e', color: '#f43f5e', borderRadius: '0.4rem', fontSize: '0.72rem', fontWeight: 700, cursor: 'pointer' }}
          >
            Limpiar Chat & Historial
          </button>
        </div>

      </div>

      {/* 📱 SIMULADOR DEL TELÉFONO MÓVIL (WHATSAPP REALISTA) */}
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem', background: '#070b0e' }}>
        
        <div style={{ 
          width: '395px', 
          height: '790px', 
          maxHeight: '94vh', 
          background: '#0b141a', 
          borderRadius: '44px', 
          border: '10px solid #202c33', 
          boxShadow: '0 25px 60px -15px rgba(0,0,0,0.9), 0 0 0 2px #374151', 
          display: 'flex', 
          flexDirection: 'column', 
          position: 'relative', 
          overflow: 'hidden' 
        }}>
          
          {/* Barra Superior del Sistema Operativo */}
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

          {/* Cabecera Oficial de WhatsApp Business */}
          <div style={{ padding: '0.65rem 1rem', background: '#202c33', display: 'flex', gap: '0.75rem', alignItems: 'center', borderBottom: '1px solid #2a3942', zIndex: 10 }}>
            <div style={{ width: '38px', height: '38px', borderRadius: '50%', background: 'linear-gradient(135deg, #d97706, #b45309)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.25rem', fontWeight: 700, color: 'white', boxShadow: '0 2px 6px rgba(0,0,0,0.2)' }}>
              🚗
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: '0.88rem', fontWeight: 800, color: '#e9edef', display: 'flex', alignItems: 'center', gap: '0.35rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                AutoEcuador Motors
                <span style={{ fontSize: '0.75rem', color: '#00a884' }}>✓</span>
              </div>
              <div style={{ fontSize: '0.68rem', color: '#00a884', fontWeight: 600 }}>
                {isTyping ? 'Alex está escribiendo... ✍️' : 'Asesor Alex • En línea'}
              </div>
            </div>
          </div>

          {/* Hilo de Mensajes de WhatsApp */}
          <div style={{ flexGrow: 1, padding: '1rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.65rem', backgroundImage: 'radial-gradient(circle, #151d22 10%, transparent 11%)', backgroundSize: '14px 14px' }}>
            {messages.map((m, idx) => {
              const isUser = m.direction === 'inbound';
              return (
                <div key={m.id || idx} style={{ alignSelf: isUser ? 'flex-end' : 'flex-start', maxWidth: '85%', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  
                  {/* Globo de Texto */}
                  <div style={{
                    padding: '0.65rem 0.9rem',
                    borderRadius: isUser ? '14px 0 14px 14px' : '0 14px 14px 14px',
                    background: isUser ? '#005c4b' : '#202c33',
                    color: '#e9edef',
                    fontSize: '0.81rem',
                    lineHeight: 1.45,
                    boxShadow: '0 1px 2px rgba(0,0,0,0.25)',
                    whiteSpace: 'pre-line',
                    wordBreak: 'break-word'
                  }}>
                    {m.message}
                  </div>

                  {/* Acceso directo a vitrina si el mensaje contiene enlace */}
                  {(m.message.includes('catalogo-autos') || m.message.includes('Explorar Vitrina') || m.message.includes('Ver Camionetas')) && (
                    <button 
                      onClick={() => setShowWebview(true)}
                      style={{
                        padding: '0.55rem',
                        background: 'linear-gradient(135deg, #b45309, #d97706)',
                        color: 'white',
                        border: 'none',
                        borderRadius: '8px',
                        fontSize: '0.75rem',
                        fontWeight: 800,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '0.35rem',
                        boxShadow: '0 2px 6px rgba(0,0,0,0.3)',
                        marginTop: '0.15rem'
                      }}
                    >
                      <span>🚘</span> Abrir Vitrina en Pantalla Emergente
                    </button>
                  )}

                  {/* Botones Interactivos Nativos de WhatsApp */}
                  {!isUser && m.buttons && m.buttons.length > 0 && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', marginTop: '0.25rem' }}>
                      {m.buttons.map((btnText: string, bIdx: number) => (
                        <button
                          key={bIdx}
                          onClick={() => handleSendMessage(btnText)}
                          style={{
                            width: '100%',
                            padding: '0.55rem',
                            background: '#202c33',
                            border: '1px solid #2a3942',
                            color: btnText.includes('Vitrina') ? '#f59e0b' : '#00a884',
                            borderRadius: '8px',
                            fontSize: '0.76rem',
                            fontWeight: 700,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '0.35rem',
                            boxShadow: '0 1px 3px rgba(0,0,0,0.2)'
                          }}
                        >
                          {btnText}
                        </button>
                      ))}
                    </div>
                  )}

                </div>
              );
            })}

            {/* Typing Indicator */}
            {isTyping && (
              <div style={{ alignSelf: 'flex-start', background: '#202c33', padding: '0.5rem 0.85rem', borderRadius: '0 12px 12px 12px', fontSize: '0.75rem', color: '#00a884', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <span style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', background: '#00a884' }}></span>
                Alex está preparando la mejor oferta...
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* Barra Inferior para Escribir Mensajes */}
          <form 
            onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }} 
            style={{ padding: '0.6rem 0.75rem', background: '#202c33', display: 'flex', gap: '0.5rem', alignItems: 'center', borderTop: '1px solid #2a3942', zIndex: 10 }}
          >
            <input 
              type="text" 
              value={message} 
              onChange={e => setMessage(e.target.value)} 
              placeholder="Pregunta sobre 4x4, cuotas, o escribe..." 
              style={{ flexGrow: 1, padding: '0.65rem 0.9rem', borderRadius: '18px', border: '1px solid #2a3942', background: '#2a3942', color: 'white', outline: 'none', fontSize: '0.8rem' }} 
            />
            <button 
              type="submit" 
              style={{ width: '36px', height: '36px', borderRadius: '50%', background: '#00a884', border: 'none', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.9rem', cursor: 'pointer', flexShrink: 0 }}
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
            boxShadow: '0 -10px 40px rgba(0,0,0,0.8)'
          }}>
            {/* Barra Superior del In-App Browser de WhatsApp */}
            <div style={{ 
              height: '46px', 
              background: '#0f172a', 
              color: '#e9edef', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between', 
              padding: '0 1rem', 
              borderBottom: '1px solid #1e293b',
              fontSize: '0.8rem'
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
