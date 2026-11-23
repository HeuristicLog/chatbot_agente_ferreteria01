import React, { useState } from 'react';

export default function ChatwootHub({ defaultTab = 'metricas', onTabChange }) {
    const [activeTab, setActiveTab] = useState(defaultTab);
    const [iframeKey, setIframeKey] = useState(Date.now());
    const [isLoading, setIsLoading] = useState(true);

    const CHATBOT_API_URL = import.meta.env.VITE_CHATBOT_API_URL || "http://localhost:8085";

    const tabs = [
        { id: 'metricas', label: '📊 Métricas Chatwoot', path: '/metricas', desc: 'KPIs en vivo de WhatsApp, Chatwoot, tiempos FRT y handoffs' },
        { id: 'ejecutivo', label: '📈 Reporte Ejecutivo', path: '/reporte-ejecutivo', desc: 'Reporte gerencial, estadísticas de ventas y exportación Excel' },
        { id: 'dragdrop', label: '🎯 Auditoría Drag & Drop', path: '/reporte-drag-drop', desc: 'Auditoría interactiva de conversaciones y evaluación con IA' }
    ];

    const currentTabInfo = tabs.find(t => t.id === activeTab) || tabs[0];
    const targetUrl = `${CHATBOT_API_URL}${currentTabInfo.path}`;

    const handleTabClick = (tabId) => {
        setActiveTab(tabId);
        setIsLoading(true);
        if (onTabChange) {
            onTabChange(tabId);
        }
    };

    const handleRefresh = () => {
        setIsLoading(true);
        setIframeKey(Date.now());
    };

    const handleOpenExternal = () => {
        window.open(targetUrl, '_blank', 'noopener,noreferrer');
    };

    return (
        <section className="card" style={{ padding: '1rem', background: 'transparent', boxShadow: 'none' }}>
            {/* Header de Pestañas y Acciones */}
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '1rem',
                marginBottom: '1rem'
            }}>
                {/* Selector de Pestañas (Sub-tabs) */}
                <div style={{
                    display: 'flex',
                    background: '#f1f5f9',
                    padding: '0.25rem',
                    borderRadius: '10px',
                    gap: '0.25rem',
                    flexWrap: 'wrap'
                }}>
                    {tabs.map((tab) => {
                        const isActive = activeTab === tab.id;
                        return (
                            <button
                                key={tab.id}
                                onClick={() => handleTabClick(tab.id)}
                                style={{
                                    padding: '0.6rem 1.25rem',
                                    borderRadius: '8px',
                                    border: 'none',
                                    background: isActive ? 'white' : 'transparent',
                                    color: isActive ? '#3b82f6' : '#64748b',
                                    fontWeight: isActive ? '600' : '500',
                                    cursor: 'pointer',
                                    boxShadow: isActive ? '0 4px 6px -1px rgba(0, 0, 0, 0.08)' : 'none',
                                    transition: 'all 0.2s ease',
                                    fontSize: '0.92rem',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.4rem'
                                }}
                            >
                                {tab.label}
                            </button>
                        );
                    })}
                </div>

                {/* Acciones Rápidas */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        fontSize: '0.85rem',
                        fontWeight: '600',
                        color: '#16a34a',
                        background: '#dcfce7',
                        padding: '0.35rem 0.75rem',
                        borderRadius: '20px'
                    }}>
                        <span style={{
                            width: '8px',
                            height: '8px',
                            backgroundColor: '#22c55e',
                            borderRadius: '50%',
                            boxShadow: '0 0 6px #22c55e'
                        }}></span>
                        Conectado: {CHATBOT_API_URL.replace(/^https?:\/\//, '')}
                    </span>

                    <button
                        onClick={handleRefresh}
                        title="Recargar panel"
                        style={{
                            background: 'white',
                            border: '1px solid #e2e8f0',
                            padding: '0.45rem 0.85rem',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.35rem',
                            fontSize: '0.88rem',
                            fontWeight: '500',
                            color: '#475569',
                            boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
                        }}
                    >
                        🔄 Recargar
                    </button>

                    <button
                        onClick={handleOpenExternal}
                        title="Abrir en ventana completa"
                        style={{
                            background: '#3b82f6',
                            color: 'white',
                            border: 'none',
                            padding: '0.45rem 0.85rem',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.35rem',
                            fontSize: '0.88rem',
                            fontWeight: '600',
                            boxShadow: '0 2px 4px rgba(59, 130, 246, 0.3)'
                        }}
                    >
                        Abrir Externo ↗
                    </button>
                </div>
            </div>

            {/* Contenedor del Iframe con indicador de carga */}
            <div style={{
                position: 'relative',
                width: '100%',
                height: 'calc(100vh - 210px)',
                minHeight: '620px',
                borderRadius: '12px',
                overflow: 'hidden',
                background: 'white',
                boxShadow: '0 4px 15px rgba(0, 0, 0, 0.05)',
                border: '1px solid #e2e8f0'
            }}>
                {isLoading && (
                    <div style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'center',
                        alignItems: 'center',
                        background: '#f8fafc',
                        zIndex: 10,
                        gap: '1rem'
                    }}>
                        <div style={{
                            width: '40px',
                            height: '40px',
                            border: '4px solid #e2e8f0',
                            borderTop: '4px solid #3b82f6',
                            borderRadius: '50%',
                            animation: 'spin 1s linear infinite'
                        }}></div>
                        <p style={{ color: '#64748b', fontSize: '0.95rem', margin: 0, fontWeight: '500' }}>
                            Cargando {currentTabInfo.label}...
                        </p>
                    </div>
                )}

                <iframe
                    key={`${activeTab}-${iframeKey}`}
                    src={targetUrl}
                    title={currentTabInfo.label}
                    onLoad={() => setIsLoading(false)}
                    style={{
                        width: '100%',
                        height: '100%',
                        border: 'none',
                        display: 'block'
                    }}
                />
            </div>

            <style>{`
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            `}</style>
        </section>
    );
}
