import { useState, useEffect, useRef } from 'react'

const GATEWAY_URL = 'http://localhost:8095';

interface ChatMessage {
  id: string;
  direction: 'inbound' | 'outbound';
  message: string;
  buttons?: string[];
  timestamp: string;
}

export default function App() {
  const [phone, setPhone] = useState('593988921136')
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [showWebview, setShowWebview] = useState(false)
  const [showListModal, setShowListModal] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const [activeStep, setActiveStep] = useState<number>(1)
  
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const knownOutboundRef = useRef<Set<string>>(new Set())

  const catalogUrl = `${GATEWAY_URL}/catalogo-autos?phone=${phone}&sucursal=Centro`;

  // Estructura oficial del WhatsApp List Message Bottom-Sheet
  const listSections = [
    {
      title: '🏎️ Tipo de Vehículo',
      rows: [
        { id: 'auto_cat_hibridos', title: '⚡ Híbridos / Eléctricos', desc: 'Toyota Yaris Cross (0 Pico y Placa)' },
        { id: 'auto_cat_pickups', title: '🛻 Camionetas 4x4', desc: 'Chevrolet D-Max, Hilux, Poer para trabajo' },
        { id: 'auto_cat_suvs', title: '🚙 SUVs Familiares', desc: 'Sportage, Tucson, Tracker 2026' }
      ]
    },
    {
      title: '💼 Crédito & Servicios',
      rows: [
        { id: 'auto_flow_credito', title: '💰 Simulación de Crédito', desc: 'Entradas desde el 20% y plazos a 60m' },
        { id: 'auto_flow_retoma', title: '🔄 Plan Retoma (Usados)', desc: 'Tu auto usado como parte de pago' },
        { id: 'auto_flow_testdrive', title: '🏎️ Agendar Test Drive', desc: 'Prueba de manejo sin costo a domicilio' },
        { id: 'flow_catalogo', title: '🚘 Vitrina & Cotizador', desc: 'Pantalla emergente con fotos reales' },
        { id: 'flow_asesor', title: '👨‍💼 Hablar con Asesor', desc: 'Atención humana en Quito Centro' }
      ]
    }
  ];

  // Inicializar historial desde localStorage
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
        setMessages([])
      }
    } else {
      setMessages([])
    }
  }, [phone])

  // Scroll automático y contenido al último mensaje
  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
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
          showToast(`¡Cotización ${qCode} registrada! Regresando al chat...`);
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
          showToast('¡Prueba de manejo agendada! Regresando al chat...');
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
          showToast('Garaje enviado. Regresando a WhatsApp...');
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
          showToast('Regresando al chat de WhatsApp...');
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

  // Función auxiliar para determinar botones interactivos según el mensaje
  const getButtonsForMessage = (msg: string): string[] => {
    // 1. Bienvenida (3 botones iniciales limpios y fluidos)
    if (msg.includes('AutoEcuador Motors') && (msg.includes('Alex') || msg.includes('¿En qué podemos ayudarte'))) {
      return ['🚘 Ver Vehículos', '🕒 Horarios y Sedes', '👨‍💼 Hablar con Asesor'];
    }
    // 2. Horarios y Showrooms
    if (msg.includes('Horarios de Atención') || msg.includes('Showrooms AutoEcuador') || msg.includes('📍 *Quito Centro')) {
      return ['🚘 Ver Vehículos', '🏎️ Agendar Visita', '👨‍💼 Hablar con Asesor'];
    }
    // 3. Menú de Categorías de Vehículos / Pantalla emergente
    if (msg.includes('Modelos y Opciones Disponibles') || msg.includes('Ver Opciones') || msg.includes('Modelos y Categorías') || msg.includes('Opciones y Flujos')) {
      return ['📑 Ver Opciones y Flujos', '🕒 Horarios y Sedes', '👨‍💼 Hablar con Asesor'];
    }
    // 4. Categoría Pickups
    if (msg.includes('Pickups') || msg.includes('Camionetas 4x4') || msg.includes('D-Max')) {
      return ['🚘 Abrir en Vitrina', '💰 Simular Cuotas', '🏎️ Test Drive 4x4'];
    }
    // 5. Categoría SUVs Familiares
    if (msg.includes('SUVs Familiares') || msg.includes('Sportage')) {
      return ['🚘 Abrir en Vitrina', '💰 Simular Cuotas', '🏎️ Test Drive SUV'];
    }
    // 6. Categoría Híbridos
    if (msg.includes('Híbrida') || msg.includes('Híbridos') || msg.includes('Yaris Cross')) {
      return ['🚘 Abrir en Vitrina', '💰 Cuotas Híbrido', '🏎️ Test Drive Híbrido'];
    }
    // 7. Simulación de crédito
    if (msg.includes('Asesoría de Financiamiento Automotriz') || msg.includes('aproximadamente para tu entrada')) {
      return ['💰 $3.000 a $5.000', '💰 $5.000 a $8.000', '💰 Más de $8.000'];
    }
    if (msg.includes('Para una Entrada de') || msg.includes('Comparativo Financiero')) {
      return ['🚘 Abrir en Vitrina', '🏎️ Agendar Test Drive', '👨‍💼 Asesor de Crédito'];
    }
    if (msg.includes('Plan Retoma')) {
      return ['🚘 Ver Vehículos', '💰 Simular Cuotas', '👨‍💼 Hablar con Asesor'];
    }
    if (msg.includes('Agenda tu Test Drive en AutoEcuador') || msg.includes('¿Cómo prefieres realizar tu Test Drive?')) {
      return ['🏠 A Domicilio', '📍 En Showroom', '👨‍💼 Hablar con Asesor'];
    }
    if (msg.includes('¡Solicitud de Test Drive Registrada!') || msg.includes('¡Test Drive Agendado')) {
      return ['🚘 Abrir en Vitrina', '💰 Simular Cuotas', '👨‍💼 Hablar con Asesor'];
    }
    if (msg.includes('Cotización Oficial Generada')) {
      return ['🏎️ Agendar Test Drive', '📍 Ver Showrooms', '👨‍💼 Hablar con Asesor'];
    }
    return ['🚘 Ver Vehículos', '🕒 Horarios y Sedes', '👨‍💼 Hablar con Asesor'];
  };

  // Polling periódico para recibir respuestas del backend en orden estricto
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${GATEWAY_URL}/outbound?phone=${phone}`);
        const result = await response.json();
        if (result.success && Array.isArray(result.data)) {
          const newOutbounds = [...result.data].reverse().filter((item: any) => {
            const trimmed = (item.message || '').trim();
            return trimmed && !knownOutboundRef.current.has(trimmed);
          });

          if (newOutbounds.length > 0) {
            setIsTyping(false);
            newOutbounds.forEach((item: any, idx: number) => {
              const msg = item.message || '';
              const btns = getButtonsForMessage(msg);

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
        // Silencio en corte
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

    // Si explícitamente se solicita abrir la vitrina
    if (text === '🚘 Explorar Vitrina' || text === '🚘 Vitrina Virtual' || text === '🚘 Ver en Vitrina' || text === '🚘 Ver Yaris Cross' || text === '🚘 Abrir Vitrina' || text === '🚘 Abrir en Vitrina' || text.toLowerCase() === 'vitrina' || text === '✨ Abrir Vitrina Virtual') {
      setShowWebview(true);
      return;
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
    const lower = text.toLowerCase();
    if (lower.includes('ver vehículo') || lower.includes('ver vehiculo') || lower.includes('vehículos disponibles') || lower.includes('vehiculos disponibles') || lower.includes('tipo de veh') || text === '🚘 Ver Vehículos') {
      interactiveId = 'auto_menu_vehiculos';
    } else if (lower.includes('horario') || lower.includes('sede') || lower.includes('donde estan') || lower.includes('dónde están') || text === '🕒 Horarios y Sedes') {
      interactiveId = 'auto_horarios';
    } else if (lower.includes('híbrido') || lower.includes('hibrido') || lower.includes('eléctrico') || lower.includes('electrico')) {
      interactiveId = 'auto_cat_hibridos';
    } else if (lower.includes('4x4') || lower.includes('camioneta') || lower.includes('pickup') || lower.includes('d-max') || lower.includes('hilux') || lower.includes('poer')) {
      interactiveId = 'auto_cat_pickups';
    } else if (lower.includes('suv') || lower.includes('familiar') || lower.includes('sportage') || lower.includes('tucson') || lower.includes('tracker')) {
      interactiveId = 'auto_cat_suvs';
    } else if (text.includes('3.000') || text.includes('3k')) {
      interactiveId = 'auto_down_3to5';
    } else if (text.includes('5.000 a 8.000') || text.includes('5k')) {
      interactiveId = 'auto_down_5to8';
    } else if (text.includes('Más de 8.000') || text.includes('más de 8000') || text.includes('más de $8.000')) {
      interactiveId = 'auto_down_more8';
    } else if (lower.includes('crédito') || lower.includes('credito') || lower.includes('cuota') || lower.includes('financiamiento')) {
      interactiveId = 'auto_flow_credito';
    } else if (lower.includes('retoma') || lower.includes('usado') || lower.includes('tasar')) {
      interactiveId = 'auto_flow_retoma';
    } else if (lower.includes('domicilio')) {
      interactiveId = 'auto_td_domicilio';
    } else if (lower.includes('showroom')) {
      interactiveId = 'auto_td_showroom';
    } else if (lower.includes('test drive') || lower.includes('prueba de manejo') || lower.includes('agendar visita')) {
      interactiveId = 'auto_flow_testdrive';
    } else if (lower.includes('asesor') || lower.includes('humano')) {
      interactiveId = 'flow_asesor';
    } else if (lower.includes('vitrina') || lower.includes('catálogo') || lower.includes('catalogo')) {
      interactiveId = 'flow_catalogo';
    }

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

      // Consultar de inmediato la respuesta generada
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
                const msg = item.message || '';
                const btns = getButtonsForMessage(msg);
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
          // Polling de respaldo
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
      // Ignorar
    }
    localStorage.removeItem(`chat_history:${phone}`);
    localStorage.clear();
    knownOutboundRef.current.clear();
    setMessages([]);
    setShowWebview(false);
    setIsTyping(false);
    setActiveStep(1);
    showToast('Pantalla limpia. Listo para simular.');
  };

  return (
    <div style={{ display: 'flex', width: '100vw', height: '100vh', background: '#070b0e', color: '#e9edef', fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', overflow: 'hidden' }}>
      
      {/* Toast Notification */}
      {toast && (
        <div style={{ position: 'fixed', top: '1.25rem', right: '1.5rem', background: '#00a884', color: 'white', padding: '0.75rem 1.25rem', borderRadius: '0.6rem', zIndex: 9999, fontWeight: 700, fontSize: '0.85rem', boxShadow: '0 8px 24px rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span>✨</span> {toast}
        </div>
      )}

      {/* 🧭 PANEL LATERAL: GUÍA COMPLETA DEL FLUJO AUTOMOTRIZ */}
      <div style={{ width: '420px', minWidth: '360px', maxWidth: '440px', background: '#0f171c', borderRight: '1px solid #1f2c34', display: 'flex', flexDirection: 'column', height: '100vh', zIndex: 50 }}>
        
        {/* Cabecera del Panel */}
        <div style={{ padding: '1.15rem 1.25rem', borderBottom: '1px solid #1f2c34', background: '#111b21', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div style={{ width: '38px', height: '38px', borderRadius: '10px', background: 'linear-gradient(135deg, #f59e0b, #d97706)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.3rem', boxShadow: '0 4px 12px rgba(245,158,11,0.3)' }}>
                🚗
              </div>
              <div>
                <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 800, color: '#f8fafc' }}>
                  AutoEcuador Motors 🇪🇨
                </h2>
                <p style={{ margin: 0, fontSize: '0.72rem', color: '#00a884', fontWeight: 600 }}>
                  Simulador de Conversación Oficial
                </p>
              </div>
            </div>

            {showWebview && (
              <button 
                onClick={() => setShowWebview(false)}
                style={{ padding: '0.35rem 0.65rem', background: '#e11d48', color: 'white', border: 'none', borderRadius: '6px', fontSize: '0.72rem', fontWeight: 800, cursor: 'pointer' }}
              >
                ✕ Ver Chat
              </button>
            )}
          </div>
        </div>

        {/* Lista de Pasos del Flujo */}
        <div style={{ flex: '1 1 0%', minHeight: 0, overflowY: 'auto', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          
          <div style={{ padding: '0.65rem 0.85rem', background: '#182229', borderRadius: '0.5rem', border: '1px solid #222e35', fontSize: '0.74rem', color: '#8696a0', lineHeight: 1.4 }}>
            💡 <strong style={{ color: '#e9edef' }}>Simula paso a paso:</strong> Haz click en cualquiera de los pasos abajo o escribe directamente en el celular para interactuar con Alex.
          </div>

          {/* PASO 1 */}
          <div style={{ background: activeStep === 1 ? '#1a2730' : '#111b21', border: `1px solid ${activeStep === 1 ? '#00a884' : '#1f2c34'}`, borderRadius: '0.65rem', padding: '0.8rem', transition: 'all 0.2s' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.3rem' }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#00a884', textTransform: 'uppercase' }}>
                Paso 1 • Saludo & Menú
              </span>
              <span style={{ fontSize: '0.68rem', background: '#1f2c34', padding: '0.1rem 0.35rem', borderRadius: '4px', color: '#94a3b8' }}>Inicio</span>
            </div>
            <p style={{ fontSize: '0.74rem', color: '#cbd5e1', margin: '0 0 0.5rem 0', lineHeight: 1.35 }}>
              Saluda al bot. Alex se presenta como asesor multimarca de AutoEcuador Motors y despliega opciones.
            </p>
            <button 
              onClick={() => { setShowWebview(false); handleSendMessage('Hola buenas tardes', 1); }}
              style={{ width: '100%', padding: '0.5rem', background: '#00a884', color: 'white', border: 'none', borderRadius: '0.4rem', fontSize: '0.74rem', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.35rem' }}
            >
              <span>👋</span> Probar: "Hola buenas tardes"
            </button>
          </div>

          {/* PASO 2 */}
          <div style={{ background: activeStep === 2 ? '#1a2730' : '#111b21', border: `1px solid ${activeStep === 2 ? '#00a884' : '#1f2c34'}`, borderRadius: '0.65rem', padding: '0.8rem', transition: 'all 0.2s' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.3rem' }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#f59e0b', textTransform: 'uppercase' }}>
                Paso 2 • Consulta por Modelos
              </span>
              <span style={{ fontSize: '0.68rem', background: '#1f2c34', padding: '0.1rem 0.35rem', borderRadius: '4px', color: '#94a3b8' }}>Autos</span>
            </div>
            <p style={{ fontSize: '0.74rem', color: '#cbd5e1', margin: '0 0 0.5rem 0', lineHeight: 1.35 }}>
              Consulta autos para trabajo, familia o ecología en Ecuador:
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
              <button 
                onClick={() => { setShowWebview(false); setShowListModal(true); setActiveStep(2); }}
                style={{ width: '100%', padding: '0.5rem', background: '#00a884', color: 'white', border: 'none', borderRadius: '0.4rem', fontSize: '0.74rem', fontWeight: 800, cursor: 'pointer', textAlign: 'left', paddingLeft: '0.65rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
              >
                <span>📑</span> Abrir "Ver Opciones y Flujos" (Pantalla Emergente)
              </button>
              <button 
                onClick={() => { setShowWebview(false); handleSendMessage('🕒 Horarios y Sedes', 2); }}
                style={{ width: '100%', padding: '0.45rem', background: '#202c33', color: '#a78bfa', border: '1px solid #374151', borderRadius: '0.4rem', fontSize: '0.73rem', fontWeight: 700, cursor: 'pointer', textAlign: 'left', paddingLeft: '0.65rem' }}
              >
                🕒 "Horarios y Sedes" (Quito, GYE, Cuenca)
              </button>
              <button 
                onClick={() => { setShowWebview(false); handleSendMessage('Qué camionetas 4x4 tienen?', 2); }}
                style={{ width: '100%', padding: '0.45rem', background: '#202c33', color: '#f59e0b', border: '1px solid #374151', borderRadius: '0.4rem', fontSize: '0.73rem', fontWeight: 700, cursor: 'pointer', textAlign: 'left', paddingLeft: '0.65rem' }}
              >
                🛻 "Qué camionetas 4x4 tienen?" (D-Max, Hilux, Poer)
              </button>
              <button 
                onClick={() => { setShowWebview(false); handleSendMessage('Busco un SUV familiar espacioso', 2); }}
                style={{ width: '100%', padding: '0.45rem', background: '#202c33', color: '#38bdf8', border: '1px solid #374151', borderRadius: '0.4rem', fontSize: '0.73rem', fontWeight: 700, cursor: 'pointer', textAlign: 'left', paddingLeft: '0.65rem' }}
              >
                🚙 "Busco un SUV familiar espacioso" (Sportage, Tucson)
              </button>
              <button 
                onClick={() => { setShowWebview(false); handleSendMessage('Quiero un auto híbrido sin pico y placa', 2); }}
                style={{ width: '100%', padding: '0.45rem', background: '#202c33', color: '#10b981', border: '1px solid #374151', borderRadius: '0.4rem', fontSize: '0.73rem', fontWeight: 700, cursor: 'pointer', textAlign: 'left', paddingLeft: '0.65rem' }}
              >
                ⚡ "Quiero un híbrido sin pico y placa" (Yaris Cross)
              </button>
            </div>
          </div>

          {/* PASO 3 */}
          <div style={{ background: activeStep === 3 ? '#1a2730' : '#111b21', border: `1px solid ${activeStep === 3 ? '#00a884' : '#1f2c34'}`, borderRadius: '0.65rem', padding: '0.8rem', transition: 'all 0.2s' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.3rem' }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#38bdf8', textTransform: 'uppercase' }}>
                Paso 3 • Presupuesto & Entrada
              </span>
              <span style={{ fontSize: '0.68rem', background: '#1f2c34', padding: '0.1rem 0.35rem', borderRadius: '4px', color: '#94a3b8' }}>Crédito</span>
            </div>
            <p style={{ fontSize: '0.74rem', color: '#cbd5e1', margin: '0 0 0.5rem 0', lineHeight: 1.35 }}>
              Indica cuánto dinero tienes de entrada. Alex calcula vehículos que entran al 20% y estima las cuotas bancarias.
            </p>
            <button 
              onClick={() => { setShowWebview(false); handleSendMessage('Tengo 5000 de entrada qué me alcanza?', 3); }}
              style={{ width: '100%', padding: '0.5rem', background: '#0284c7', color: 'white', border: 'none', borderRadius: '0.4rem', fontSize: '0.74rem', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.35rem' }}
            >
              <span>💰</span> Probar: "Tengo $5.000 de entrada"
            </button>
          </div>

          {/* PASO 4 */}
          <div style={{ background: activeStep === 4 ? '#1a2730' : '#111b21', border: `1px solid ${activeStep === 4 ? '#00a884' : '#1f2c34'}`, borderRadius: '0.65rem', padding: '0.8rem', transition: 'all 0.2s' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.3rem' }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#ec4899', textTransform: 'uppercase' }}>
                Paso 4 • Pantalla Emergente (Vitrina)
              </span>
              <span style={{ fontSize: '0.68rem', background: '#1f2c34', padding: '0.1rem 0.35rem', borderRadius: '4px', color: '#94a3b8' }}>Webview</span>
            </div>
            <p style={{ fontSize: '0.74rem', color: '#cbd5e1', margin: '0 0 0.5rem 0', lineHeight: 1.35 }}>
              Abre la vitrina virtual dentro de WhatsApp para ver fotos reales, ajustar sliders de cuotas o cotizar en vivo.
            </p>
            <button 
              onClick={() => { setShowWebview(prev => !prev); setActiveStep(4); }}
              style={{ width: '100%', padding: '0.5rem', background: showWebview ? '#475569' : 'linear-gradient(135deg, #d97706, #b45309)', color: 'white', border: 'none', borderRadius: '0.4rem', fontSize: '0.74rem', fontWeight: 800, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.35rem' }}
            >
              {showWebview ? '✕ Cerrar Vitrina y Ver Chat' : '✨ Abrir Vitrina Emergente'}
            </button>
          </div>

          {/* PASO 5 */}
          <div style={{ background: activeStep === 5 ? '#1a2730' : '#111b21', border: `1px solid ${activeStep === 5 ? '#00a884' : '#1f2c34'}`, borderRadius: '0.65rem', padding: '0.8rem', transition: 'all 0.2s' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.3rem' }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#a855f7', textTransform: 'uppercase' }}>
                Paso 5 • Test Drive & Cierre
              </span>
              <span style={{ fontSize: '0.68rem', background: '#1f2c34', padding: '0.1rem 0.35rem', borderRadius: '4px', color: '#94a3b8' }}>Lead</span>
            </div>
            <p style={{ fontSize: '0.74rem', color: '#cbd5e1', margin: '0 0 0.5rem 0', lineHeight: 1.35 }}>
              Simula la solicitud de prueba de manejo a domicilio. Se genera código oficial y se registra en PostgreSQL.
            </p>
            <button 
              onClick={() => { setShowWebview(false); handleSendMessage('Cómo agendo un test drive a domicilio?', 5); }}
              style={{ width: '100%', padding: '0.5rem', background: '#7c3aed', color: 'white', border: 'none', borderRadius: '0.4rem', fontSize: '0.74rem', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.35rem' }}
            >
              <span>🏎️</span> Probar: "Cómo agendo un test drive?"
            </button>
          </div>

          {/* PASO 6 */}
          <div style={{ background: activeStep === 6 ? '#1a2730' : '#111b21', border: `1px solid ${activeStep === 6 ? '#00a884' : '#1f2c34'}`, borderRadius: '0.65rem', padding: '0.8rem', transition: 'all 0.2s' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.3rem' }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#10b981', textTransform: 'uppercase' }}>
                Paso 6 • Asesor Humano
              </span>
              <span style={{ fontSize: '0.68rem', background: '#1f2c34', padding: '0.1rem 0.35rem', borderRadius: '4px', color: '#94a3b8' }}>Handoff</span>
            </div>
            <p style={{ fontSize: '0.74rem', color: '#cbd5e1', margin: '0 0 0.5rem 0', lineHeight: 1.35 }}>
              Transfiere la conversación a un ejecutivo de ventas humano de Quito Centro.
            </p>
            <button 
              onClick={() => { setShowWebview(false); handleSendMessage('Quiero hablar con un asesor comercial humano', 6); }}
              style={{ width: '100%', padding: '0.5rem', background: '#059669', color: 'white', border: 'none', borderRadius: '0.4rem', fontSize: '0.74rem', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.35rem' }}
            >
              <span>👨‍💼</span> Probar: "Hablar con Asesor"
            </button>
          </div>

        </div>

        {/* Footer del Panel */}
        <div style={{ padding: '0.8rem 1rem', borderTop: '1px solid #1f2c34', background: '#111b21', display: 'flex', flexDirection: 'column', gap: '0.5rem', flexShrink: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <label style={{ fontSize: '0.72rem', color: '#8696a0', fontWeight: 600 }}>Línea de Prueba:</label>
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
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem', background: '#070b0e', height: '100vh', overflow: 'hidden' }}>
        
        <div style={{ 
          width: '385px', 
          height: 'min(730px, 92vh)', 
          background: '#0b141a', 
          borderRadius: '40px', 
          border: '10px solid #202c33', 
          boxShadow: '0 25px 60px -15px rgba(0,0,0,0.9), 0 0 0 2px #374151', 
          display: 'flex', 
          flexDirection: 'column', 
          position: 'relative', 
          overflow: 'hidden' 
        }}>
          
          {/* Barra Superior del Sistema Operativo */}
          <div style={{ height: '34px', background: '#202c33', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 1.25rem', fontSize: '0.72rem', color: '#e9edef', fontWeight: 600, flexShrink: 0, zIndex: 10 }}>
            <span>9:41</span>
            <div style={{ width: '80px', height: '16px', background: '#0b141a', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ width: '7px', height: '7px', borderRadius: '50%', background: '#1e293b', marginRight: '4px' }}></div>
              <div style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#f59e0b' }}></div>
            </div>
            <div style={{ display: 'flex', gap: '0.3rem', alignItems: 'center' }}>
              <span>5G</span>
              <span>100%</span>
            </div>
          </div>

          {/* Cabecera Oficial de WhatsApp Business */}
          <div style={{ padding: '0.6rem 0.9rem', background: '#202c33', display: 'flex', gap: '0.75rem', alignItems: 'center', borderBottom: '1px solid #2a3942', flexShrink: 0, zIndex: 10 }}>
            <div style={{ width: '36px', height: '36px', borderRadius: '50%', background: 'linear-gradient(135deg, #d97706, #b45309)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.2rem', fontWeight: 700, color: 'white', flexShrink: 0 }}>
              🚗
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: '0.86rem', fontWeight: 800, color: '#e9edef', display: 'flex', alignItems: 'center', gap: '0.3rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                AutoEcuador Motors
                <span style={{ fontSize: '0.72rem', color: '#00a884' }}>✓</span>
              </div>
              <div style={{ fontSize: '0.68rem', color: '#00a884', fontWeight: 600 }}>
                {isTyping ? 'Alex está escribiendo... ✍️' : 'Asesor Alex • En línea'}
              </div>
            </div>
          </div>

          {/* Hilo de Mensajes de WhatsApp */}
          <div 
            ref={messagesContainerRef}
            style={{ 
              flex: '1 1 0%', 
              minHeight: 0, 
              padding: '1rem', 
              overflowY: 'auto', 
              display: 'flex', 
              flexDirection: 'column', 
              gap: '0.65rem', 
              backgroundImage: 'radial-gradient(circle, #151d22 10%, transparent 11%)', 
              backgroundSize: '14px 14px' 
            }}
          >
            {messages.length === 0 && (
              <div style={{ margin: 'auto', textAlign: 'center', padding: '1.5rem', maxWidth: '85%' }}>
                <div style={{ display: 'inline-block', background: '#182229', padding: '0.45rem 0.9rem', borderRadius: '8px', border: '1px solid #222e35', fontSize: '0.74rem', color: '#f59e0b', marginBottom: '0.85rem', boxShadow: '0 2px 6px rgba(0,0,0,0.2)' }}>
                  🔒 Cifrado de extremo a extremo
                </div>
                <div style={{ fontSize: '0.82rem', color: '#94a3b8', lineHeight: 1.5, fontWeight: 500 }}>
                  Pantalla limpia. Inicia tu consulta escribiendo un mensaje abajo o seleccionando un paso en la guía lateral.
                </div>
              </div>
            )}

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
                          onClick={() => {
                            if (btnText.includes('Vitrina') || btnText.includes('Catálogo')) {
                              setShowWebview(true);
                            } else if (btnText.includes('Ver Opciones') || btnText.includes('Ver Vehículos')) {
                              setShowListModal(true);
                            } else {
                              handleSendMessage(btnText);
                            }
                          }}
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
              <div style={{ alignSelf: 'flex-start', background: '#202c33', padding: '0.5rem 0.85rem', borderRadius: '0 12px 12px 12px', fontSize: '0.74rem', color: '#00a884', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <span style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', background: '#00a884' }}></span>
                Alex está preparando la respuesta...
              </div>
            )}
          </div>

          {/* Barra Inferior para Escribir Mensajes */}
          <form 
            onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }} 
            style={{ padding: '0.55rem 0.75rem', background: '#202c33', display: 'flex', gap: '0.5rem', alignItems: 'center', borderTop: '1px solid #2a3942', flexShrink: 0, zIndex: 10 }}
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

          {/* 📑 BOTTOM SHEET MODAL (PANTALLITA EMERGENTE NATIVA DE WHATSAPP) */}
          {showListModal && (
            <div style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(0, 0, 0, 0.72)',
              zIndex: 900,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'flex-end',
              animation: 'fadeIn 0.2s ease-out'
            }}>
              <div style={{
                background: '#111b21',
                borderTopLeftRadius: '16px',
                borderTopRightRadius: '16px',
                borderTop: '1px solid #222e35',
                maxHeight: '80%',
                display: 'flex',
                flexDirection: 'column',
                boxShadow: '0 -8px 30px rgba(0,0,0,0.8)'
              }}>
                {/* Cabecera del Bottom Sheet */}
                <div style={{
                  padding: '0.85rem 1rem',
                  borderBottom: '1px solid #202c33',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                  flexShrink: 0
                }}>
                  <button 
                    onClick={() => setShowListModal(false)}
                    style={{ background: 'transparent', border: 'none', color: '#8696a0', fontSize: '1.1rem', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                  >
                    ✕
                  </button>
                  <span style={{ fontSize: '0.86rem', fontWeight: 700, color: '#e9edef', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    📑 Ver Opciones y Flujos
                  </span>
                </div>

                {/* Contenido scrolleable de secciones y filas */}
                <div style={{ overflowY: 'auto', padding: '0.5rem 0 1rem 0' }}>
                  {listSections.map((sec, sIdx) => (
                    <div key={sIdx} style={{ marginBottom: '0.75rem' }}>
                      <div style={{ padding: '0.4rem 1rem', fontSize: '0.72rem', fontWeight: 800, color: '#8696a0', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                        {sec.title}
                      </div>
                      {sec.rows.map(row => (
                        <div 
                          key={row.id}
                          onClick={() => {
                            setShowListModal(false);
                            if (row.id === 'flow_catalogo') {
                              setShowWebview(true);
                            } else {
                              handleSendMessage(row.title);
                            }
                          }}
                          style={{
                            padding: '0.65rem 1rem',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            cursor: 'pointer',
                            borderBottom: '1px solid rgba(255,255,255,0.03)',
                            transition: 'background 0.15s'
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.background = '#1a2730'}
                          onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                        >
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
                            <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#e9edef' }}>
                              {row.title}
                            </div>
                            <div style={{ fontSize: '0.71rem', color: '#8696a0' }}>
                              {row.desc}
                            </div>
                          </div>
                          {/* Radio button circle */}
                          <div style={{
                            width: '18px',
                            height: '18px',
                            borderRadius: '50%',
                            border: '2px solid #64748b',
                            flexShrink: 0,
                            marginLeft: '0.75rem'
                          }} />
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* 🪟 PANTALLA EMERGENTE IN-APP BROWSER (Navegación Interna sin salir de WhatsApp) */}
          {showWebview && (
            <div style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: '#090d16',
              zIndex: 999,
              display: 'flex',
              flexDirection: 'column',
              boxShadow: '0 0 50px rgba(0,0,0,0.95)'
            }}>
              {/* Barra Superior del In-App Browser de WhatsApp */}
              <div style={{ 
                height: '46px', 
                background: '#0f172a', 
                color: '#e9edef', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'space-between', 
                padding: '0 0.85rem', 
                borderBottom: '1px solid #1e293b',
                fontSize: '0.78rem',
                flexShrink: 0
              }}>
                <button 
                  onClick={() => setShowWebview(false)} 
                  style={{ background: '#e11d48', border: 'none', color: 'white', fontSize: '0.72rem', cursor: 'pointer', padding: '0.35rem 0.65rem', fontWeight: 800, borderRadius: '6px' }}
                >
                  ✕ Cerrar
                </button>
                
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  <span style={{ fontWeight: 800, fontSize: '0.76rem', color: '#f8fafc' }}>WhatsApp In-App Browser</span>
                  <span style={{ fontSize: '0.62rem', color: '#10b981' }}>
                    🔒 autoecuador.com/catalogo
                  </span>
                </div>

                <button 
                  onClick={() => setShowWebview(false)} 
                  style={{ background: '#1e293b', border: '1px solid #334155', color: '#38bdf8', fontSize: '0.7rem', borderRadius: '6px', padding: '0.35rem 0.65rem', cursor: 'pointer', fontWeight: 700 }}
                >
                  Volver al Chat
                </button>
              </div>

              {/* Iframe de la Vitrina Oficial */}
              <iframe 
                src={catalogUrl}
                style={{ width: '100%', flex: '1 1 0%', minHeight: 0, border: 'none', background: '#020617' }}
                title="Vitrina Virtual AutoEcuador Motors"
                allow="camera; microphone; geolocation"
              />
            </div>
          )}

        </div>

      </div>

    </div>
  )
}
