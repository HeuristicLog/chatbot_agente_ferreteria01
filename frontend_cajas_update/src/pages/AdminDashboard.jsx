import React, { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { getLogs, getEstadoCajas, getSucursales, createSucursal, updateSucursal, deleteSucursal } from "../api/admin";
import { getContacts, createContact, updateContact, deleteContact } from "../api/contacts";
import { getUsers, createUser, updateUser, deleteUser, getRoles } from "../api/users";
import { getCajas as getCajasDB, getTodasCajas, createCaja, updateCaja, deleteCaja } from "../api/cajas";
import { getGrabaciones, getTranscripciones, getAnalisis, updateRespuesta } from "../api/grabaciones";
import "../styles/dashboard.css";
import { SentimentPieChart, ActivityBarChart } from "../components/dashboard/DashboardCharts";
import CashierList from "../components/dashboard/CashierList";
import CashierDetailModal from "../components/dashboard/CashierDetailModal";
import BoxDetailModal from "../components/dashboard/BoxDetailModal";
import MetricsManager from '../components/dashboard/MetricsManager';
import CashierClientsModal from '../components/dashboard/CashierClientsModal';
import CashierAtencionesModal from '../components/dashboard/CashierAtencionesModal';
import ChatwootHub from '../components/chatwoot/ChatwootHub';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis } from 'recharts';
import { useCustomDialog } from "../components/common/CustomDialog";
import { getEcuadorDateString, getEcuadorTimeString, getEcuadorDateTimeString } from "../utils/date";

// Helper functions for human-readable audit logs
const getAccionBadge = (tipo) => {
    switch (tipo) {
        case 'INSERT':
            return { label: 'Creó nuevo registro', color: '#166534', bg: '#dcfce7', border: '#bbf7d0', verb: 'creó' };
        case 'UPDATE':
            return { label: 'Actualizó información', color: '#92400e', bg: '#fef3c7', border: '#fde68a', verb: 'actualizó' };
        case 'DELETE':
            return { label: 'Eliminó registro', color: '#991b1b', bg: '#fee2e2', border: '#fecaca', verb: 'eliminó' };
        default:
            return { label: tipo, color: '#374151', bg: '#f3f4f6', border: '#e5e7eb', verb: 'modificó' };
    }
};

const getTablaHumanReadable = (tabla) => {
    const map = {
        'cajas': 'Caja / Punto de Venta',
        'usuarios': 'Usuario del Sistema',
        'contactos': 'Personal / Contacto',
        'sucursales': 'Sucursal',
        'categorias_preguntas': 'Categoría de Métrica',
        'catalogo_preguntas': 'Pregunta de Evaluación',
        'analisis_general': 'Calificación de Atención',
        'respuestas_evaluacion': 'Criterio Evaluado',
        'grabaciones': 'Grabación de Audio',
        'atenciones': 'Atención al Cliente'
    };
    return map[tabla] || tabla.replace(/_/g, ' ');
};

const getHumanLogDescription = (log) => {
    const actor = log.usuario_actor ? log.usuario_actor.username : "Sistema";
    const accion = getAccionBadge(log.tipo_accion);
    const entidad = getTablaHumanReadable(log.tabla_afectada);
    
    // Intenta extraer detalles específicos del cambio si existen
    let detalle = "";
    if (log.cambios_json && typeof log.cambios_json === 'object') {
        if (log.cambios_json.nombre_identificador) {
            detalle = ` "${log.cambios_json.nombre_identificador}"`;
        } else if (log.cambios_json.nombre) {
            detalle = ` "${log.cambios_json.nombre}"`;
        } else if (log.cambios_json.texto_pregunta) {
            detalle = ` "${log.cambios_json.texto_pregunta.slice(0, 35)}..."`;
        } else if (log.cambios_json.username) {
            detalle = ` "${log.cambios_json.username}"`;
        } else if (log.cambios_json.estado_operativo) {
            detalle = ` (Estado: ${log.cambios_json.estado_operativo})`;
        } else if (log.cambios_json.activo !== undefined) {
            detalle = log.cambios_json.activo ? ' (Habilitada)' : ' (Deshabilitada)';
        }
    }
    
    return {
        actor,
        accion,
        entidad,
        detalle,
        resumen: `El usuario ${actor} ${accion.verb} ${entidad.toLowerCase()}${detalle}`
    };
};

export default function AdminDashboard({ user }) {
    const { alert, confirm } = useCustomDialog();
    const navigate = useNavigate();
    const [currentView, setCurrentView] = useState("panel");
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    // Settings State removed


    // Box Configuration State
    const [boxConfigs, setBoxConfigs] = useState([]);
    const [boxStates, setBoxStates] = useState({});

    // Toggle States for Views
    const [panelViewMode, setPanelViewMode] = useState('cajeros'); // 'cajeros' or 'cajas'
    const [configuracionViewMode, setConfiguracionViewMode] = useState('grabaciones'); // 'grabaciones' or 'cajas'
    const [personalViewMode, setPersonalViewMode] = useState('contactos'); // 'contactos' or 'usuarios'
    const [analisisViewMode, setAnalisisViewMode] = useState('cajas'); // 'cajas' or 'cajeros'

    // Fetch real-time Box States and configs periodically
    useEffect(() => {
        let intervalId;
        if (currentView === "configuracion" && configuracionViewMode === "cajas") {
            const fetchRealtimeCajas = async () => {
                try {
                    // Fetch both box status map and boxes configurations
                    const [states, cajasData] = await Promise.all([
                        getEstadoCajas(),
                        getTodasCajas()
                    ]);
                    
                    const stateMap = {};
                    states.forEach(s => {
                        stateMap[s.codigo] = s.tiene_sesion_abierta;
                    });
                    setBoxStates(stateMap);

                    const formattedBoxes = cajasData.map(b => ({
                        id: b.id,
                        name: b.nombre_identificador,
                        description: b.ubicacion,
                        assignedContactId: b.contacto_id,
                        recordingMode: "schedule",
                        enabled: b.activo,
                        en_uso: b.en_uso,
                        ultima_conexion: b.ultima_conexion,
                        estado_operativo: b.estado_operativo,
                        motivo_estado: b.motivo_estado,
                        estado_grabacion: b.estado_grabacion,
                        turno_manana_inicio: b.turno_manana_inicio,
                        turno_manana_fin: b.turno_manana_fin,
                        turno_tarde_inicio: b.turno_tarde_inicio,
                        turno_tarde_fin: b.turno_tarde_fin,
                        grabacion_habilitada: b.grabacion_habilitada,
                        en_pausa: b.en_pausa,
                        duracion_segmento_minutos: b.duracion_segmento_minutos,
                        microfono_asignado: b.microfono_asignado,
                        lista_microfonos: b.lista_microfonos,
                        version_actual: b.version_actual
                    }));
                    
                    // Sort boxes by name alphabetically
                    formattedBoxes.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
                    setBoxConfigs(formattedBoxes);
                } catch (error) {
                    console.error("Error fetching real-time boxes:", error);
                }
            };
            fetchRealtimeCajas();
            intervalId = setInterval(fetchRealtimeCajas, 3000);
        }
        return () => {
            if (intervalId) clearInterval(intervalId);
        };
    }, [currentView, configuracionViewMode]);

    const [showBoxModal, setShowBoxModal] = useState(false);
    const [currentBox, setCurrentBox] = useState(null);
    const [boxForm, setBoxForm] = useState({
        name: "",
        description: "",
        assignedContactId: "",
                sucursal_id: "",
        recordingMode: "schedule",
        enabled: true,
        estado_operativo: "Operativa",
        motivo_estado: ""
    });

    // Estado Modal States
    const [showEstadoModal, setShowEstadoModal] = useState(false);
    const [estadoForm, setEstadoForm] = useState({
        id: null,
        estado_operativo: "Operativa",
        motivo_estado: ""
    });

    const openEstadoModal = (box) => {
        setEstadoForm({
            id: box.id,
            estado_operativo: box.estado_operativo || "Operativa",
            motivo_estado: box.motivo_estado || ""
        });
        setShowEstadoModal(true);
    };

    const saveEstadoBox = async () => {
        try {
            await updateCaja(estadoForm.id, {
                estado_operativo: estadoForm.estado_operativo,
                motivo_estado: estadoForm.motivo_estado
            });
            setShowEstadoModal(false);
            loadData(); // refresh the table
        } catch (error) {
            console.error("Error updating box state:", error);
            alert("Error actualizando el estado de la caja");
        }
    };

    // updateBoxConfig removed


    // Box CRUD Handlers
    const handleCreateBox = async (e) => {
        e.preventDefault();
        if (!boxForm.name) {
            alert("El nombre de la caja es obligatorio");
            return;
        }

        try {
            const boxData = {
                nombre_identificador: boxForm.name,
                ubicacion: boxForm.description,
                sucursal_id: boxForm.sucursal_id || null,
                activo: boxForm.estado_operativo === 'Operativa',
                contacto_id: boxForm.assignedContactId || null,
                estado_operativo: boxForm.estado_operativo,
                motivo_estado: boxForm.motivo_estado,
                turno_manana_inicio: boxForm.turno_manana_inicio || "07:30:00",
                turno_manana_fin: boxForm.turno_manana_fin || "12:00:00",
                turno_tarde_inicio: boxForm.turno_tarde_inicio || "16:00:00",
                turno_tarde_fin: boxForm.turno_tarde_fin || "19:00:00",
                grabacion_habilitada: boxForm.grabacion_habilitada !== false,
                en_pausa: boxForm.en_pausa === true,
                duracion_segmento_minutos: boxForm.duracion_segmento_minutos || 10,
                microfono_asignado: boxForm.microfono_asignado || null
            };

            if (currentBox) {
                // Edit
                await updateCaja(currentBox.id, boxData);
                await loadData();
                await alert({ type: "success", message: "Caja actualizada exitosamente" });
            } else {
                // Create
                await createCaja(boxData);
                await loadData();
                await alert({ type: "success", message: "Caja creada exitosamente" });
            }
            setShowBoxModal(false);
            setBoxForm({
                name: "",
                description: "",
                assignedContactId: "",
                sucursal_id: "",
                recordingMode: "schedule",
                enabled: true,
                estado_operativo: "Operativa",
                motivo_estado: "",
                turno_manana_inicio: "07:30:00",
                turno_manana_fin: "12:00:00",
                turno_tarde_inicio: "16:00:00",
                turno_tarde_fin: "19:00:00",
                grabacion_habilitada: true,
                en_pausa: false
            });
            setCurrentBox(null);
        } catch (error) {
            console.error("Error saving box:", error);
            alert("Error al guardar caja: " + (error.response?.data?.detail || error.message));
        }
    };

    const handleDeleteBox = async (id) => {
        const isConfirmed = await confirm({
            title: "¿Estás seguro?",
            message: "¿Está seguro de que desea eliminar esta caja?",
            confirmText: "Sí, eliminar",
            cancelText: "Cancelar"
        });
        if (isConfirmed) {
            try {
                await deleteCaja(id);
                setBoxConfigs(prev => prev.filter(box => box.id !== id));
                await alert({ type: "success", message: "Caja eliminada exitosamente" });
            } catch (error) {
                console.error("Error deleting box:", error);
                await alert({ type: "error", message: "Error al eliminar caja" });
            }
        }
    };

    const openBoxModal = (box = null) => {
        if (box) {
            setCurrentBox(box);
            setBoxForm({
                name: box.name,
                description: box.description || "",
                sucursal_id: box.sucursal_id || "",
                assignedContactId: box.assignedContactId || "",
                recordingMode: box.recordingMode,
                enabled: box.enabled,
                estado_operativo: box.estado_operativo || "Operativa",
                motivo_estado: box.motivo_estado || "",
                turno_manana_inicio: box.turno_manana_inicio || "07:30:00",
                turno_manana_fin: box.turno_manana_fin || "12:00:00",
                turno_tarde_inicio: box.turno_tarde_inicio || "16:00:00",
                turno_tarde_fin: box.turno_tarde_fin || "19:00:00",
                grabacion_habilitada: box.grabacion_habilitada !== false,
                en_pausa: box.en_pausa === true,
                duracion_segmento_minutos: box.duracion_segmento_minutos || 10,
                microfono_asignado: box.microfono_asignado || "",
                lista_microfonos: box.lista_microfonos || []
            });
        } else {
            setCurrentBox(null);
            setBoxForm({
                name: "",
                description: "",
                assignedContactId: "",
                sucursal_id: "",
                recordingMode: "continuo",
                enabled: true,
                estado_operativo: "Operativa",
                motivo_estado: "",
                turno_manana_inicio: "07:30:00",
                turno_manana_fin: "12:00:00",
                turno_tarde_inicio: "16:00:00",
                turno_tarde_fin: "19:00:00",
                grabacion_habilitada: true,
                en_pausa: false,
                duracion_segmento_minutos: 10,
                microfono_asignado: "",
                lista_microfonos: []
            });
        }
        setShowBoxModal(true);
    };

    // Recordings State
    const [allRecordings, setAllRecordings] = useState([]);
    const [currentPage, setCurrentPage] = useState(1);
    const itemsPerPage = 10;
    const [selectedRecording, setSelectedRecording] = useState(null);
    const [selectedAnalysis, setSelectedAnalysis] = useState(null);
    const [transcriptionData, setTranscriptionData] = useState(null);
    const [isTranscriptionLoading, setIsTranscriptionLoading] = useState(false);
    const [transcriptionError, setTranscriptionError] = useState(null);
    const [analysisData, setAnalysisData] = useState(null);
    const [isAnalysisLoading, setIsAnalysisLoading] = useState(false);

    // Individual Response Editing State
    const [editingResponseId, setEditingResponseId] = useState(null);
    const [tempResponseScore, setTempResponseScore] = useState("");

    // Fetch Transcriptions Effect
    useEffect(() => {
        if (selectedRecording) {
            const fetchTranscripciones = async () => {
                setIsTranscriptionLoading(true);
                setTranscriptionError(null);
                try {
                    const data = await getTranscripciones(selectedRecording.rawId);
                    setTranscriptionData(data);
                } catch (error) {
                    console.error("Error fetching transcription:", error);
                    setTranscriptionError(error.response?.data?.detail || error.message || "Error al cargar la transcripción");
                    setTranscriptionData(null);
                } finally {
                    setIsTranscriptionLoading(false);
                }
            };
            fetchTranscripciones();
        } else {
            setTranscriptionData(null);
            setTranscriptionError(null);
        }
    }, [selectedRecording]);

    // Fetch Analysis Effect
    useEffect(() => {
        if (selectedAnalysis) {
            const fetchAnalisisData = async () => {
                setIsAnalysisLoading(true);
                try {
                    const data = await getAnalisis(selectedAnalysis.rawId);
                    setAnalysisData(data);
                } catch (error) {
                    console.error("Error fetching analysis:", error);
                    setAnalysisData(null);
                } finally {
                    setIsAnalysisLoading(false);
                }
            };
            fetchAnalisisData();
        } else {
            setAnalysisData(null);
        }
    }, [selectedAnalysis]);

    const handleSaveResponseScore = async (respId) => {
        if (!analysisData) return;
        try {
            const val = tempResponseScore === "" ? null : parseFloat(tempResponseScore);
            await updateRespuesta(respId, { puntaje_obtenido: val });

            // Re-fetch analysis to show updated nested relations and scores
            setIsAnalysisLoading(true);
            const updatedAnalysis = await getAnalisis(selectedAnalysis.rawId);
            setAnalysisData(updatedAnalysis);
            setEditingResponseId(null);
        } catch (error) {
            console.error("Error updating response score:", error);
            alert("Error al actualizar la calificación del ítem.");
        } finally {
            setIsAnalysisLoading(false);
        }
    };

    // Filters State
    const [filters, setFilters] = useState({
        search: "",
        date: "",
        time: ""
    });

    // User Management State
    const [showUserModal, setShowUserModal] = useState(false);
    const [isEditingUser, setIsEditingUser] = useState(false);
    const [users, setUsers] = useState([]);
    const [roles, setRoles] = useState([]);
    const [newUser, setNewUser] = useState({
        id: null,
        username: "",
        password: "",
        confirmPassword: "",
        nombre: "",
        role: "cajero", // Will be mapped to ID
        cajaAsignada: "",
        estado: "activo",
        contacto_id: ""
    });

    // Contacts Management State
    const [contacts, setContacts] = useState([]);
    const [sucursales, setSucursales] = useState([]);
    const [showContactModal, setShowContactModal] = useState(false);
    const [showSucursalModal, setShowSucursalModal] = useState(false);
    const [currentSucursal, setCurrentSucursal] = useState(null);
    const [sucursalForm, setSucursalForm] = useState({ nombre: "", direccion: "", activa: true });
    const [showCreateUserFromContactModal, setShowCreateUserFromContactModal] = useState(false);
    const [currentContact, setCurrentContact] = useState(null);
    const [contactsCurrentPage, setContactsCurrentPage] = useState(1);
    const [contactForm, setContactForm] = useState({
        nombre: "",
        apellido: "",
        email: "",
        telefono: "",
        direccion: "",
        rol: "Cajero",
        sucursal_id: ""
    });
    const [userFromContactForm, setUserFromContactForm] = useState({
        username: "",
        password: "",
        confirmPassword: "",
        role: "cajero",
        cajaAsignada: ""
    });

    // New Modals State
    const [selectedCashierForDetail, setSelectedCashierForDetail] = useState(null);
    const [selectedBoxForDetail, setSelectedBoxForDetail] = useState(null);
    const [selectedCashierForClients, setSelectedCashierForClients] = useState(null);
    const [selectedCashierForAtenciones, setSelectedCashierForAtenciones] = useState(null);


    const isLoadingRef = useRef(false);

    // Fetch Data on Mount
    const loadData = async (silent = false) => {
        if (isLoadingRef.current) return;
        isLoadingRef.current = true;
        try {
            const [usersData, contactsData, rolesData, cajasData, grabacionesData, sucursalesData] = await Promise.all([
                getUsers(),
                getContacts(),
                getRoles(),
                getTodasCajas(),
                getGrabaciones(),
                getSucursales()
            ]);
            setUsers(usersData);
            setRoles(rolesData);

            // Format Grabaciones
            const formattedRecordings = grabacionesData.map(g => {
                const hrs = Math.floor((g.duracion_segundos || 0) / 3600);
                const mins = Math.floor(((g.duracion_segundos || 0) % 3600) / 60);
                const secs = (g.duracion_segundos || 0) % 60;
                let durText = '';
                if (hrs > 0) durText += `${hrs}:`;
                durText += `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;

                return {
                    id: g.id.substring(0, 8),
                    rawId: g.id,
                    usuario_id: g.usuario_id,
                    contacto_id: g.contacto_id,
                    caja_id: g.caja_id,
                    cajero: g.contacto ? `${g.contacto.nombre} ${g.contacto.apellido}` : (g.usuario ? (g.usuario.contacto ? `${g.usuario.contacto.nombre} ${g.usuario.contacto.apellido}` : g.usuario.username) : "Desconocido"),
                    caja: g.caja ? g.caja.nombre_identificador : "Desconocida",
                    fecha: getEcuadorDateString(g.fecha_hora_inicio),
                    hora: getEcuadorTimeString(g.fecha_hora_inicio),
                    fecha_hora_inicio: g.fecha_hora_inicio,
                    duracion: durText,
                    duracion_segundos: g.duracion_segundos != null ? g.duracion_segundos : 0,
                    transcripcion: g.transcripcion || null,
                    analisis: g.analisis || null
                };
            });
            setAllRecordings(formattedRecordings);

            // Process Contacts to check for existing users
            const processedContacts = contactsData.map(contact => {
                const hasUser = usersData.some(u => u.contacto_id === contact.id);
                return { ...contact, hasUserAccount: hasUser };
            });
            setContacts(processedContacts);

            // Format Cajas
            const formattedBoxes = cajasData.map(b => ({
                id: b.id,
                name: b.nombre_identificador,
                description: b.ubicacion,
                sucursal_id: b.sucursal_id || null,
                assignedContactId: b.contacto_id,
                recordingMode: "schedule",
                enabled: b.activo,
                en_uso: b.en_uso,
                ultima_conexion: b.ultima_conexion,
                estado_operativo: b.estado_operativo,
                motivo_estado: b.motivo_estado,
                estado_grabacion: b.estado_grabacion,
                turno_manana_inicio: b.turno_manana_inicio,
                turno_manana_fin: b.turno_manana_fin,
                turno_tarde_inicio: b.turno_tarde_inicio,
                turno_tarde_fin: b.turno_tarde_fin,
                grabacion_habilitada: b.grabacion_habilitada,
                en_pausa: b.en_pausa,
                duracion_segmento_minutos: b.duracion_segmento_minutos,
                microfono_asignado: b.microfono_asignado,
                lista_microfonos: b.lista_microfonos,
                version_actual: b.version_actual
            }));
            
            // Sort boxes by name alphabetically
            formattedBoxes.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
            
            setBoxConfigs(formattedBoxes);
            
            if (sucursalesData && sucursalesData.length === 0) {
                try {
                    await createSucursal({ nombre: "Sucursal Central", direccion: "Centro", activa: true });
                    await createSucursal({ nombre: "Sucursal Norte", direccion: "Norte", activa: true });
                    const newSucursales = await getSucursales();
                    setSucursales(newSucursales);
                } catch (e) {
                    console.error("Auto-seed failed", e);
                    setSucursales(sucursalesData);
                }
            } else {
                setSucursales(sucursalesData);
            }
        } catch (error) {
            console.error("Error loading data:", error);
            if (error.response?.status === 401) {
                if (!silent) {
                    alert("Tu sesión ha expirado por inactividad. Por favor, inicia sesión nuevamente.");
                }
                localStorage.removeItem("token");
                localStorage.removeItem("user");
                navigate("/login");
                window.location.reload();
            } else {
                if (!silent) {
                    alert("Error cargando datos: " + (error.response?.data?.detail || error.message));
                }
            }
        } finally {
            isLoadingRef.current = false;
        }
    };

    useEffect(() => {
        loadData();
        const intervalId = setInterval(() => {
            loadData(true);
        }, 5000);
        return () => clearInterval(intervalId);
    }, []);

    // Logs State
    const [logs, setLogs] = useState([]);
    const [logsTotal, setLogsTotal] = useState(0);
    const [logsPage, setLogsPage] = useState(1);
    const [logsDateFilter, setLogsDateFilter] = useState('');
    const logsLimit = 10;

    const fetchLogsData = async () => {
        try {
            const logsData = await getLogs(logsPage, logsLimit, logsDateFilter);
            setLogs(logsData.items || []);
            setLogsTotal(logsData.total || 0);
        } catch (error) {
            console.error("Error fetching logs", error);
        }
    };

    useEffect(() => {
        fetchLogsData();
    }, [logsPage, logsDateFilter]);

    const handleLogout = () => {
        navigate("/login");
        window.location.reload();
    };

    // Notifications State
    const [showNotifications, setShowNotifications] = useState(false);
    const notificationsRef = React.useRef(null);

    useEffect(() => {
        function handleClickOutside(event) {
            if (notificationsRef.current && !notificationsRef.current.contains(event.target)) {
                setShowNotifications(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, []);

    // Filter Logic
    // getDiff removed


    const filteredRecordings = allRecordings.filter(rec => {
        const q = (filters.search || "").toLowerCase().trim();
        const matchesSearch = !q ||
            (rec.id && rec.id.toLowerCase().includes(q)) ||
            (rec.rawId && rec.rawId.toLowerCase().includes(q)) ||
            (rec.cajero && rec.cajero.toLowerCase().includes(q)) ||
            (rec.caja && rec.caja.toLowerCase().includes(q));

        let matchesDate = true;
        if (filters.date) {
            // filters.date comes from <input type="date"> as "YYYY-MM-DD"
            const expectedDate = filters.date.trim();
            // rec.fecha is formatted with getEcuadorDateString which is "YYYY-MM-DD"
            const recEcuadorDate = rec.fecha || (rec.fecha_hora_inicio ? getEcuadorDateString(rec.fecha_hora_inicio) : "");
            matchesDate = recEcuadorDate === expectedDate;
        }

        const matchesTime = filters.time ? (rec.hora && rec.hora.startsWith(filters.time)) : true;

        return matchesSearch && matchesDate && matchesTime;
    });

    // Sort from most recent to oldest
    const sortedRecordings = [...filteredRecordings].sort((a, b) => {
        return new Date(b.fecha_hora_inicio) - new Date(a.fecha_hora_inicio);
    });

    // Pagination Logic
    const indexOfLastItem = currentPage * itemsPerPage;
    const indexOfFirstItem = indexOfLastItem - itemsPerPage;
    const currentRecordings = sortedRecordings.slice(indexOfFirstItem, indexOfLastItem);
    const totalPages = Math.ceil(filteredRecordings.length / itemsPerPage);

    const paginate = (pageNumber) => setCurrentPage(pageNumber);

    // Contacts Pagination Logic
    const contactsPerPage = 7;
    const indexOfLastContact = contactsCurrentPage * contactsPerPage;
    const indexOfFirstContact = indexOfLastContact - contactsPerPage;
    const currentContacts = contacts.slice(indexOfFirstContact, indexOfLastContact);
    const totalContactPages = Math.ceil(contacts.length / contactsPerPage);

    const paginateContacts = (pageNumber) => setContactsCurrentPage(pageNumber);

    // Handle User Creation and Updates
    const handleCreateUser = async (e) => {
        e.preventDefault();

        if (!newUser.username || !newUser.nombre) {
            alert("Por favor complete todos los campos obligatorios");
            return;
        }

        try {
            if (isEditingUser) {
                // Update existing user
                if (newUser.password && newUser.password !== newUser.confirmPassword) {
                    alert("Las contraseñas no coinciden");
                    return;
                }

                // Find role ID
                const roleObj = roles.find(r => r.nombre.toLowerCase() === newUser.role.toLowerCase());
                const roleId = roleObj ? roleObj.id : null;

                const userData = {
                    username: newUser.username,
                    activo: newUser.estado === "activo",
                    rol_id: roleId,
                    // contacto_id: ... (Needs to be handled, maybe select existing contact or create one)
                    // For now assuming we are just updating basic info
                };

                if (newUser.password) userData.password = newUser.password;

                await updateUser(newUser.id, userData);

                // Update Contact Name and Role if changed
                const currentUser = users.find(u => u.id === newUser.id);
                if (currentUser && currentUser.contacto) {
                    const nameParts = (newUser.nombre || "").trim().split(" ");
                    const firstName = nameParts[0] || currentUser.contacto.nombre;
                    const lastName = nameParts.slice(1).join(" ") || currentUser.contacto.apellido;
                    const contactRole = newUser.role.toLowerCase() === "administrador" ? "Administrador" : "Cajero";

                    await updateContact(currentUser.contacto.id, {
                        nombre: firstName,
                        apellido: lastName,
                        rol: contactRole
                    });
                }

                // Refresh list
                const [updatedUsers, updatedContacts] = await Promise.all([getUsers(), getContacts()]);
                setUsers(updatedUsers);

                const processedContacts = updatedContacts.map(contact => {
                    const hasUser = updatedUsers.some(u => u.contacto_id === contact.id);
                    return { ...contact, hasUserAccount: hasUser };
                });
                setContacts(processedContacts);

                alert("Usuario actualizado exitosamente");
            } else {
                // Create new user
                if (!newUser.password) {
                    alert("La contraseña es obligatoria para nuevos usuarios");
                    return;
                }
                if (newUser.password !== newUser.confirmPassword) {
                    alert("Las contraseñas no coinciden");
                    return;
                }

                // Find role ID
                const roleObj = roles.find(r => r.nombre.toLowerCase() === newUser.role.toLowerCase());
                if (!roleObj) {
                    alert("Rol no válido");
                    return;
                }

                // We need a contact for the user. 
                // If not provided, we should probably create one implicitly or ask for it.
                // For this implementation, let's create a contact with the user's name first.
                const nameParts = newUser.nombre.trim().split(" ");
                const firstName = nameParts[0];
                const lastName = nameParts.slice(1).join(" ") || "."; // Ensure apellido is not empty if required
                const contactRole = newUser.role.toLowerCase() === "administrador" ? "Administrador" : "Cajero";

                const newContact = await createContact({
                    nombre: firstName,
                    apellido: lastName,
                    email: null,
                    telefono: null,
                    direccion: null,
                    rol: contactRole
                });

                const userData = {
                    username: newUser.username,
                    password: newUser.password,
                    rol_id: roleObj.id,
                    contacto_id: newContact.id,
                    activo: newUser.estado === "activo"
                };

                await createUser(userData);

                // Refresh list
                const [updatedUsers, updatedContacts] = await Promise.all([getUsers(), getContacts()]);
                setUsers(updatedUsers);

                const processedContacts = updatedContacts.map(contact => {
                    const hasUser = updatedUsers.some(u => u.contacto_id === contact.id);
                    return { ...contact, hasUserAccount: hasUser };
                });
                setContacts(processedContacts);

                alert(`Usuario ${newUser.username} creado exitosamente`);
            }

            setNewUser({
                id: null,
                username: "",
                password: "",
                confirmPassword: "",
                nombre: "",
                role: "cajero",
                cajaAsignada: "",
                estado: "activo"
            });
            setIsEditingUser(false);
            setShowUserModal(false);
        } catch (error) {
            console.error("Error saving user:", error);
            alert("Error al guardar usuario: " + (error.response?.data?.detail || error.message));
        }
    };

    const handleEditUser = (user) => {
        setNewUser({
            id: user.id,
            username: user.username,
            password: "", // Don't populate password
            confirmPassword: "",
            nombre: user.nombre || (user.contacto ? `${user.contacto.nombre} ${user.contacto.apellido}`.trim() : ""),
            role: user.rol?.nombre || "cajero",
            cajaAsignada: user.cajaAsignada || "",
            estado: user.activo ? "activo" : "inactivo"
        });
        setIsEditingUser(true);
        setShowUserModal(true);
    };

    const handleDeleteUser = async (id) => {
        const isConfirmed = await confirm({
            title: "¿Estás seguro?",
            message: "¿Está seguro de que desea eliminar este usuario?",
            confirmText: "Sí, eliminar",
            cancelText: "Cancelar"
        });
        if (isConfirmed) {
            try {
                await deleteUser(id);
                setUsers(users.filter(u => u.id !== id));
                await alert({ type: "success", message: "Usuario eliminado exitosamente" });
            } catch (error) {
                console.error("Error deleting user:", error);
                await alert({ type: "error", message: "Error al eliminar usuario" });
            }
        }
    };

    const handleOpenCreateUserFromContact = (contact) => {
        setCurrentContact(contact);
        setUserFromContactForm({
            username: "",
            password: "",
            confirmPassword: "",
            role: (contact.rol || "Cajero").toLowerCase(),
            cajaAsignada: ""
        });
        setShowCreateUserFromContactModal(true);
    };

    const handleCreateUserFromContact = async (e) => {
        e.preventDefault();

        if (!userFromContactForm.username || !userFromContactForm.password) {
            alert("Por favor complete todos los campos obligatorios");
            return;
        }

        if (userFromContactForm.password !== userFromContactForm.confirmPassword) {
            alert("Las contraseñas no coinciden");
            return;
        }

        try {
            // Find role ID
            const roleObj = roles.find(r => r.nombre.toLowerCase() === userFromContactForm.role.toLowerCase());
            if (!roleObj) {
                alert("Rol no válido");
                return;
            }

            const userData = {
                username: userFromContactForm.username,
                password: userFromContactForm.password,
                rol_id: roleObj.id,
                contacto_id: currentContact.id,
                activo: true
            };

            await createUser(userData);

            // Refresh users and contacts (to update hasUserAccount status if we were tracking it properly)
            const [updatedUsers, updatedContacts] = await Promise.all([getUsers(), getContacts()]);
            setUsers(updatedUsers);

            const processedContacts = updatedContacts.map(contact => {
                const hasUser = updatedUsers.some(u => u.contacto_id === contact.id);
                return { ...contact, hasUserAccount: hasUser };
            });
            setContacts(processedContacts);

            setUserFromContactForm({
                username: "",
                password: "",
                confirmPassword: "",
                role: "cajero",
                cajaAsignada: ""
            });
            setCurrentContact(null);
            setShowCreateUserFromContactModal(false);
            alert(`Usuario ${userData.username} creado exitosamente desde contacto`);

        } catch (error) {
            console.error("Error creating user from contact:", error);
            alert("Error al crear usuario: " + (error.response?.data?.detail || error.message));
        }
    };


    const handleCreateContact = async (e) => {
        e.preventDefault();
        try {
            if (currentContact) {
                const payload = { ...contactForm, sucursal_id: contactForm.sucursal_id || null };
                await updateContact(currentContact.id, payload);
                alert("Contacto actualizado exitosamente");
            } else {
                const payload = { ...contactForm, sucursal_id: contactForm.sucursal_id || null };
                await createContact(payload);
                alert("Contacto creado exitosamente");
            }
            const data = await getContacts();

            // Preserve hasUserAccount status
            const processedContacts = data.map(contact => {
                const hasUser = users.some(u => u.contacto_id === contact.id);
                return { ...contact, hasUserAccount: hasUser };
            });
            setContacts(processedContacts);
            setShowContactModal(false);
            setContactForm({
                nombre: "",
                apellido: "",
                email: "",
                telefono: "",
                direccion: ""
            });
            setCurrentContact(null);
        } catch (error) {
            console.error("Error saving contact:", error);
            alert("Error al guardar contacto: " + (error.response?.data?.detail || error.message));
        }
    };

    const handleEditContact = (contact) => {
        setCurrentContact(contact);
        setContactForm({
            nombre: contact.nombre,
            apellido: contact.apellido,
            email: contact.email || "",
            telefono: contact.telefono || "",
            direccion: contact.direccion || "",
            rol: contact.rol || "Cajero",
            sucursal_id: contact.sucursal_id || ""
        });
        setShowContactModal(true);
    };

    const openSucursalModal = (sucursal = null) => {
        if (sucursal) {
            setCurrentSucursal(sucursal);
            setSucursalForm({ nombre: sucursal.nombre, direccion: sucursal.direccion || "", activa: sucursal.activa });
        } else {
            setCurrentSucursal(null);
            setSucursalForm({ nombre: "", direccion: "", activa: true });
        }
        setShowSucursalModal(true);
    };

    const handleSaveSucursal = async (e) => {
        e.preventDefault();
        try {
            if (currentSucursal) {
                await updateSucursal(currentSucursal.id, sucursalForm);
                await alert({ type: "success", message: "Sucursal actualizada" });
            } else {
                await createSucursal(sucursalForm);
                await alert({ type: "success", message: "Sucursal creada" });
            }
            setShowSucursalModal(false);
            loadData(true);
        } catch (error) {
            await alert({ type: "error", message: error.message || "Error al guardar sucursal" });
        }
    };

    const handleDeleteSucursal = async (id) => {
        const isConfirmed = await confirm({
            title: "¿Estás seguro?",
            message: "Esta acción eliminará la sucursal permanentemente.",
            confirmText: "Eliminar",
            cancelText: "Cancelar"
        });
        if (isConfirmed) {
            try {
                await deleteSucursal(id);
                await alert({ type: "success", message: "Sucursal eliminada" });
                loadData(true);
            } catch (error) {
                await alert({ type: "error", message: "Error al eliminar sucursal" });
            }
        }
    };

    const handleDeleteContact = async (id) => {
    
        const isConfirmed = await confirm({
            title: "¿Estás seguro?",
            message: "¿Está seguro de que desea eliminar este contacto?",
            confirmText: "Sí, eliminar",
            cancelText: "Cancelar"
        });
        if (isConfirmed) {
            try {
                await deleteContact(id);
                setContacts(contacts.filter(c => c.id !== id));
                await alert({ type: "success", message: "Contacto eliminado exitosamente" });
            } catch (error) {
                console.error("Error deleting contact:", error);
                await alert({ type: "error", message: "Error al eliminar contacto" });
            }
        }
    };

    const renderContent = () => {
        switch (currentView) {
            case "panel":
                return (
                    <>
                        {/* Stats Cards */}
                        <div className="cards-grid">
                            <div className="card stat-card">
                                <div className="stat-icon bg-blue">📦</div>
                                <div className="stat-info">
                                    <h3>Cajas Operativas</h3>
                                    <p className="value">{boxConfigs.filter(b => b.estado_operativo === 'Operativa' || b.enabled).length} <span style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: '500' }}>/ {boxConfigs.length}</span></p>
                                </div>
                            </div>

                            <div className="card stat-card">
                                <div className="stat-icon bg-green">👥</div>
                                <div className="stat-info">
                                    <h3>Personal Cajeros</h3>
                                    <p className="value">{contacts.filter(c => c.rol?.toLowerCase() === 'cajero').length || users.filter(u => u.rol?.nombre?.toLowerCase() === 'cajero').length}</p>
                                </div>
                            </div>

                            <div className="card stat-card">
                                <div className="stat-icon bg-orange">🎙️</div>
                                <div className="stat-info">
                                    <h3>Grabaciones Procesadas</h3>
                                    <p className="value">{allRecordings.length}</p>
                                </div>
                            </div>
                        </div>

                        {/* Charts Section */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginBottom: '3rem' }}>
                            <SentimentPieChart recordings={allRecordings} />
                            <ActivityBarChart recordings={allRecordings} />
                        </div>


                    </>
                );

            case "analisis":
                return (
                    <>
                        {/* Toggle de Análisis */}
                        <div style={{ marginBottom: '2rem' }}>
                            <div className="toggle-container" style={{
                                display: 'flex',
                                background: '#f3f4f6',
                                borderRadius: '12px',
                                padding: '0.5rem',
                                maxWidth: '400px',
                                margin: '0 auto',
                                position: 'relative',
                                boxShadow: 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)'
                            }}>
                                <button
                                    onClick={() => setAnalisisViewMode('cajas')}
                                    style={{
                                        flex: 1,
                                        padding: '0.75rem 1.5rem',
                                        borderRadius: '8px',
                                        border: 'none',
                                        background: analisisViewMode === 'cajas' ? 'white' : 'transparent',
                                        color: analisisViewMode === 'cajas' ? '#3b82f6' : '#6b7280',
                                        fontWeight: analisisViewMode === 'cajas' ? '600' : '500',
                                        cursor: 'pointer',
                                        boxShadow: analisisViewMode === 'cajas' ? '0 4px 6px -1px rgba(0, 0, 0, 0.1)' : 'none',
                                        transition: 'all 0.3s ease',
                                        fontSize: '1rem',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem'
                                    }}
                                >
                                    📦 Cajas
                                </button>
                                <button
                                    onClick={() => setAnalisisViewMode('cajeros')}
                                    style={{
                                        flex: 1,
                                        padding: '0.75rem 1.5rem',
                                        borderRadius: '8px',
                                        border: 'none',
                                        background: analisisViewMode === 'cajeros' ? 'white' : 'transparent',
                                        color: analisisViewMode === 'cajeros' ? '#3b82f6' : '#6b7280',
                                        fontWeight: analisisViewMode === 'cajeros' ? '600' : '500',
                                        cursor: 'pointer',
                                        boxShadow: analisisViewMode === 'cajeros' ? '0 4px 6px -1px rgba(0, 0, 0, 0.1)' : 'none',
                                        transition: 'all 0.3s ease',
                                        fontSize: '1rem',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem'
                                    }}
                                >
                                    👥 Cajeros
                                </button>
                                <button
                                    onClick={() => setAnalisisViewMode('grabaciones')}
                                    style={{
                                        flex: 1,
                                        padding: '0.75rem 1.5rem',
                                        borderRadius: '8px',
                                        border: 'none',
                                        background: analisisViewMode === 'grabaciones' ? 'white' : 'transparent',
                                        color: analisisViewMode === 'grabaciones' ? '#3b82f6' : '#6b7280',
                                        fontWeight: analisisViewMode === 'grabaciones' ? '600' : '500',
                                        cursor: 'pointer',
                                        boxShadow: analisisViewMode === 'grabaciones' ? '0 4px 6px -1px rgba(0, 0, 0, 0.1)' : 'none',
                                        transition: 'all 0.3s ease',
                                        fontSize: '1rem',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem'
                                    }}
                                >
                                    🎤 Grabaciones
                                </button>
                            </div>
                        </div>

                        {/* Contenido dinámico según toggle */}
                        <div style={{
                            minHeight: '400px',
                            transition: 'opacity 0.3s ease-in-out',
                            opacity: 1
                        }}>
                            {analisisViewMode === 'grabaciones' ? (
                                <section className="card" style={{ animation: 'fadeIn 0.5s ease-out' }}>
                                    <div className="table-header">
                                        <h2>Grabaciones</h2>
                                    </div>
                                    <div style={{ padding: '2rem' }}>
                                        <div className="filters-bar" style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', flexWrap: 'wrap' }}>
                                            <div style={{ flex: 1, minWidth: '200px' }}>
                                                <input
                                                    type="text"
                                                    placeholder="Buscar por ID, Cajero, Caja..."
                                                    className="form-input"
                                                    style={{ width: '100%' }}
                                                    value={filters.search}
                                                    onChange={(e) => { setFilters({ ...filters, search: e.target.value }); setCurrentPage(1); }}
                                                />
                                            </div>
                                            <div>
                                                <input
                                                    type="date"
                                                    className="form-input"
                                                    value={filters.date}
                                                    onChange={(e) => { setFilters({ ...filters, date: e.target.value }); setCurrentPage(1); }}
                                                />
                                            </div>
                                            <div>
                                                <input
                                                    type="time"
                                                    className="form-input"
                                                    value={filters.time}
                                                    onChange={(e) => { setFilters({ ...filters, time: e.target.value }); setCurrentPage(1); }}
                                                />
                                            </div>
                                            <button
                                                className="btn"
                                                onClick={() => setFilters({ search: "", date: "", time: "" })}
                                                style={{ border: '1px solid var(--border-color)', background: 'white', cursor: 'pointer' }}
                                            >
                                                Limpiar
                                            </button>
                                        </div>

                                        <div className="recordings-list-container">
                                            <div className="recordings-list-header">
                                                <div className="col-cajero" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg> Cajero
                                                </div>
                                                <div className="col-caja" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><polyline points="3.27 6.96 12 12.01 20.73 6.96" /><line x1="12" y1="22.08" x2="12" y2="12" /></svg> Caja
                                                </div>
                                                <div className="col-fecha" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" /></svg> Fecha
                                                </div>
                                                <div className="col-hora" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg> Hora
                                                </div>
                                                <div className="col-duracion" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="10" y1="2" x2="14" y2="2" /><line x1="12" y1="14" x2="12" y2="10" /><circle cx="12" cy="14" r="8" /></svg> Duración
                                                </div>
                                                <div className="col-acciones" style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.5rem' }}>
                                                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" /></svg> Acciones
                                                </div>
                                            </div>
                                            <div className="recordings-list-body">
                                                {currentRecordings.map((rec) => (
                                                    <div key={rec.id} className="recording-row">
                                                        <div className="col-cajero">
                                                            <div className="cajero-info">
                                                                <div className="avatar small-avatar" style={{ background: '#eff6ff', color: '#2563eb', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>
                                                                </div>
                                                                <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{rec.cajero}</span>
                                                            </div>
                                                        </div>
                                                        <div className="col-caja">
                                                            <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f8fafc', color: '#64748b', borderRadius: '6px', padding: '0.35rem', border: '1px solid #e2e8f0' }}>
                                                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><polyline points="3.27 6.96 12 12.01 20.73 6.96" /><line x1="12" y1="22.08" x2="12" y2="12" /></svg>
                                                                </div>
                                                                {rec.caja}
                                                            </span>
                                                        </div>
                                                        <div className="col-fecha">
                                                            <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#0ea5e9', background: '#e0f2fe', borderRadius: '6px', padding: '0.35rem' }}>
                                                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" /></svg>
                                                                </div>
                                                                {rec.fecha}
                                                            </span>
                                                        </div>
                                                        <div className="col-hora">
                                                            <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#8b5cf6', background: '#ede9fe', borderRadius: '6px', padding: '0.35rem' }}>
                                                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>
                                                                </div>
                                                                {rec.hora}
                                                            </span>
                                                        </div>
                                                        <div className="col-duracion">
                                                            <div style={{
                                                                fontSize: '0.9rem', padding: '0.4rem 0.75rem',
                                                                display: 'inline-flex', alignItems: 'center', gap: '0.4rem',
                                                                borderRadius: '8px', border: '1px solid #fed7aa',
                                                                backgroundColor: '#ffedd5', color: '#ea580c', fontWeight: '500'
                                                            }}>
                                                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="10" y1="2" x2="14" y2="2" /><line x1="12" y1="14" x2="12" y2="10" /><circle cx="12" cy="14" r="8" /></svg>
                                                                {rec.duracion_segundos > 0 ? `${Math.round(rec.duracion_segundos)} seg` : (rec.duracion || "00:00")}
                                                            </div>
                                                        </div>
                                                        <div className="col-acciones">
                                                            <button
                                                                className="btn-action-outline"
                                                                title="Ver Transcripción"
                                                                onClick={() => setSelectedRecording(rec)}
                                                            >
                                                                <span className="icon" style={{ display: 'flex', alignItems: 'center' }}><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg></span> Transcripción
                                                            </button>
                                                        </div>
                                                    </div>
                                                ))}
                                                {currentRecordings.length === 0 && (
                                                    <div className="empty-state">
                                                        No se encontraron grabaciones con los filtros seleccionados.
                                                    </div>
                                                )}
                                            </div>
                                        </div>

                                        {totalPages > 1 && (
                                            <div className="pagination" style={{ display: 'flex', justifyContent: 'center', gap: '0.5rem', marginTop: '2rem' }}>
                                                <button
                                                    disabled={currentPage === 1}
                                                    onClick={() => paginate(currentPage - 1)}
                                                    className="btn"
                                                    style={{ padding: '0.5rem 1rem', border: '1px solid var(--border-color)', background: 'white', cursor: 'pointer' }}
                                                >
                                                    Anterior
                                                </button>
                                                <span style={{ display: 'flex', alignItems: 'center', padding: '0 1rem' }}>
                                                    Página {currentPage} de {totalPages}
                                                </span>
                                                <button
                                                    disabled={currentPage === totalPages}
                                                    onClick={() => paginate(currentPage + 1)}
                                                    className="btn"
                                                    style={{ padding: '0.5rem 1rem', border: '1px solid var(--border-color)', background: 'white', cursor: 'pointer' }}
                                                >
                                                    Siguiente
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                </section>
                            ) : analisisViewMode === 'cajas' ? (
                                <section className="card" style={{ animation: 'fadeIn 0.5s ease-out' }}>
                                    <div className="table-header">
                                        <h2>Análisis de Cajas</h2>
                                        <p className="subtitle" style={{ fontSize: '0.9rem', marginTop: '0.5rem' }}>
                                            Supervisión detallada de productividad y métricas por punto de venta
                                        </p>
                                    </div>
                                    <div style={{ padding: '2rem' }}>
                                        <div className="recordings-list-container" style={{ border: '1px solid #e2e8f0', borderRadius: '12px', overflow: 'hidden', background: 'white' }}>
                                            <div className="recordings-list-header" style={{ display: 'grid', gridTemplateColumns: 'minmax(200px, 2fr) minmax(180px, 1.5fr) minmax(200px, 2fr) 150px', gap: '1rem', padding: '1rem 1.5rem', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#64748b', fontWeight: '600', fontSize: '0.9rem' }}>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><polyline points="3.27 6.96 12 12.01 20.73 6.96" /><line x1="12" y1="22.08" x2="12" y2="12" /></svg>
                                                    Caja
                                                </div>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                                                    Estado
                                                </div>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>
                                                    Cajero Asignado
                                                </div>
                                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.5rem' }}>
                                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" /></svg>
                                                    Acciones
                                                </div>
                                            </div>
                                            <div className="recordings-list-body" style={{ display: 'flex', flexDirection: 'column' }}>
                                                {boxConfigs.map((box) => {
                                                    const isOnline = box.ultima_conexion && (new Date() - new Date(box.ultima_conexion)) < 120000 && box.version_actual === "v2.0.0";
                                                    return (
                                                    <div key={box.id} className="recording-row hover-row" style={{ display: 'grid', gridTemplateColumns: 'minmax(200px, 2fr) minmax(180px, 1.5fr) minmax(200px, 2fr) 150px', gap: '1rem', padding: '1rem 1.5rem', borderBottom: '1px solid #f1f5f9', alignItems: 'center', transition: 'background-color 0.2s', backgroundColor: 'inherit' }}>
                                                        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                                            <div style={{ position: 'relative', width: '40px', height: '40px', borderRadius: '10px', background: isOnline ? '#fff7ed' : '#f8fafc', border: `1px solid ${isOnline ? '#fed7aa' : '#e2e8f0'}`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: isOnline ? '#ea580c' : '#64748b' }}>
                                                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><polyline points="3.27 6.96 12 12.01 20.73 6.96" /><line x1="12" y1="22.08" x2="12" y2="12" /></svg>
                                                                {isOnline && (
                                                                    <span style={{ position: 'absolute', top: '-4px', right: '-4px', width: '12px', height: '12px', background: '#ea580c', borderRadius: '50%', border: '2px solid white', animation: 'pulse 2s infinite' }}></span>
                                                                )}
                                                            </div>
                                                            <div style={{ display: 'flex', flexDirection: 'column' }}>
                                                                <span className="font-medium" style={{ fontSize: '1.05rem', color: '#1e293b' }}>{box.name}</span>
                                                                <span style={{ fontSize: '0.75rem', color: isOnline ? '#ea580c' : '#94a3b8', fontWeight: '600' }}>
                                                                    {isOnline ? 'Transmisión Activa' : 'Fuera de Línea'}
                                                                </span>
                                                            </div>
                                                        </div>
                                                        <div>
                                                            <span style={{ display: 'inline-block', padding: '0.3rem 0.6rem', borderRadius: '4px', fontSize: '0.85rem', fontWeight: '500', backgroundColor: box.estado_operativo === 'Operativa' ? '#e0f2fe' : box.estado_operativo === 'Mantenimiento' ? '#fef08a' : '#fee2e2', color: box.estado_operativo === 'Operativa' ? '#0369a1' : box.estado_operativo === 'Mantenimiento' ? '#854d0e' : '#991b1b' }}>
                                                                {box.estado_operativo || 'Operativa'}
                                                            </span>
                                                            {box.motivo_estado && (
                                                                <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.2rem', maxWidth: '180px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={box.motivo_estado}>
                                                                    {box.motivo_estado}
                                                                </div>
                                                            )}
                                                        </div>
                                                        <div>
                                                            {box.assignedContactId ? (
                                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                                                    <div className="avatar small-avatar" style={{ background: '#eff6ff', color: '#2563eb', display: 'flex', alignItems: 'center', justifyContent: 'center', width: '32px', height: '32px' }}>
                                                                        {(contacts.find(c => c.id === box.assignedContactId)?.nombre?.charAt(0) || "U").toUpperCase()}
                                                                    </div>
                                                                    <span style={{ color: '#334155', fontWeight: '500' }}>
                                                                        {contacts.find(c => c.id === box.assignedContactId)?.nombre || "Desconocido"} {contacts.find(c => c.id === box.assignedContactId)?.apellido || ""}
                                                                    </span>
                                                                </div>
                                                            ) : (
                                                                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', color: '#94a3b8', fontStyle: 'italic', fontSize: '0.9rem', background: '#f8fafc', padding: '0.3rem 0.6rem', borderRadius: '6px', border: '1px dashed #cbd5e1' }}>
                                                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><line x1="4.93" y1="4.93" x2="19.07" y2="19.07" /></svg>
                                                                    Sin asignar
                                                                </span>
                                                            )}
                                                        </div>
                                                        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                                                            <button
                                                                className="btn-action-primary"
                                                                style={{ padding: '0.5rem 1rem', fontSize: '0.9rem', background: 'linear-gradient(135deg, #fb923c 0%, #f97316 100%)', border: 'none', color: 'white', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem', boxShadow: '0 4px 6px -1px rgba(249, 115, 22, 0.2)', transition: 'transform 0.2s, box-shadow 0.2s', fontWeight: '600' }}
                                                                onClick={() => setSelectedBoxForDetail(box)}
                                                                onMouseOver={(e) => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 6px 8px -1px rgba(249, 115, 22, 0.3)'; }}
                                                                onMouseOut={(e) => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = '0 4px 6px -1px rgba(249, 115, 22, 0.2)'; }}
                                                            >
                                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="6" y1="20" x2="6" y2="14" /></svg>
                                                                Análisis
                                                            </button>
                                                        </div>
                                                    </div>
                                                );
                                                })}
                                                {boxConfigs.length === 0 && (
                                                    <div className="empty-state" style={{ padding: '3rem', textAlign: 'center', color: '#64748b' }}>
                                                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto 1rem auto' }}><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><polyline points="3.27 6.96 12 12.01 20.73 6.96" /><line x1="12" y1="22.08" x2="12" y2="12" /></svg>
                                                        <p>No hay cajas configuradas para analizar.</p>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </section>
                            ) : (
                                <div style={{ animation: 'fadeIn 0.5s ease-out' }}>
                                    {selectedCashierForAtenciones ? (
                                        <CashierAtencionesModal
                                            cashier={selectedCashierForAtenciones}
                                            onClose={() => setSelectedCashierForAtenciones(null)}
                                            inline={true}
                                        />
                                    ) : (
                                        <CashierList
                                            contacts={contacts}
                                            users={users}
                                            boxes={boxConfigs}
                                            recordings={allRecordings}
                                            onViewAtenciones={setSelectedCashierForAtenciones}
                                        />
                                    )}
                                </div>
                            )}
                        </div>
                    </>
                );

            case "configuracion":
                return (
                    <>
                        <div style={{
                            minHeight: '400px',
                            transition: 'opacity 0.3s ease-in-out',
                            opacity: 1
                        }}>

                            <section className="card" style={{ animation: 'fadeIn 0.5s ease-out' }}>
                                <div className="table-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <h2>Gestión de Cajas</h2>
                                    <button
                                        className="btn btn-primary"
                                        onClick={() => openBoxModal()}
                                        style={{ padding: '0.65rem 1.25rem', cursor: 'pointer', border: 'none', background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)', color: 'white', borderRadius: '10px', fontWeight: '700', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.5rem', boxShadow: '0 4px 12px rgba(249, 115, 22, 0.35)', transition: 'all 0.2s' }}
                                        onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = '0 6px 16px rgba(249, 115, 22, 0.45)'; }}
                                        onMouseLeave={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = '0 4px 12px rgba(249, 115, 22, 0.35)'; }}
                                    >
                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
                                        Agregar Caja
                                    </button>
                                </div>
                                <div style={{ padding: '2rem' }}>
                                    <div className="recordings-list-container" style={{ border: '1px solid #e2e8f0', borderRadius: '12px', overflow: 'hidden', background: 'white' }}>
                                        <div className="recordings-list-header" style={{ display: 'grid', gridTemplateColumns: 'minmax(180px, 1.5fr) minmax(150px, 1fr) minmax(180px, 1.5fr) 140px 120px', gap: '1rem', padding: '1rem 1.5rem', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#64748b', fontWeight: '600', fontSize: '0.9rem' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><polyline points="3.27 6.96 12 12.01 20.73 6.96" /><line x1="12" y1="22.08" x2="12" y2="12" /></svg>
                                                Caja
                                            </div>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
                                                Estado
                                            </div>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>
                                                Cajero Asignado
                                            </div>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/></svg>
                                                Grabación
                                            </div>
                                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" /></svg>
                                                Acciones
                                            </div>
                                        </div>
                                        <div className="recordings-list-body" style={{ display: 'flex', flexDirection: 'column' }}>
                                            {boxConfigs.map((box) => {
                                                const isOnline = box.ultima_conexion && (new Date() - new Date(box.ultima_conexion)) < 120000 && box.version_actual === "v2.0.0";
                                                const currentEstado = box.estado_operativo || 'Operativa';
                                                const isRecording = currentEstado === "Operativa" ? (box.en_uso || false) : false;
                                                return (
                                                <div key={box.id} className="recording-row hover-row" style={{ display: 'grid', gridTemplateColumns: 'minmax(180px, 1.5fr) minmax(150px, 1fr) minmax(180px, 1.5fr) 140px 120px', gap: '1rem', padding: '1rem 1.5rem', borderBottom: '1px solid #f1f5f9', alignItems: 'center', transition: 'background-color 0.2s', backgroundColor: 'inherit' }}>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                                        <div style={{ position: 'relative', width: '40px', height: '40px', borderRadius: '10px', background: isRecording ? '#ecfdf5' : isOnline ? '#fff7ed' : '#f8fafc', border: `1px solid ${isRecording ? '#a7f3d0' : isOnline ? '#fed7aa' : '#e2e8f0'}`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: isRecording ? '#10b981' : isOnline ? '#ea580c' : '#94a3b8' }}>
                                                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><polyline points="3.27 6.96 12 12.01 20.73 6.96" /><line x1="12" y1="22.08" x2="12" y2="12" /></svg>
                                                            {(isOnline || isRecording) && (
                                                                <span style={{ position: 'absolute', top: '-4px', right: '-4px', width: '12px', height: '12px', background: isRecording ? '#10b981' : '#ea580c', borderRadius: '50%', border: '2px solid white', animation: 'pulse 2s infinite' }}></span>
                                                            )}
                                                        </div>
                                                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                                <span className="font-medium" style={{ fontSize: '1.05rem', color: '#1e293b' }}>{box.name}</span>
                                                                {box.version_actual && (
                                                                    <span style={{ fontSize: '0.65rem', padding: '0.1rem 0.4rem', borderRadius: '4px', background: '#e2e8f0', color: '#475569', fontWeight: 'bold' }}>
                                                                        {box.version_actual}
                                                                    </span>
                                                                )}
                                                            </div>
                                                            <span style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.2rem' }}>{sucursales.find(s => s.id === box.sucursal_id)?.nombre || box.description || "Sin sucursal asignada"}</span>
                                                            <span style={{ fontSize: '0.75rem', color: (isOnline && isRecording) ? '#10b981' : isOnline ? '#ea580c' : '#94a3b8', fontWeight: '600' }}>
                                                                {isOnline 
                                                                    ? (isRecording 
                                                                        ? (box.assignedContactId ? 'Grabando / Transcribiendo' : 'Grabando / No Transcribiendo') 
                                                                        : (box.estado_grabacion === 'pausa' ? 'En Pausa' : 'Transmisión Activa')) 
                                                                    : 'Fuera de Línea'}
                                                            </span>
                                                        </div>
                                                    </div>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={currentEstado === 'Operativa' ? '#16a34a' : '#ef4444'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                            {currentEstado === 'Operativa' ? (
                                                                <>
                                                                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                                                                    <polyline points="22 4 12 14.01 9 11.01" />
                                                                </>
                                                            ) : (
                                                                <>
                                                                    <circle cx="12" cy="12" r="10" />
                                                                    <line x1="12" y1="8" x2="12" y2="12" />
                                                                    <line x1="12" y1="16" x2="12.01" y2="16" />
                                                                </>
                                                            )}
                                                        </svg>
                                                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                                                            <span style={{ fontSize: '0.9rem', fontWeight: '600', color: currentEstado === 'Operativa' ? '#16a34a' : '#ef4444' }}>
                                                                {currentEstado}
                                                            </span>
                                                            {box.motivo_estado && (
                                                                <span style={{ fontSize: '0.75rem', color: '#64748b', maxWidth: '150px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={box.motivo_estado}>
                                                                    {box.motivo_estado}
                                                                </span>
                                                            )}
                                                        </div>
                                                    </div>
                                                    <div>
                                                        {box.assignedContactId ? (
                                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                                                <div className="avatar small-avatar" style={{ background: '#f0fdf4', color: '#16a34a', display: 'flex', alignItems: 'center', justifyContent: 'center', width: '32px', height: '32px' }}>
                                                                    {(contacts.find(c => c.id === box.assignedContactId)?.nombre?.charAt(0) || "U").toUpperCase()}
                                                                </div>
                                                                <span style={{ color: '#334155', fontWeight: '500' }}>
                                                                    {contacts.find(c => c.id === box.assignedContactId)?.nombre || "Desconocido"} {contacts.find(c => c.id === box.assignedContactId)?.apellido || ""}
                                                                </span>
                                                            </div>
                                                        ) : (
                                                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', color: '#94a3b8', fontStyle: 'italic', fontSize: '0.9rem', background: '#f8fafc', padding: '0.3rem 0.6rem', borderRadius: '6px', border: '1px dashed #cbd5e1' }}>
                                                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><line x1="4.93" y1="4.93" x2="19.07" y2="19.07" /></svg>
                                                                Sin asignar
                                                            </span>
                                                        )}
                                                    </div>
                                                    <div>
                                                        {(() => {
                                                            const grabacionEstado = isOnline ? (box.estado_grabacion || (isRecording ? 'grabando' : 'apagado')) : 'apagado';
                                                            
                                                            let pillColor = '#991b1b';
                                                            let pillBg = '#fee2e2';
                                                            let dotColor = '#ef4444';
                                                            let statusText = 'Inactiva';
                                                            let showPulse = false;

                                                            if (grabacionEstado === 'grabando') {
                                                                pillColor = '#166534';
                                                                pillBg = '#dcfce7';
                                                                dotColor = '#22c55e';
                                                                statusText = 'Grabando / Transcribiendo';
                                                                showPulse = true;
                                                            } else if (grabacionEstado === 'pausa' || grabacionEstado === 'en_pausa') {
                                                                pillColor = '#9a3412';
                                                                pillBg = '#ffedd5';
                                                                dotColor = '#f97316';
                                                                statusText = 'En Pausa';
                                                                showPulse = true;
                                                            } else if (grabacionEstado === 'fuera de horario' || grabacionEstado === 'fuera_horario') {
                                                                pillColor = '#475569';
                                                                pillBg = '#f1f5f9';
                                                                dotColor = '#64748b';
                                                                statusText = 'Fuera de Horario';
                                                            } else if (grabacionEstado === 'transmitiendo') {
                                                                pillColor = '#1e40af';
                                                                pillBg = '#dbeafe';
                                                                dotColor = '#3b82f6';
                                                                statusText = 'Transmitiendo';
                                                                showPulse = true;
                                                            } else {
                                                                pillColor = '#991b1b';
                                                                pillBg = '#fee2e2';
                                                                dotColor = '#ef4444';
                                                                statusText = 'Apagada';
                                                            }

                                                            return (
                                                                <span style={{ 
                                                                    display: 'inline-flex', 
                                                                    alignItems: 'center', 
                                                                    gap: '0.4rem', 
                                                                    color: pillColor, 
                                                                    fontSize: '0.85rem', 
                                                                    background: pillBg, 
                                                                    padding: '0.3rem 0.6rem', 
                                                                    borderRadius: '6px', 
                                                                    fontWeight: '600' 
                                                                }}>
                                                                    <div style={{ 
                                                                        width: '8px', 
                                                                        height: '8px', 
                                                                        borderRadius: '50%', 
                                                                        background: dotColor, 
                                                                        animation: showPulse ? 'pulse 2s infinite' : 'none' 
                                                                    }}></div>
                                                                    {statusText}
                                                                </span>
                                                            );
                                                        })()}
                                                    </div>
                                                    <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                                                        <button
                                                            onClick={() => openBoxModal(box)}
                                                            title="Editar"
                                                            style={{ padding: '0.5rem', border: '1px solid #e2e8f0', background: 'white', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.2s', color: '#64748b' }}
                                                            onMouseEnter={e => { e.currentTarget.style.background = '#f8fafc'; e.currentTarget.style.color = '#3b82f6'; e.currentTarget.style.borderColor = '#cbd5e1'; }}
                                                            onMouseLeave={e => { e.currentTarget.style.background = 'white'; e.currentTarget.style.color = '#64748b'; e.currentTarget.style.borderColor = '#e2e8f0'; }}
                                                        >
                                                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
                                                        </button>
                                                        <button
                                                            onClick={() => handleDeleteBox(box.id)}
                                                            title="Eliminar"
                                                            style={{ padding: '0.5rem', border: '1px solid #fee2e2', background: '#fff1f2', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.2s', color: '#ef4444' }}
                                                            onMouseEnter={e => { e.currentTarget.style.background = '#fee2e2'; e.currentTarget.style.color = '#dc2626'; }}
                                                            onMouseLeave={e => { e.currentTarget.style.background = '#fff1f2'; e.currentTarget.style.color = '#ef4444'; }}
                                                        >
                                                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /><line x1="10" y1="11" x2="10" y2="17" /><line x1="14" y1="11" x2="14" y2="17" /></svg>
                                                        </button>
                                                    </div>
                                                </div>
                                                );
                                            })}
                                            {boxConfigs.length === 0 && (
                                                <div className="empty-state" style={{ padding: '3rem', textAlign: 'center', color: '#64748b' }}>
                                                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto 1rem auto' }}><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><polyline points="3.27 6.96 12 12.01 20.73 6.96" /><line x1="12" y1="22.08" x2="12" y2="12" /></svg>
                                                    <p>No hay cajas configuradas.</p>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </section>
                        </div>

                        <style>{`
                            @keyframes fadeIn {
                                from { opacity: 0; transform: translateY(10px); }
                                to { opacity: 1; transform: translateY(0); }
                            }
                        `}</style>
                    </>
                );

            case "personal":
                return (
                    <>
                        {/* Toggle de Personal */}
                        <div style={{ marginBottom: '2rem' }}>
                            <div className="toggle-container" style={{
                                display: 'flex',
                                background: '#f3f4f6',
                                borderRadius: '12px',
                                padding: '0.5rem',
                                maxWidth: '400px',
                                margin: '0 auto',
                                position: 'relative',
                                boxShadow: 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)'
                            }}>
                                <button
                                    onClick={() => setPersonalViewMode('contactos')}
                                    style={{
                                        flex: 1, padding: '0.75rem 1.5rem', borderRadius: '8px', border: 'none',
                                        background: personalViewMode === 'contactos' ? 'white' : 'transparent',
                                        color: personalViewMode === 'contactos' ? '#ea580c' : '#6b7280',
                                        fontWeight: personalViewMode === 'contactos' ? '600' : '500',
                                        cursor: 'pointer',
                                        boxShadow: personalViewMode === 'contactos' ? '0 4px 6px -1px rgba(0, 0, 0, 0.1)' : 'none',
                                        transition: 'all 0.3s ease', fontSize: '1rem',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem'
                                    }}
                                >
                                    📒 Contactos
                                </button>
                                                                <button
                                    onClick={() => setPersonalViewMode('usuarios')}
                                    style={{
                                        flex: 1, padding: '0.75rem 1.5rem', borderRadius: '8px', border: 'none',
                                        background: personalViewMode === 'usuarios' ? 'white' : 'transparent',
                                        color: personalViewMode === 'usuarios' ? '#ea580c' : '#6b7280',
                                        fontWeight: personalViewMode === 'usuarios' ? '600' : '500',
                                        cursor: 'pointer',
                                        boxShadow: personalViewMode === 'usuarios' ? '0 4px 6px -1px rgba(0, 0, 0, 0.1)' : 'none',
                                        transition: 'all 0.3s ease', fontSize: '1rem',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem'
                                    }}
                                >
                                    👥 Usuarios
                                </button>
                                <button
                                    onClick={() => setPersonalViewMode('sucursales')}
                                    style={{
                                        flex: 1, padding: '0.75rem 1.5rem', borderRadius: '8px', border: 'none',
                                        background: personalViewMode === 'sucursales' ? 'white' : 'transparent',
                                        color: personalViewMode === 'sucursales' ? '#ea580c' : '#6b7280',
                                        fontWeight: personalViewMode === 'sucursales' ? '600' : '500',
                                        cursor: 'pointer',
                                        boxShadow: personalViewMode === 'sucursales' ? '0 4px 6px -1px rgba(0, 0, 0, 0.1)' : 'none',
                                        transition: 'all 0.3s ease', fontSize: '1rem',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem'
                                    }}
                                >
                                    🏢 Sucursales
                                </button>
                            </div>
                        </div>

                        {/* Contenido dinámico según toggle */}
                        <div style={{ minHeight: '400px', transition: 'opacity 0.3s ease-in-out', opacity: 1 }}>
                            {personalViewMode === 'contactos' ? (
                                <div style={{ animation: 'fadeIn 0.4s ease-out' }}>
                                    {/* Header Contactos */}
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
                                        <div>
                                            <h2 style={{ fontSize: '1.4rem', fontWeight: '800', color: '#0f172a', margin: '0 0 0.25rem 0', letterSpacing: '-0.02em' }}>Contactos</h2>
                                            <p style={{ margin: 0, fontSize: '0.875rem', color: '#64748b' }}>
                                                <span style={{ fontWeight: '700', color: '#ea580c' }}>{contacts.length}</span> contactos registrados
                                            </p>
                                        </div>
                                        <button
                                            onClick={() => { setContactForm({ nombre: "", apellido: "", email: "", telefono: "", direccion: "", rol: "Cajero", sucursal_id: "" }); setCurrentContact(null); setShowContactModal(true); }}
                                            style={{
                                                padding: '0.65rem 1.25rem', cursor: 'pointer', border: 'none',
                                                background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
                                                color: 'white', borderRadius: '10px', fontWeight: '700', fontSize: '0.9rem',
                                                display: 'flex', alignItems: 'center', gap: '0.5rem',
                                                boxShadow: '0 4px 12px rgba(249,115,22,0.35)', transition: 'all 0.2s'
                                            }}
                                            onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = '0 6px 16px rgba(249,115,22,0.45)'; }}
                                            onMouseLeave={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = '0 4px 12px rgba(249,115,22,0.35)'; }}
                                        >
                                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
                                            Nuevo Contacto
                                        </button>
                                    </div>

                                    {/* Lista Contactos */}
                                    <div className="recordings-list-container" style={{ border: '1px solid #e2e8f0', borderRadius: '12px', overflow: 'hidden', background: 'white' }}>
                                        <div className="recordings-list-header" style={{ display: 'grid', gridTemplateColumns: 'minmax(250px, 2fr) minmax(200px, 1.5fr) minmax(150px, 1fr) 200px', gap: '1rem', padding: '1rem 1.5rem', background: '#fff7ed', borderBottom: '1px solid #fed7aa', color: '#c2410c', fontWeight: '600', fontSize: '0.9rem' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>
                                                Contacto
                                            </div>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" /><polyline points="22,6 12,13 2,6" /></svg>
                                                Email y Teléfono
                                            </div>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" /><circle cx="12" cy="10" r="3" /></svg>
                                                Dirección
                                            </div>
                                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.5rem' }}>
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" /></svg>
                                                Acciones
                                            </div>
                                        </div>
                                        <div className="recordings-list-body" style={{ display: 'flex', flexDirection: 'column' }}>
                                            {currentContacts.map((contact) => (
                                                <div key={contact.id} className="recording-row hover-row" style={{ display: 'grid', gridTemplateColumns: 'minmax(250px, 2fr) minmax(200px, 1.5fr) minmax(150px, 1fr) 200px', gap: '1rem', padding: '1rem 1.5rem', borderBottom: '1px solid #f1f5f9', alignItems: 'center', transition: 'background-color 0.2s', backgroundColor: 'inherit' }}>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                                        <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: 'linear-gradient(135deg, #f97316, #fb923c)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: '800', fontSize: '1.1rem', flexShrink: 0, boxShadow: '0 4px 10px rgba(249,115,22,0.3)' }}>
                                                            {contact.nombre.charAt(0).toUpperCase()}
                                                        </div>
                                                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                                <span className="font-medium" style={{ fontSize: '1rem', color: '#0f172a', fontWeight: '700' }}>
                                                                    {contact.nombre} {contact.apellido}
                                                                </span>
                                                                {contact.hasUserAccount && <span title="Tiene cuenta de usuario" style={{ fontSize: '0.85rem' }}>👤</span>}
                                                            </div>
                                                            <div style={{ display: 'flex', gap: '0.4rem', marginTop: '0.2rem' }}>
                                                                <span style={{ fontSize: '0.75rem', padding: '0.15rem 0.6rem', borderRadius: '999px', background: '#dcfce7', color: '#15803d', fontWeight: '600', border: '1px solid #bbf7d0', alignSelf: 'flex-start' }}>● Activo</span>
                                                                {contact.rol && (
                                                                    <span style={{ 
                                                                        fontSize: '0.75rem', 
                                                                        padding: '0.15rem 0.6rem', 
                                                                        borderRadius: '999px', 
                                                                        background: contact.rol.toLowerCase() === 'administrador' ? '#f5f3ff' : '#f0f9ff', 
                                                                        color: contact.rol.toLowerCase() === 'administrador' ? '#6d28d9' : '#0369a1', 
                                                                        fontWeight: '600', 
                                                                        border: contact.rol.toLowerCase() === 'administrador' ? '1px solid #ddd6fe' : '1px solid #bae6fd', 
                                                                        alignSelf: 'flex-start' 
                                                                    }}>{contact.rol}</span>
                                                                )}
                                                            </div>
                                                        </div>
                                                    </div>
                                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                                                        <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: contact.email ? '#475569' : '#94a3b8', fontSize: '0.85rem', fontStyle: contact.email ? 'normal' : 'italic', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" /><polyline points="22,6 12,13 2,6" /></svg>
                                                            {contact.email || "Sin email"}
                                                        </span>
                                                        <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: contact.telefono ? '#475569' : '#94a3b8', fontSize: '0.85rem', fontStyle: contact.telefono ? 'normal' : 'italic', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" /></svg>
                                                            {contact.telefono || "Sin teléfono"}
                                                        </span>
                                                    </div>
                                                    <div>
                                                        <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: contact.direccion ? '#475569' : '#94a3b8', fontSize: '0.85rem', fontStyle: contact.direccion ? 'normal' : 'italic', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', background: '#f8fafc', padding: '0.3rem 0.6rem', borderRadius: '6px', border: '1px solid #f1f5f9' }}>
                                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" /><circle cx="12" cy="10" r="3" /></svg>
                                                            {contact.direccion || "Sin dirección"}
                                                        </span>
                                                    </div>
                                                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                                                        <button
                                                            onClick={() => handleEditContact(contact)}
                                                            title="Editar"
                                                            style={{ padding: '0.4rem 0.6rem', border: '1px solid #e2e8f0', background: 'white', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.3rem', transition: 'all 0.2s', color: '#475569', fontSize: '0.8rem', fontWeight: '600' }}
                                                            onMouseEnter={e => { e.currentTarget.style.background = '#fff7ed'; e.currentTarget.style.borderColor = '#f97316'; e.currentTarget.style.color = '#ea580c'; }}
                                                            onMouseLeave={e => { e.currentTarget.style.background = 'white'; e.currentTarget.style.borderColor = '#e2e8f0'; e.currentTarget.style.color = '#475569'; }}
                                                        >
                                                            ✏️ Editar
                                                        </button>
                                                        {!contact.hasUserAccount && (
                                                            <button
                                                                onClick={() => handleOpenCreateUserFromContact(contact)}
                                                                title="Crear Usuario"
                                                                style={{ padding: '0.4rem 0.6rem', border: '1px solid #fed7aa', background: '#fff7ed', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.3rem', transition: 'all 0.2s', color: '#c2410c', fontSize: '0.8rem', fontWeight: '600' }}
                                                                onMouseEnter={e => { e.currentTarget.style.background = '#ffedd5'; }}
                                                                onMouseLeave={e => { e.currentTarget.style.background = '#fff7ed'; }}
                                                            >
                                                                👤➕
                                                            </button>
                                                        )}
                                                        <button
                                                            onClick={() => handleDeleteContact(contact.id)}
                                                            title="Eliminar"
                                                            style={{ padding: '0.4rem 0.6rem', border: '1px solid #fee2e2', background: '#fff1f2', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.2s', color: '#dc2626' }}
                                                            onMouseEnter={e => { e.currentTarget.style.background = '#fee2e2'; }}
                                                            onMouseLeave={e => { e.currentTarget.style.background = '#fff1f2'; }}
                                                        >
                                                            🗑️
                                                        </button>
                                                    </div>
                                                </div>
                                            ))}
                                            {currentContacts.length === 0 && (
                                                <div style={{ textAlign: 'center', padding: '4rem 2rem', color: '#94a3b8', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', borderRadius: '0 0 12px 12px' }}>
                                                    <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📒</div>
                                                    <p style={{ fontWeight: '600', fontSize: '1rem', margin: '0 0 0.5rem 0' }}>No hay contactos registrados</p>
                                                    <p style={{ fontSize: '0.875rem', margin: 0 }}>Agrega un nuevo contacto para comenzar</p>
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    {/* Pagination */}
                                    {totalContactPages > 1 && (
                                        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem', marginTop: '2rem' }}>
                                            <button
                                                disabled={contactsCurrentPage === 1}
                                                onClick={() => paginateContacts(contactsCurrentPage - 1)}
                                                style={{ padding: '0.5rem 1rem', border: '1px solid #e2e8f0', background: contactsCurrentPage === 1 ? '#f8fafc' : 'white', borderRadius: '8px', cursor: contactsCurrentPage === 1 ? 'not-allowed' : 'pointer', color: contactsCurrentPage === 1 ? '#cbd5e1' : '#475569', fontWeight: '500', fontSize: '0.875rem' }}
                                            >← Anterior</button>
                                            <span style={{ padding: '0.5rem 1rem', background: '#fff7ed', borderRadius: '8px', color: '#c2410c', fontWeight: '700', fontSize: '0.875rem', border: '1px solid #fed7aa' }}>
                                                {contactsCurrentPage} / {totalContactPages}
                                            </span>
                                            <button
                                                disabled={contactsCurrentPage === totalContactPages}
                                                onClick={() => paginateContacts(contactsCurrentPage + 1)}
                                                style={{ padding: '0.5rem 1rem', border: '1px solid #e2e8f0', background: contactsCurrentPage === totalContactPages ? '#f8fafc' : 'white', borderRadius: '8px', cursor: contactsCurrentPage === totalContactPages ? 'not-allowed' : 'pointer', color: contactsCurrentPage === totalContactPages ? '#cbd5e1' : '#475569', fontWeight: '500', fontSize: '0.875rem' }}
                                            >Siguiente →</button>
                                        </div>
                                    )}
                                </div>
                            ) : personalViewMode === 'usuarios' ? (
                                <div style={{ animation: 'fadeIn 0.4s ease-out' }}>
                                    {/* Header Usuarios */}
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
                                        <div>
                                            <h2 style={{ fontSize: '1.4rem', fontWeight: '800', color: '#0f172a', margin: '0 0 0.25rem 0', letterSpacing: '-0.02em' }}>Gestión de Usuarios</h2>
                                            <p style={{ margin: 0, fontSize: '0.875rem', color: '#64748b' }}>
                                                <span style={{ fontWeight: '700', color: '#ea580c' }}>{users.length}</span> usuarios en el sistema
                                            </p>
                                        </div>
                                        <button
                                            onClick={() => setShowUserModal(true)}
                                            style={{
                                                padding: '0.65rem 1.25rem', cursor: 'pointer', border: 'none',
                                                background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
                                                color: 'white', borderRadius: '10px', fontWeight: '700', fontSize: '0.9rem',
                                                display: 'flex', alignItems: 'center', gap: '0.5rem',
                                                boxShadow: '0 4px 12px rgba(249,115,22,0.35)', transition: 'all 0.2s'
                                            }}
                                            onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = '0 6px 16px rgba(249,115,22,0.45)'; }}
                                            onMouseLeave={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = '0 4px 12px rgba(249,115,22,0.35)'; }}
                                        >
                                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
                                            Nuevo Usuario
                                        </button>
                                    </div>

                                    {/* Grid Usuarios */}
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1.25rem' }}>
                                        {users.map((user) => {
                                            const rolNombre = user.rol ? user.rol.nombre : 'Sin rol';
                                            const isAdmin = rolNombre.toLowerCase().includes('admin');
                                            const initials = user.username.charAt(0).toUpperCase();
                                            const linkedContact = user.contacto;
                                            return (
                                                <div key={user.id} style={{
                                                    background: '#ffffff', borderRadius: '1rem', overflow: 'hidden',
                                                    border: '1px solid #e2e8f0', boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                                                    transition: 'box-shadow 0.2s, transform 0.2s', display: 'flex', flexDirection: 'column'
                                                }}
                                                    onMouseEnter={e => { e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.1)'; e.currentTarget.style.transform = 'translateY(-2px)'; }}
                                                    onMouseLeave={e => { e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.06)'; e.currentTarget.style.transform = 'none'; }}
                                                >
                                                    <div style={{ height: '6px', background: isAdmin ? 'linear-gradient(90deg, #c2410c, #f97316)' : 'linear-gradient(90deg, #f97316, #fb923c)' }} />
                                                    <div style={{ padding: '1.25rem' }}>
                                                        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                                                            <div style={{
                                                                width: '48px', height: '48px', borderRadius: '50%', flexShrink: 0,
                                                                background: isAdmin ? 'linear-gradient(135deg, #c2410c, #f97316)' : 'linear-gradient(135deg, #f97316, #fb923c)',
                                                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                                color: 'white', fontWeight: '800', fontSize: '1.1rem',
                                                                boxShadow: `0 4px 10px ${isAdmin ? 'rgba(194,65,12,0.3)' : 'rgba(249,115,22,0.3)'}`
                                                            }}>
                                                                {initials}
                                                            </div>
                                                            <div style={{ minWidth: 0, flex: 1 }}>
                                                                <h3 style={{ margin: '0 0 0.25rem 0', fontSize: '1rem', fontWeight: '700', color: '#0f172a', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                                                    {linkedContact ? `${linkedContact.nombre} ${linkedContact.apellido}` : user.username}
                                                                </h3>
                                                                <span style={{ fontSize: '0.72rem', padding: '0.15rem 0.55rem', borderRadius: '999px', background: isAdmin ? '#fff7ed' : '#ffedd5', color: isAdmin ? '#c2410c' : '#ea580c', fontWeight: '700', border: `1px solid ${isAdmin ? '#fed7aa' : '#fdba74'}` }}>
                                                                    {rolNombre}
                                                                </span>
                                                            </div>
                                                        </div>
                                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1.25rem' }}>
                                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                                                                <span style={{ fontSize: '0.9rem', flexShrink: 0 }}>🔑</span>
                                                                <span style={{ fontSize: '0.82rem', color: '#64748b', fontFamily: 'monospace' }}>@{user.username}</span>
                                                            </div>
                                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                                                                <span style={{ fontSize: '0.9rem', flexShrink: 0 }}>📧</span>
                                                                <span style={{ fontSize: '0.82rem', color: linkedContact?.email ? '#475569' : '#94a3b8', fontStyle: linkedContact?.email ? 'normal' : 'italic', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                                    {linkedContact?.email || 'Sin email'}
                                                                </span>
                                                            </div>
                                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                                                                <span style={{ fontSize: '0.9rem', flexShrink: 0 }}>🏢</span>
                                                                <span style={{ fontSize: '0.82rem', color: linkedContact ? '#475569' : '#94a3b8', fontStyle: linkedContact ? 'normal' : 'italic' }}>
                                                                    {linkedContact ? 'Vinculado a contacto' : 'Usuario independiente'}
                                                                </span>
                                                            </div>
                                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                                                                <span style={{ fontSize: '0.9rem', flexShrink: 0 }}>⚡</span>
                                                                <span style={{ fontSize: '0.72rem', padding: '0.1rem 0.5rem', borderRadius: '999px', background: user.activo ? '#dcfce7' : '#fee2e2', color: user.activo ? '#15803d' : '#b91c1c', fontWeight: '600', border: `1px solid ${user.activo ? '#bbf7d0' : '#fca5a5'}` }}>
                                                                    {user.activo ? '● Activo' : '● Inactivo'}
                                                                </span>
                                                            </div>
                                                        </div>
                                                    </div>
                                                    <div style={{ padding: '0.875rem 1.25rem', borderTop: '1px solid #f1f5f9', background: '#f8fafc', display: 'flex', gap: '0.5rem', marginTop: 'auto' }}>
                                                        <button
                                                            onClick={() => handleEditUser(user)}
                                                            style={{ flex: 1, padding: '0.5rem', border: '1px solid #e2e8f0', background: 'white', borderRadius: '8px', cursor: 'pointer', fontSize: '0.82rem', fontWeight: '600', color: '#475569', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.35rem', transition: 'all 0.2s' }}
                                                            onMouseEnter={e => { e.currentTarget.style.background = '#fff7ed'; e.currentTarget.style.borderColor = '#f97316'; e.currentTarget.style.color = '#ea580c'; }}
                                                            onMouseLeave={e => { e.currentTarget.style.background = 'white'; e.currentTarget.style.borderColor = '#e2e8f0'; e.currentTarget.style.color = '#475569'; }}
                                                        >✏️ Editar</button>
                                                        <button
                                                            onClick={() => handleDeleteUser(user.id)}
                                                            title="Eliminar"
                                                            style={{ padding: '0.5rem 0.75rem', border: '1px solid #fee2e2', background: '#fff1f2', borderRadius: '8px', cursor: 'pointer', fontSize: '0.82rem', color: '#dc2626', display: 'flex', alignItems: 'center', transition: 'all 0.2s' }}
                                                            onMouseEnter={e => { e.currentTarget.style.background = '#fee2e2'; }}
                                                            onMouseLeave={e => { e.currentTarget.style.background = '#fff1f2'; }}
                                                        >🗑️</button>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                        {users.length === 0 && (
                                            <div style={{ textAlign: 'center', gridColumn: '1 / -1', padding: '4rem 2rem', color: '#94a3b8', background: '#f8fafc', borderRadius: '1rem', border: '2px dashed #e2e8f0' }}>
                                                <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>👥</div>
                                                <p style={{ fontWeight: '600', fontSize: '1rem', margin: '0 0 0.5rem 0' }}>No hay usuarios registrados</p>
                                                <p style={{ fontSize: '0.875rem', margin: 0 }}>Crea el primer usuario del sistema</p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ) : (
                                <div style={{ animation: 'fadeIn 0.4s ease-out' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
                                        <div>
                                            <h2 style={{ fontSize: '1.4rem', fontWeight: '800', color: '#0f172a', margin: '0 0 0.25rem 0', letterSpacing: '-0.02em' }}>Sucursales</h2>
                                            <p style={{ margin: 0, fontSize: '0.875rem', color: '#64748b' }}>
                                                <span style={{ fontWeight: '700', color: '#ea580c' }}>{sucursales.length}</span> sucursales registradas
                                            </p>
                                        </div>
                                        <button
                                            onClick={() => openSucursalModal()}
                                            style={{
                                                padding: '0.65rem 1.25rem', cursor: 'pointer', border: 'none',
                                                background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
                                                color: 'white', borderRadius: '10px', fontWeight: '700', fontSize: '0.9rem',
                                                display: 'flex', alignItems: 'center', gap: '0.5rem',
                                                boxShadow: '0 4px 12px rgba(249,115,22,0.35)', transition: 'all 0.2s'
                                            }}
                                            onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = '0 6px 16px rgba(249,115,22,0.45)'; }}
                                            onMouseLeave={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = '0 4px 12px rgba(249,115,22,0.35)'; }}
                                        >
                                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
                                            Nueva Sucursal
                                        </button>
                                    </div>
                                    {/* Lista Sucursales */}
                                    <div className="recordings-list-container" style={{ border: '1px solid #e2e8f0', borderRadius: '12px', overflow: 'hidden', background: 'white' }}>
                                        <div className="recordings-list-header" style={{ display: 'grid', gridTemplateColumns: 'minmax(250px, 2fr) minmax(200px, 1.5fr) minmax(150px, 1fr) 200px', gap: '1rem', padding: '1rem 1.5rem', background: '#fff7ed', borderBottom: '1px solid #fed7aa', color: '#c2410c', fontWeight: '600', fontSize: '0.9rem' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><path d="M9 3v18" /><path d="M15 3v18" /></svg>
                                                Sucursal
                                            </div>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" /><circle cx="12" cy="10" r="3" /></svg>
                                                Dirección
                                            </div>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" /></svg>
                                                Estado
                                            </div>
                                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.5rem' }}>
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" /></svg>
                                                Acciones
                                            </div>
                                        </div>
                                        <div className="recordings-list-body" style={{ display: 'flex', flexDirection: 'column' }}>
                                            {sucursales.map((s) => (
                                                <div key={s.id} className="recording-row hover-row" style={{ display: 'grid', gridTemplateColumns: 'minmax(250px, 2fr) minmax(200px, 1.5fr) minmax(150px, 1fr) 200px', gap: '1rem', padding: '1rem 1.5rem', borderBottom: '1px solid #f1f5f9', alignItems: 'center', transition: 'background-color 0.2s', backgroundColor: 'inherit' }}>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                                        <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'linear-gradient(135deg, #10b981, #34d399)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, boxShadow: '0 4px 10px rgba(16,185,129,0.3)' }}>
                                                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><polyline points="9 22 9 12 15 12 15 22" /></svg>
                                                        </div>
                                                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                                                            <span className="font-medium" style={{ fontSize: '1rem', color: '#0f172a', fontWeight: '700' }}>
                                                                {s.nombre}
                                                            </span>
                                                        </div>
                                                    </div>
                                                    
                                                    <div style={{ display: 'flex', alignItems: 'center', color: '#475569', fontSize: '0.9rem' }}>
                                                        {s.direccion || <span style={{ fontStyle: 'italic', color: '#94a3b8' }}>Sin dirección</span>}
                                                    </div>
                                                    
                                                    <div style={{ display: 'flex', alignItems: 'center' }}>
                                                        {s.activa ? (
                                                            <span style={{ fontSize: '0.75rem', padding: '0.2rem 0.75rem', borderRadius: '999px', background: '#dcfce7', color: '#15803d', fontWeight: '600', border: '1px solid #bbf7d0', display: 'inline-block' }}>
                                                                Activa
                                                            </span>
                                                        ) : (
                                                            <span style={{ fontSize: '0.75rem', padding: '0.2rem 0.75rem', borderRadius: '999px', background: '#f1f5f9', color: '#64748b', fontWeight: '600', border: '1px solid #e2e8f0', display: 'inline-block' }}>
                                                                Inactiva
                                                            </span>
                                                        )}
                                                    </div>
                                                    
                                                    <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                                                        <button
                                                            onClick={() => openSucursalModal(s)}
                                                            style={{ padding: '0.4rem 0.6rem', border: '1px solid #e2e8f0', background: 'white', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.3rem', transition: 'all 0.2s', color: '#475569', fontSize: '0.8rem', fontWeight: '600' }}
                                                            onMouseEnter={e => { e.currentTarget.style.background = '#f8fafc'; }}
                                                            onMouseLeave={e => { e.currentTarget.style.background = 'white'; }}
                                                        >
                                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
                                                            Editar
                                                        </button>
                                                        <button
                                                            onClick={() => handleDeleteSucursal(s.id)}
                                                            title="Eliminar"
                                                            style={{ padding: '0.4rem 0.6rem', border: '1px solid #fee2e2', background: '#fff1f2', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.2s', color: '#dc2626' }}
                                                            onMouseEnter={e => { e.currentTarget.style.background = '#fecaca'; }}
                                                            onMouseLeave={e => { e.currentTarget.style.background = '#fff1f2'; }}
                                                        >
                                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>
                                                        </button>
                                                    </div>
                                                </div>
                                            ))}
                                            {sucursales.length === 0 && (
                                                <div style={{ textAlign: 'center', padding: '4rem 2rem', color: '#94a3b8', background: '#f8fafc' }}>
                                                    <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🏢</div>
                                                    <p style={{ fontWeight: '600', fontSize: '1rem', margin: '0 0 0.5rem 0' }}>No hay sucursales registradas</p>
                                                    <p style={{ fontSize: '0.875rem', margin: 0 }}>Haz clic en "Nueva Sucursal" para empezar.</p>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>

                        <style>{`
                            @keyframes fadeIn {
                                from { opacity: 0; transform: translateY(10px); }
                                to { opacity: 1; transform: translateY(0); }
                            }
                        `}</style>
                    </>
                );








            case "registro":
                return (
                    <section className="card" style={{ padding: '0', overflow: 'hidden' }}>
                        <div className="table-header" style={{ padding: '1.5rem 2rem', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                            <h2 style={{ fontSize: '1.25rem', fontWeight: '700', color: 'var(--text-primary)', margin: 0, display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                <span style={{ fontSize: '1.5rem' }}>📝</span>
                                Registro Permanente de Auditoría
                            </h2>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                <input 
                                    type="date" 
                                    value={logsDateFilter}
                                    onChange={(e) => { setLogsDateFilter(e.target.value); setLogsPage(1); }}
                                    style={{ padding: '0.5rem 1rem', borderRadius: '8px', border: '1px solid var(--border-color)', outline: 'none', color: 'var(--text-primary)' }}
                                />
                                <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                                    {logsTotal} registros en total
                                </span>
                            </div>
                        </div>
                        <div style={{ backgroundColor: '#f8fafc' }}>
                            <div className="table-responsive">
                                <table className="table" style={{ margin: 0 }}>
                                    <thead style={{ backgroundColor: '#f1f5f9' }}>
                                        <tr>
                                            <th>Fecha y Hora</th>
                                            <th>Actor (User / IP)</th>
                                            <th>Acción Realizada</th>
                                            <th>Entidad Afectada (Destino)</th>
                                        </tr>
                                    </thead>
                                    <tbody style={{ backgroundColor: 'white' }}>
                                        {logs.map((log) => (
                                            <tr key={log.id} style={{ transition: 'background-color 0.2s', borderBottom: '1px solid #e2e8f0' }}>
                                                {/* Fecha */}
                                                <td style={{ verticalAlign: 'middle', paddingTop: '1.25rem', paddingBottom: '1.25rem' }}>
                                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                                                        <span style={{ fontWeight: '600', color: 'var(--text-primary)' }}>
                                                            {getEcuadorDateString(log.fecha_accion)}
                                                        </span>
                                                        <span style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
                                                            {getEcuadorTimeString(log.fecha_accion)}
                                                        </span>
                                                    </div>
                                                </td>

                                                {/* Actor & IP */}
                                                <td style={{ verticalAlign: 'middle', paddingTop: '1.25rem', paddingBottom: '1.25rem' }}>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                                        <div style={{
                                                            width: '36px', height: '36px', borderRadius: '50%',
                                                            backgroundColor: log.usuario_actor ? '#e0e7ff' : '#f1f5f9',
                                                            color: log.usuario_actor ? '#4338ca' : '#64748b',
                                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                            fontWeight: 'bold', fontSize: '1rem', flexShrink: 0
                                                        }}>
                                                            {log.usuario_actor ? log.usuario_actor.username.charAt(0).toUpperCase() : 'S'}
                                                        </div>
                                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                                                            <span style={{ fontWeight: '600', color: 'var(--text-primary)', fontSize: '0.95rem' }}>
                                                                {log.usuario_actor ? log.usuario_actor.username : "Sistema Automatizado"}
                                                            </span>
                                                            <span style={{ fontSize: '0.8rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '0.25rem', marginTop: '0.1rem' }}>
                                                                🌐 IP: {log.direccion_ip || 'Local / Interna'}
                                                            </span>
                                                        </div>
                                                    </div>
                                                </td>

                                                {/* Acción y Descripción Humana */}
                                                <td style={{ verticalAlign: 'middle', paddingTop: '1.25rem', paddingBottom: '1.25rem' }}>
                                                    {(() => {
                                                        const human = getHumanLogDescription(log);
                                                        return (
                                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                                                                <span className="status-badge" style={{
                                                                    padding: '0.35rem 0.75rem', borderRadius: '6px',
                                                                    backgroundColor: human.accion.bg,
                                                                    color: human.accion.color,
                                                                    border: `1px solid ${human.accion.border}`,
                                                                    fontWeight: '700', fontSize: '0.78rem',
                                                                    display: 'inline-flex', alignItems: 'center', gap: '0.3rem',
                                                                    width: 'fit-content'
                                                                }}>
                                                                    {human.accion.label}
                                                                </span>
                                                                <span style={{ fontSize: '0.82rem', color: '#64748b' }}>
                                                                    {human.resumen}
                                                                </span>
                                                            </div>
                                                        );
                                                    })()}
                                                </td>

                                                {/* Entidad Afectada */}
                                                <td style={{ verticalAlign: 'middle', paddingTop: '1.25rem', paddingBottom: '1.25rem' }}>
                                                    {(() => {
                                                        const human = getHumanLogDescription(log);
                                                        return (
                                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                                                                <span style={{ fontSize: '0.92rem', color: 'var(--text-primary)', fontWeight: '700' }}>
                                                                    {human.entidad}
                                                                </span>
                                                                {human.detalle && (
                                                                    <span style={{ fontSize: '0.8rem', color: '#0284c7', fontWeight: '500' }}>
                                                                        {human.detalle}
                                                                    </span>
                                                                )}
                                                            </div>
                                                        );
                                                    })()}
                                                </td>
                                            </tr>
                                        ))}
                                        {logs.length === 0 && (
                                            <tr>
                                                <td colSpan="4" style={{ textAlign: 'center', padding: '4rem 2rem', color: 'var(--text-secondary)' }}>
                                                    <div style={{ fontSize: '3rem', marginBottom: '1rem', opacity: 0.5 }}>📭</div>
                                                    <p style={{ margin: 0, fontSize: '1.1rem', fontWeight: '500' }}>No existen registros de auditoría en la Base de Datos.</p>
                                                    <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.9rem' }}>Los logs de tipo INSERT, UPDATE o DELETE aparecerán aquí.</p>
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                            <div style={{ padding: '1rem 2rem', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#fff' }}>
                                <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                                    Mostrando página {logsPage} de {Math.max(1, Math.ceil(logsTotal / logsLimit))}
                                </span>
                                <div style={{ display: 'flex', gap: '0.5rem' }}>
                                    <button 
                                        onClick={() => setLogsPage(p => Math.max(1, p - 1))}
                                        disabled={logsPage === 1}
                                        style={{ padding: '0.5rem 1rem', borderRadius: '6px', border: '1px solid var(--border-color)', backgroundColor: logsPage === 1 ? '#f1f5f9' : 'white', cursor: logsPage === 1 ? 'not-allowed' : 'pointer' }}>
                                        Anterior
                                    </button>
                                    <button 
                                        onClick={() => setLogsPage(p => p + 1)}
                                        disabled={logsPage >= Math.ceil(logsTotal / logsLimit)}
                                        style={{ padding: '0.5rem 1rem', borderRadius: '6px', border: '1px solid var(--border-color)', backgroundColor: logsPage >= Math.ceil(logsTotal / logsLimit) ? '#f1f5f9' : 'white', cursor: logsPage >= Math.ceil(logsTotal / logsLimit) ? 'not-allowed' : 'pointer' }}>
                                        Siguiente
                                    </button>
                                </div>
                            </div>
                        </div>
                    </section>
                );

            case "metricas-manager":
                return (
                    <section className="card" style={{ background: 'transparent', boxShadow: 'none' }}>
                        <MetricsManager />
                    </section>
                );

            case "chatwoot-metricas":
                return <ChatwootHub defaultTab="metricas" onTabChange={(tab) => setCurrentView(`chatwoot-${tab}`)} />;

            case "chatwoot-ejecutivo":
                return <ChatwootHub defaultTab="ejecutivo" onTabChange={(tab) => setCurrentView(`chatwoot-${tab}`)} />;

            case "chatwoot-dragdrop":
                return <ChatwootHub defaultTab="dragdrop" onTabChange={(tab) => setCurrentView(`chatwoot-${tab}`)} />;

            default:
                return null;
        }
    };

    return (
        <div className={`layout ${!isSidebarOpen ? 'sidebar-collapsed' : ''}`}>
            {/* SIDEBAR */}
            <aside className="sidebar">
                <div className="sidebar-header" style={{ justifyContent: isSidebarOpen ? 'flex-start' : 'center', padding: isSidebarOpen ? '1.5rem' : '1.5rem 0' }}>
                    <div
                        className="logo"
                        style={{ display: 'flex', alignItems: 'center', gap: isSidebarOpen ? '10px' : '0', cursor: 'pointer' }}
                        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                        title={isSidebarOpen ? "Contraer Menú" : "Abrir Menú"}
                    >
                        <span className="logo-icon" style={{ fontSize: '1.5rem', minWidth: '1.5rem', textAlign: 'center' }}>📦</span>
                        {isSidebarOpen && <span className="logo-text" style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>Admin</span>}
                    </div>
                </div>

                <nav className="menu">
                    <a href="#" className={`menu-item ${currentView === 'panel' ? 'active' : ''}`} title="Inicio" onClick={(e) => { e.preventDefault(); setCurrentView('panel'); }}>
                        <span className="icon">🏠</span>
                        {isSidebarOpen && <span className="menu-text">Inicio</span>}
                    </a>
                    <a href="#" className={`menu-item ${currentView === 'configuracion' ? 'active' : ''}`} title="Configuración" onClick={(e) => { e.preventDefault(); setCurrentView('configuracion'); }}>
                        <span className="icon">⚙️</span>
                        {isSidebarOpen && <span className="menu-text">Configuración</span>}
                    </a>
                    <a href="#" className={`menu-item ${currentView === 'personal' ? 'active' : ''}`} title="Personal" onClick={(e) => { e.preventDefault(); setCurrentView('personal'); }}>
                        <span className="icon">👥</span>
                        {isSidebarOpen && <span className="menu-text">Personal</span>}
                    </a>
                    <a href="#" className={`menu-item ${currentView === 'analisis' ? 'active' : ''}`} title="Análisis" onClick={(e) => { e.preventDefault(); setCurrentView('analisis'); }}>
                        <span className="icon">📈</span>
                        {isSidebarOpen && <span className="menu-text">Análisis</span>}
                    </a>

                    <a href="#" className={`menu-item ${currentView === 'metricas-manager' ? 'active' : ''}`} title="Métricas" onClick={(e) => { e.preventDefault(); setCurrentView('metricas-manager'); }}>
                        <span className="icon">📏</span>
                        {isSidebarOpen && <span className="menu-text">Métricas</span>}
                    </a>

                    <a href="#" className={`menu-item ${currentView === 'registro' ? 'active' : ''}`} title="Registro" onClick={(e) => { e.preventDefault(); setCurrentView('registro'); }}>
                        <span className="icon">📝</span>
                        {isSidebarOpen && <span className="menu-text">Registro</span>}
                    </a>

                    {/* CANALES CHATBOT & CHATWOOT */}
                    <div style={{ margin: '14px 0 6px 0', borderTop: '1px solid #e2e8f0', paddingTop: '10px' }}>
                        {isSidebarOpen && <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.06em', padding: '0 14px' }}>Canales Chatbot</span>}
                    </div>

                    <a href="#" className={`menu-item ${currentView === 'chatwoot-metricas' ? 'active' : ''}`} title="Métricas Chatwoot" onClick={(e) => { e.preventDefault(); setCurrentView('chatwoot-metricas'); }}>
                        <span className="icon">💬</span>
                        {isSidebarOpen && <span className="menu-text">Métricas Chatwoot</span>}
                    </a>

                    <a href="#" className={`menu-item ${currentView === 'chatwoot-ejecutivo' ? 'active' : ''}`} title="Reporte Ejecutivo" onClick={(e) => { e.preventDefault(); setCurrentView('chatwoot-ejecutivo'); }}>
                        <span className="icon">📊</span>
                        {isSidebarOpen && <span className="menu-text">Reporte Ejecutivo</span>}
                    </a>

                    <a href="#" className={`menu-item ${currentView === 'chatwoot-dragdrop' ? 'active' : ''}`} title="Auditoría Drag & Drop" onClick={(e) => { e.preventDefault(); setCurrentView('chatwoot-dragdrop'); }}>
                        <span className="icon">🎯</span>
                        {isSidebarOpen && <span className="menu-text">Auditoría Drag & Drop</span>}
                    </a>
                </nav>

                <div className="sidebar-footer">
                    {isSidebarOpen && <p style={{ marginBottom: '10px' }}>Usuario: {user?.username}</p>}
                    <button
                        onClick={handleLogout}
                        className="btn-logout"
                        title="Cerrar Sesión"
                        style={{
                            width: '100%',
                            padding: '0.5rem',
                            cursor: 'pointer',
                            background: 'none',
                            border: '1px solid var(--danger-color)',
                            color: 'var(--danger-color)',
                            borderRadius: 'var(--radius-md)',
                            fontWeight: '500',
                            transition: 'all 0.2s',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '0.5rem'
                        }}
                    >
                        <span className="icon">🚪</span>
                        {isSidebarOpen && <span>Salir</span>}
                    </button>
                </div>
            </aside>

            {/* CONTENT */}
            <main className="layout-content">
                <header className="topbar">
                    <div className="topbar-left" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <h1 className="page-title">
                            {currentView === 'panel' && "Panel de Control"}
                            {currentView === 'configuracion' && "Configuración"}
                            {currentView === 'personal' && "Personal"}
                            {currentView === 'analisis' && "Análisis"}
                            {currentView === 'metricas-manager' && "Métricas"}
                            {currentView === 'registro' && "Registro"}
                            {currentView === 'chatwoot-metricas' && "Métricas de Chatwoot & WhatsApp"}
                            {currentView === 'chatwoot-ejecutivo' && "Reporte Ejecutivo y Ventas del Chatbot"}
                            {currentView === 'chatwoot-dragdrop' && "Auditoría de Conversaciones (Drag & Drop)"}
                        </h1>
                    </div>

                    <div className="topbar-right">
                        <div className="topbar-actions" style={{ position: 'relative' }} ref={notificationsRef}>
                            <button
                                className="icon-btn"
                                title="Notificaciones de Auditoría"
                                onClick={() => setShowNotifications(!showNotifications)}
                            >
                                🔔
                                {logs && logs.length > 0 && (
                                    <span className="badge badge-orange">{logs.length}</span>
                                )}
                            </button>

                            {/* Notifications Dropdown */}
                            {showNotifications && (
                                <div style={{
                                    position: 'absolute',
                                    top: '100%',
                                    right: 0,
                                    marginTop: '0.5rem',
                                    width: '320px',
                                    backgroundColor: '#ffffff',
                                    borderRadius: '12px',
                                    boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
                                    border: '1px solid #e2e8f0',
                                    zIndex: 1000,
                                    overflow: 'hidden',
                                    animation: 'fadeIn 0.2s ease-out'
                                }}>
                                    <div style={{ padding: '1rem', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#f8fafc' }}>
                                        <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: '700', color: '#0f172a' }}>Notificaciones Recientes</h3>
                                        <span style={{ fontSize: '0.75rem', color: '#64748b', background: '#e2e8f0', padding: '0.15rem 0.5rem', borderRadius: '999px', fontWeight: '600' }}>{logs.length} Total</span>
                                    </div>
                                    <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                                        {logs.length > 0 ? (
                                            logs.slice(0, 5).map(log => (
                                                <div key={log.id} style={{ padding: '0.75rem 1rem', borderBottom: '1px solid #f1f5f9', cursor: 'pointer', transition: 'background-color 0.2s' }}
                                                    onMouseEnter={e => e.currentTarget.style.backgroundColor = '#f8fafc'}
                                                    onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
                                                    onClick={() => { setShowNotifications(false); setCurrentView('registro'); }}
                                                >
                                                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                                                        <div style={{
                                                            width: '8px', height: '8px', borderRadius: '50%', flexShrink: 0, marginTop: '6px',
                                                            backgroundColor: log.tipo_accion === 'INSERT' ? '#10b981' : log.tipo_accion === 'UPDATE' ? '#f59e0b' : log.tipo_accion === 'DELETE' ? '#ef4444' : '#64748b'
                                                        }} />
                                                        <div style={{ flex: 1 }}>
                                                            {(() => {
                                                                const human = getHumanLogDescription(log);
                                                                return (
                                                                    <p style={{ margin: '0 0 0.25rem 0', fontSize: '0.85rem', color: '#334155', lineHeight: '1.4' }}>
                                                                        <span style={{ fontWeight: '700', color: '#0f172a' }}>{human.actor}</span> {human.accion.verb} <strong>{human.entidad.toLowerCase()}</strong>{human.detalle}
                                                                    </p>
                                                                );
                                                            })()}
                                                            <span style={{ fontSize: '0.7rem', color: '#94a3b8' }}>{getEcuadorDateTimeString(log.fecha_accion)}</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            ))
                                        ) : (
                                            <div style={{ padding: '2rem 1rem', textAlign: 'center', color: '#94a3b8' }}>
                                                <div style={{ fontSize: '2rem', marginBottom: '0.5rem', opacity: 0.5 }}>📭</div>
                                                <p style={{ margin: 0, fontSize: '0.85rem' }}>No hay notificaciones nuevas</p>
                                            </div>
                                        )}
                                    </div>
                                    {logs.length > 0 && (
                                        <div
                                            style={{ padding: '0.75rem', textAlign: 'center', borderTop: '1px solid #e2e8f0', background: '#f8fafc', color: '#3b82f6', fontSize: '0.85rem', fontWeight: '600', cursor: 'pointer' }}
                                            onClick={() => { setShowNotifications(false); setCurrentView('registro'); }}
                                            onMouseEnter={e => e.currentTarget.style.textDecoration = 'underline'}
                                            onMouseLeave={e => e.currentTarget.style.textDecoration = 'none'}
                                        >
                                            Ver todo el registro de auditoría
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                        <div className="user-profile" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                            <span style={{ fontWeight: '500', color: 'var(--text-secondary)' }}>{user?.username || 'Admin'}</span>
                            <div className="avatar">
                                {user?.username ? user.username.charAt(0).toUpperCase() : 'U'}
                            </div>
                        </div>
                    </div>
                </header>

                <div className="page-content">
                    {renderContent()}
                </div>
            </main>

            {/* TRANSCRIPTION MODAL */}
            {selectedRecording && (
                <div className="modal-overlay" style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(15, 23, 42, 0.6)', display: 'flex', justifyContent: 'center', alignItems: 'center',
                    zIndex: 1000, backdropFilter: 'blur(4px)'
                }}>
                    <div className="modal-content" style={{
                        backgroundColor: 'white', padding: '0', borderRadius: 'var(--radius-xl)',
                        width: '90%', maxWidth: '850px', maxHeight: '85vh', overflow: 'hidden',
                        boxShadow: 'var(--shadow-2xl)', display: 'flex', flexDirection: 'column',
                        animation: 'fadeIn 0.3s ease-out'
                    }}>
                        <div style={{ padding: '1.5rem 2rem', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', background: '#f8fafc' }}>
                            <div>
                                <h2 style={{ fontSize: '1.25rem', color: 'var(--text-primary)', margin: '0 0 0.5rem 0', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    <span style={{ fontSize: '1.5rem' }}>📝</span> Transcripción de Llamada
                                </h2>
                                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                    <span className="badge badge-blue">Cajero: {selectedRecording.cajero}</span>
                                    <span className="badge badge-orange">Duración: {selectedRecording.duracion}</span>
                                    <span className="badge badge-green">Caja: {selectedRecording.caja}</span>
                                </div>
                            </div>
                            <button
                                onClick={() => setSelectedRecording(null)}
                                className="icon-btn"
                                style={{ background: 'white', border: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}
                                title="Cerrar"
                            >
                                ✕
                            </button>
                        </div>

                        <div className="transcription-body" style={{
                            fontSize: '0.95rem', lineHeight: '1.6',
                            padding: '2rem', flexGrow: 1, overflowY: 'auto',
                            backgroundColor: 'white'
                        }}>
                            {isTranscriptionLoading ? (
                                <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
                                    <div style={{ fontSize: '2rem', marginBottom: '1rem', animation: 'spin 1s linear infinite' }}>⏳</div>
                                    Cargando transcripción...
                                </div>
                            ) : transcriptionError ? (
                                <div style={{ textAlign: 'center', padding: '3rem', color: '#ef4444' }}>
                                    <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>⚠️</div>
                                    <p style={{ fontWeight: '600', margin: '0 0 0.5rem 0' }}>Error al cargar la transcripción</p>
                                    <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-secondary)' }}>{transcriptionError}</p>
                                </div>
                            ) : transcriptionData && transcriptionData.length > 0 && transcriptionData[0].segmentos && transcriptionData[0].segmentos.length > 0 ? (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                                    {transcriptionData[0].segmentos.map((segmento, idx) => {
                                        const speakerName = segmento.hablante || 'SPEAKER_00';
                                        const isSpeaker0 = speakerName.includes('00');
                                        return (
                                            <div key={idx} style={{
                                                display: 'flex',
                                                alignItems: 'baseline',
                                                gap: '1rem',
                                                padding: '0.5rem 0.5rem',
                                                borderBottom: '1px solid #f8fafc',
                                                fontFamily: 'monospace, sans-serif'
                                            }}>
                                                <span style={{ color: '#64748b', fontSize: '0.9rem', whiteSpace: 'nowrap', minWidth: '160px', flexShrink: 0 }}>
                                                    [ {Number(segmento.inicio_segundo).toFixed(2).padStart(5, '0')} - {Number(segmento.fin_segundo).toFixed(2).padStart(5, '0')} ]
                                                </span>
                                                <span style={{
                                                    color: isSpeaker0 ? '#0ea5e9' : '#f97316',
                                                    fontWeight: '700',
                                                    minWidth: '85px',
                                                    flexShrink: 0,
                                                    fontSize: '0.95rem'
                                                }}>
                                                    {speakerName}:
                                                </span>
                                                <span style={{
                                                    color: '#334155',
                                                    fontSize: '0.95rem',
                                                    fontFamily: 'system-ui, -apple-system, sans-serif',
                                                    lineHeight: '1.5'
                                                }}>
                                                    {segmento.texto}
                                                </span>
                                            </div>
                                        );
                                    })}
                                </div>
                            ) : transcriptionData && transcriptionData.length > 0 && transcriptionData[0].texto_completo ? (
                                <div style={{ padding: '1rem', whiteSpace: 'pre-wrap', color: '#334155', fontFamily: 'system-ui, -apple-system, sans-serif', fontSize: '0.95rem', lineHeight: '1.6' }}>
                                    <div style={{ padding: '0.75rem 1rem', background: '#f8fafc', borderLeft: '4px solid #cbd5e1', borderRadius: '6px', color: '#64748b', fontSize: '0.85rem', marginBottom: '1.5rem', fontWeight: '500' }}>
                                        ℹ️ Se muestra el texto completo de la llamada ya que no se encontraron marcas de tiempo detalladas.
                                    </div>
                                    {transcriptionData[0].texto_completo}
                                </div>
                            ) : (
                                <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
                                    <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>📭</div>
                                    No hay transcripción disponible para esta grabación.
                                </div>
                            )}
                        </div>

                        <div style={{ padding: '1.5rem', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'flex-end', gap: '1rem', background: '#f8fafc' }}>
                            <button className="btn" onClick={() => setSelectedRecording(null)} style={{ padding: '0.6rem 1.25rem', cursor: 'pointer', border: '1px solid var(--border-color)', background: 'white', fontWeight: '500' }}>Cerrar</button>
                            <button className="btn btn-primary" style={{ padding: '0.6rem 1.25rem', fontWeight: '500' }} disabled={isTranscriptionLoading || !transcriptionData}>
                                Descargar Texto
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* ANALYSIS MODAL */}
            {selectedAnalysis && (
                <div className="modal-overlay" style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(15, 23, 42, 0.7)', display: 'flex', justifyContent: 'center', alignItems: 'center',
                    zIndex: 1000, backdropFilter: 'blur(8px)'
                }}>
                    <div className="modal-content" style={{
                        backgroundColor: '#ffffff', padding: '0', borderRadius: '1.25rem',
                        width: '92%', maxWidth: '900px', maxHeight: '90vh', overflow: 'hidden',
                        boxShadow: '0 25px 60px -15px rgba(180,83,9,0.2), 0 10px 30px rgba(0,0,0,0.15)', display: 'flex', flexDirection: 'column',
                        animation: 'fadeIn 0.25s ease-out'
                    }}>
                        {/* Premium Header */}
                        <div style={{
                            padding: '1.75rem 2rem',
                            background: 'linear-gradient(135deg, #431407 0%, #9a3412 40%, #ea580c 80%, #fb923c 100%)',
                            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                            flexShrink: 0,
                            position: 'relative',
                            overflow: 'hidden'
                        }}>
                            {/* Decorative blur orb */}
                            <div style={{ position: 'absolute', top: '-30px', right: '80px', width: '120px', height: '120px', borderRadius: '50%', background: 'rgba(251,191,36,0.15)', filter: 'blur(30px)', pointerEvents: 'none' }} />
                            <div style={{ position: 'absolute', bottom: '-20px', left: '200px', width: '80px', height: '80px', borderRadius: '50%', background: 'rgba(255,255,255,0.08)', filter: 'blur(20px)', pointerEvents: 'none' }} />
                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                <div style={{
                                    width: '44px', height: '44px', borderRadius: '12px',
                                    background: 'rgba(255,255,255,0.15)', display: 'flex',
                                    alignItems: 'center', justifyContent: 'center', fontSize: '1.4rem',
                                    backdropFilter: 'blur(4px)', border: '1px solid rgba(255,255,255,0.2)'
                                }}>🎙️</div>
                                <div>
                                    <h2 style={{ fontSize: '1.35rem', color: '#ffffff', margin: '0 0 0.25rem 0', fontWeight: '700', letterSpacing: '-0.01em' }}>
                                        Análisis de Grabación
                                    </h2>
                                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                        <span style={{ fontSize: '0.78rem', padding: '0.15rem 0.6rem', borderRadius: '999px', background: 'rgba(255,255,255,0.15)', color: 'rgba(255,255,255,0.9)', border: '1px solid rgba(255,255,255,0.25)', fontWeight: '500' }}>ID: {selectedAnalysis.id}</span>
                                        <span style={{ fontSize: '0.78rem', padding: '0.15rem 0.6rem', borderRadius: '999px', background: 'rgba(251,191,36,0.25)', color: '#fef3c7', border: '1px solid rgba(251,191,36,0.35)', fontWeight: '600' }}>👤 {selectedAnalysis.cajero}</span>
                                    </div>
                                </div>
                            </div>
                            <button
                                onClick={() => setSelectedAnalysis(null)}
                                style={{
                                    background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)',
                                    borderRadius: '10px', width: '36px', height: '36px', display: 'flex',
                                    alignItems: 'center', justifyContent: 'center',
                                    fontSize: '1.1rem', cursor: 'pointer', color: 'rgba(255,255,255,0.8)',
                                    transition: 'all 0.2s', fontWeight: '600'
                                }}
                                title="Cerrar"
                                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.2)'; }}
                                onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.1)'; }}
                            >
                                ✕
                            </button>
                        </div>

                        <div style={{ flexGrow: 1, overflowY: 'auto', padding: '1.75rem 2rem', backgroundColor: '#fffbf7' }}>
                            {isAnalysisLoading ? (
                                <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
                                    <div className="spinner" style={{ margin: '0 auto 1rem auto', border: '3px solid #fed7aa', borderTop: '3px solid #ea580c', borderRadius: '50%', width: '32px', height: '32px', animation: 'spin 1s linear infinite' }}></div>
                                    Cargando análisis...
                                </div>
                            ) : analysisData ? (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

                                    {/* Header Metrics */}
                                    {(() => {
                                        let sumNormalized = 0;
                                        let countNormalized = 0;
                                        const radarDataMap = {};

                                        let resumenTexto = "";
                                        if (analysisData.resumen_ejecutivo) {
                                            const cleanText = analysisData.resumen_ejecutivo.replace(/\r/g, '');
                                            let firstLineEnd = cleanText.indexOf('\n');
                                            if (firstLineEnd === -1) {
                                                resumenTexto = cleanText.includes('|') && cleanText.includes('=') ? '' : cleanText;
                                            } else {
                                                resumenTexto = cleanText.substring(firstLineEnd + 1).trim();
                                            }
                                        }

                                        const parsedMetricsList = [];
                                        if (analysisData.respuestas) {
                                            analysisData.respuestas.forEach((r, idx) => {
                                                const qText = r.pregunta?.texto_pregunta || `Pregunta ${idx + 1}`;
                                                const catName = r.pregunta?.categoria?.nombre || "General";
                                                const score = r.puntaje_obtenido !== null && r.puntaje_obtenido !== undefined ? parseFloat(r.puntaje_obtenido) : null;
                                                const max = (qText.toLowerCase().includes("customer effort score") || qText.toLowerCase().includes("ces")) ? 5 : 10;

                                                const getAcronym = (text) => {
                                                    const lower = text.toLowerCase();
                                                    if (lower.includes("customer effort score") || lower.includes("ces")) return "CES";
                                                    if (lower.includes("net promoter score") || lower.includes("nps")) return "NPS";
                                                    if (lower.includes("ins") || lower.includes("satisfacción")) return "INS";
                                                    return null;
                                                };
                                                const acronym = getAcronym(qText);

                                                if (score !== null) {
                                                    sumNormalized += (score / max) * 10;
                                                    countNormalized++;
                                                }

                                                if (!radarDataMap[catName]) radarDataMap[catName] = { name: catName, total: 0, count: 0 };
                                                radarDataMap[catName].total += (score !== null ? score : 0) / max * 10;
                                                radarDataMap[catName].count += 1;

                                                if (acronym) {
                                                    let explicitoMatch = undefined;
                                                    if (r.justificacion_ia) {
                                                        if (r.justificacion_ia.includes('Explicito=True')) explicitoMatch = true;
                                                        else if (r.justificacion_ia.includes('Explicito=False')) explicitoMatch = false;
                                                    }
                                                    parsedMetricsList.push({
                                                        sigla: acronym,
                                                        score: score !== null ? score : '-',
                                                        max: max,
                                                        explicito: explicitoMatch,
                                                        justificacion: r.justificacion_ia
                                                    });
                                                }
                                            });
                                        }

                                        const avgScore = countNormalized > 0 ? (sumNormalized / countNormalized).toFixed(1) : '-';
                                        const radarData = Object.values(radarDataMap).map(d => ({ name: d.name, score: Number((d.total / d.count).toFixed(1)), fullMark: 10 }));

                                        return (
                                            <>
                                                {/* ─── Top KPI Row ─── */}
                                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
                                                    {/* Calificación General */}
                                                    <div style={{
                                                        padding: '1.25rem 1.5rem',
                                                        background: 'linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)',
                                                        borderRadius: '1rem', border: '1px solid #6ee7b7',
                                                        display: 'flex', flexDirection: 'column', alignItems: 'center',
                                                        boxShadow: '0 4px 12px rgba(16,185,129,0.1)'
                                                    }}>
                                                        <span style={{ fontSize: '0.7rem', color: '#065f46', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: '700', marginBottom: '0.5rem' }}>Calificación General</span>
                                                        <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.25rem' }}>
                                                            <span style={{ fontSize: '2.75rem', fontWeight: '800', color: '#059669', lineHeight: '1' }}>{avgScore}</span>
                                                            <span style={{ fontSize: '1.1rem', color: '#10b981', fontWeight: '600' }}>/10</span>
                                                        </div>
                                                        {/* mini progress bar */}
                                                        <div style={{ width: '100%', height: '6px', background: '#a7f3d0', borderRadius: '999px', marginTop: '0.75rem', overflow: 'hidden' }}>
                                                            <div style={{ height: '100%', width: `${Math.min((parseFloat(avgScore) || 0) * 10, 100)}%`, background: 'linear-gradient(90deg, #10b981, #059669)', borderRadius: '999px', transition: 'width 0.8s ease' }} />
                                                        </div>
                                                    </div>

                                                    {/* Sentimiento */}
                                                    <div style={{
                                                        padding: '1.25rem 1.5rem',
                                                        background: (() => {
                                                            const s = analysisData.sentimiento_general?.toLowerCase() || '';
                                                            if (s.includes('positiv')) return 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)';
                                                            if (s.includes('negativ')) return 'linear-gradient(135deg, #fff1f2 0%, #ffe4e6 100%)';
                                                            return 'linear-gradient(135deg, #fefce8 0%, #fef9c3 100%)';
                                                        })(),
                                                        borderRadius: '1rem',
                                                        border: (() => {
                                                            const s = analysisData.sentimiento_general?.toLowerCase() || '';
                                                            if (s.includes('positiv')) return '1px solid #93c5fd';
                                                            if (s.includes('negativ')) return '1px solid #fca5a5';
                                                            return '1px solid #fde68a';
                                                        })(),
                                                        display: 'flex', flexDirection: 'column', alignItems: 'center',
                                                        boxShadow: '0 4px 12px rgba(0,0,0,0.05)'
                                                    }}>
                                                        <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: '700', marginBottom: '0.5rem', color: '#374151' }}>Sentimiento</span>
                                                        <span style={{ fontSize: '2.2rem', marginBottom: '0.25rem' }}>
                                                            {analysisData.sentimiento_general?.toLowerCase().includes('positiv') ? '😊' :
                                                                analysisData.sentimiento_general?.toLowerCase().includes('negativ') ? '😠' : '😐'}
                                                        </span>
                                                        <span style={{ fontSize: '0.95rem', fontWeight: '700', color: '#1e293b' }}>{analysisData.sentimiento_general || 'N/A'}</span>
                                                    </div>

                                                    {/* Métricas CES / INS / NPS como mini-KPIs adicionales */}
                                                    {parsedMetricsList.map((metric, idx) => {
                                                        const pct = Math.min((parseFloat(metric.score) || 0) / (parseFloat(metric.max) || 10) * 100, 100);
                                                        const color = pct >= 75 ? '#10b981' : pct >= 50 ? '#f59e0b' : '#ef4444';
                                                        const bg = pct >= 75 ? 'linear-gradient(135deg,#ecfdf5,#d1fae5)' : pct >= 50 ? 'linear-gradient(135deg,#fffbeb,#fef3c7)' : 'linear-gradient(135deg,#fff1f2,#ffe4e6)';
                                                        const borderColor = pct >= 75 ? '#6ee7b7' : pct >= 50 ? '#fcd34d' : '#fca5a5';
                                                        return (
                                                            <div key={idx} style={{
                                                                padding: '1.25rem 1.5rem', background: bg,
                                                                borderRadius: '1rem', border: `1px solid ${borderColor}`,
                                                                display: 'flex', flexDirection: 'column', alignItems: 'center',
                                                                boxShadow: '0 4px 12px rgba(0,0,0,0.05)'
                                                            }}>
                                                                <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center', marginBottom: '0.5rem' }}>
                                                                    <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: '700', color: '#374151' }}>{metric.sigla}</span>
                                                                    {metric.explicito !== undefined && (
                                                                        <span style={{ fontSize: '0.65rem', padding: '0.1rem 0.4rem', borderRadius: '999px', background: metric.explicito ? 'rgba(16,185,129,0.15)' : 'rgba(100,116,139,0.1)', color: metric.explicito ? '#059669' : '#475569', fontWeight: '600', border: '1px solid currentColor' }}>
                                                                            {metric.explicito ? 'Explícito' : 'Implícito'}
                                                                        </span>
                                                                    )}
                                                                </div>
                                                                <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.2rem' }}>
                                                                    <span style={{ fontSize: '2.75rem', fontWeight: '800', color: color, lineHeight: '1' }}>{metric.score}</span>
                                                                    <span style={{ fontSize: '1rem', color: '#64748b', fontWeight: '600' }}>/{metric.max}</span>
                                                                </div>
                                                                <div style={{ width: '100%', height: '5px', background: 'rgba(0,0,0,0.08)', borderRadius: '999px', marginTop: '0.65rem', overflow: 'hidden' }}>
                                                                    <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: '999px', transition: 'width 0.8s ease' }} />
                                                                </div>
                                                            </div>
                                                        );
                                                    })}
                                                </div>

                                                {/* ─── Resumen Ejecutivo ─── */}
                                                {resumenTexto && (
                                                    <div style={{
                                                        padding: '1.5rem',
                                                        background: '#ffffff',
                                                        borderRadius: '1rem',
                                                        border: '1px solid #e2e8f0',
                                                        boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
                                                        position: 'relative',
                                                        overflow: 'hidden'
                                                    }}>
                                                        <div style={{ position: 'absolute', top: 0, left: 0, width: '4px', height: '100%', background: 'linear-gradient(180deg, #f97316, #fb923c)' }} />
                                                        <h3 style={{ fontSize: '0.85rem', marginBottom: '0.75rem', color: '#c2410c', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                                                            <span>📋</span> Resumen Ejecutivo
                                                        </h3>
                                                        <p style={{ color: '#334155', lineHeight: '1.75', fontSize: '0.95rem', whiteSpace: 'pre-wrap', margin: 0 }}>
                                                            {resumenTexto}
                                                        </p>
                                                    </div>
                                                )}

                                                {/* ─── Justificaciones métricas (CES/INS/NPS) ─── */}
                                                {parsedMetricsList.some(m => m.justificacion) && (
                                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '0.75rem' }}>
                                                        {parsedMetricsList.filter(m => m.justificacion).map((metric, idx) => (
                                                            <div key={idx} style={{
                                                                padding: '1rem 1.25rem', background: '#ffffff',
                                                                borderRadius: '0.875rem', border: '1px solid #e2e8f0',
                                                                boxShadow: '0 1px 4px rgba(0,0,0,0.04)'
                                                            }}>
                                                                <span style={{ display: 'inline-block', fontSize: '0.7rem', padding: '0.15rem 0.5rem', borderRadius: '999px', background: '#ffedd5', color: '#c2410c', fontWeight: '700', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.05em', border: '1px solid #fed7aa' }}>{metric.sigla}</span>
                                                                <p style={{ margin: 0, fontSize: '0.875rem', color: '#475569', lineHeight: '1.6' }}>{metric.justificacion}</p>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}

                                                {/* ─── Evaluación Detallada ─── */}
                                                <div>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                                                        <div style={{ width: '28px', height: '28px', borderRadius: '8px', background: 'linear-gradient(135deg, #f97316, #ea580c)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.85rem', boxShadow: '0 2px 6px rgba(249,115,22,0.35)' }}>📊</div>
                                                        <h3 style={{ fontSize: '1rem', color: '#0f172a', fontWeight: '700', margin: 0, letterSpacing: '-0.01em' }}>Evaluación Detallada</h3>
                                                        {analysisData.respuestas && (
                                                            <span style={{ marginLeft: 'auto', fontSize: '0.75rem', padding: '0.2rem 0.6rem', borderRadius: '999px', background: '#fff7ed', color: '#c2410c', fontWeight: '700', border: '1px solid #fed7aa' }}>
                                                                {analysisData.respuestas.length} ítems
                                                            </span>
                                                        )}
                                                    </div>

                                                    {analysisData.respuestas && analysisData.respuestas.length > 0 ? (
                                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                                            {analysisData.respuestas.map((resp, idx) => {
                                                                const questionText = resp.pregunta?.texto_pregunta || "Pregunta";
                                                                const catName = resp.pregunta?.categoria?.nombre;
                                                                const maxScore = questionText.toLowerCase().includes("customer effort score") || questionText.toLowerCase().includes("ces") ? 5 : 10;
                                                                const getAcronym = (text) => {
                                                                    const lower = text.toLowerCase();
                                                                    if (lower.includes("customer effort score") || lower.includes("ces")) return "CES";
                                                                    if (lower.includes("net promoter score") || lower.includes("nps")) return "NPS";
                                                                    if (lower.includes("ins") || lower.includes("satisfacción")) return "INS";
                                                                    return null;
                                                                };
                                                                const acronym = getAcronym(questionText);

                                                                let currentScore = resp.puntaje_obtenido !== null && resp.puntaje_obtenido !== undefined ? Number(resp.puntaje_obtenido) : '-';

                                                                const isEditing = editingResponseId === resp.id;
                                                                const cumple = resp.respuesta_booleana;
                                                                const scorePct = currentScore !== '-' ? Math.min((currentScore / maxScore) * 100, 100) : null;
                                                                const scoreColor = scorePct === null ? '#94a3b8' : scorePct >= 75 ? '#10b981' : scorePct >= 50 ? '#f59e0b' : '#ef4444';

                                                                return (
                                                                    <div key={idx} style={{
                                                                        padding: '1rem 1.25rem',
                                                                        backgroundColor: '#ffffff',
                                                                        borderRadius: '0.875rem',
                                                                        border: '1px solid #e2e8f0',
                                                                        borderLeft: `4px solid ${cumple ? '#10b981' : cumple === false ? '#ef4444' : '#cbd5e1'}`,
                                                                        boxShadow: '0 1px 4px rgba(0,0,0,0.05)',
                                                                        transition: 'box-shadow 0.2s'
                                                                    }}>
                                                                        {/* Question header row */}
                                                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem', marginBottom: resp.justificacion_ia ? '0.875rem' : '0' }}>
                                                                            <div style={{ flex: 1, minWidth: 0 }}>
                                                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.25rem' }}>
                                                                                    <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: '600', flexShrink: 0 }}>#{idx + 1}</span>
                                                                                    {catName && (
                                                                                        <span style={{ fontSize: '0.68rem', padding: '0.1rem 0.45rem', borderRadius: '999px', background: '#f1f5f9', color: '#64748b', border: '1px solid #e2e8f0', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{catName}</span>
                                                                                    )}
                                                                                    {acronym && (
                                                                                        <span style={{ fontSize: '0.68rem', padding: '0.1rem 0.45rem', borderRadius: '999px', background: '#ffedd5', color: '#c2410c', border: '1px solid #fed7aa', fontWeight: '700', textTransform: 'uppercase' }}>{acronym}</span>
                                                                                    )}
                                                                                </div>
                                                                                <span style={{ fontWeight: '600', color: '#1e293b', fontSize: '0.9rem', lineHeight: '1.4', display: 'block' }}>{questionText}</span>
                                                                            </div>

                                                                            {/* Score + Status */}
                                                                            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.4rem', flexShrink: 0 }}>
                                                                                {/* Score bubble */}
                                                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', background: '#f8fafc', padding: '0.3rem 0.6rem', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                                                                                    {isEditing ? (
                                                                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                                                                            <input
                                                                                                type="number" min="0" max={maxScore} step="0.1"
                                                                                                value={tempResponseScore}
                                                                                                onChange={(e) => setTempResponseScore(e.target.value)}
                                                                                                style={{ width: '55px', padding: '0.2rem 0.3rem', textAlign: 'center', border: '1px solid #f97316', borderRadius: '6px', fontSize: '0.9rem', outline: 'none' }}
                                                                                                autoFocus
                                                                                            />
                                                                                            <span style={{ color: '#64748b', fontSize: '0.85rem' }}>/{maxScore}</span>
                                                                                            <button onClick={() => handleSaveResponseScore(resp.id)} style={{ background: '#10b981', border: 'none', color: 'white', cursor: 'pointer', borderRadius: '6px', padding: '0.2rem 0.45rem', fontSize: '0.85rem', fontWeight: '700' }}>✓</button>
                                                                                            <button onClick={() => setEditingResponseId(null)} style={{ background: '#f1f5f9', border: '1px solid #e2e8f0', color: '#64748b', cursor: 'pointer', borderRadius: '6px', padding: '0.2rem 0.45rem', fontSize: '0.85rem' }}>✕</button>
                                                                                        </div>
                                                                                    ) : (
                                                                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                                                                                            <span style={{ fontWeight: '800', fontSize: '1.05rem', color: scoreColor }}>{currentScore}</span>
                                                                                            <span style={{ color: '#94a3b8', fontSize: '0.85rem', fontWeight: '500' }}>/{maxScore}</span>
                                                                                            <button onClick={() => { setEditingResponseId(resp.id); setTempResponseScore(currentScore !== '-' ? currentScore : ''); }} style={{ background: 'none', border: 'none', color: '#ea580c', cursor: 'pointer', marginLeft: '0.25rem', fontSize: '0.8rem', padding: '0', opacity: 0.7 }} title="Editar puntaje">✏️</button>
                                                                                        </div>
                                                                                    )}
                                                                                </div>
                                                                                {/* Cumplimiento badge */}
                                                                                <span style={{
                                                                                    padding: '0.2rem 0.6rem', borderRadius: '999px', fontSize: '0.7rem', fontWeight: '700',
                                                                                    backgroundColor: cumple ? '#d1fae5' : (cumple === false ? '#fee2e2' : '#f1f5f9'),
                                                                                    color: cumple ? '#065f46' : (cumple === false ? '#991b1b' : '#64748b'),
                                                                                    border: `1px solid ${cumple ? '#6ee7b7' : cumple === false ? '#fca5a5' : '#e2e8f0'}`
                                                                                }}>
                                                                                    {cumple ? '✓ Cumple' : (cumple === false ? '✗ No Cumple' : '— N/A')}
                                                                                </span>
                                                                            </div>
                                                                        </div>

                                                                        {/* Mini score bar */}
                                                                        {scorePct !== null && !isEditing && (
                                                                            <div style={{ width: '100%', height: '4px', background: '#f1f5f9', borderRadius: '999px', overflow: 'hidden', marginBottom: resp.justificacion_ia ? '0.75rem' : '0' }}>
                                                                                <div style={{ height: '100%', width: `${scorePct}%`, background: scoreColor, borderRadius: '999px', transition: 'width 0.6s ease' }} />
                                                                            </div>
                                                                        )}

                                                                        {resp.justificacion_ia && (
                                                                            <div style={{ marginTop: '0.25rem', fontSize: '0.875rem', color: '#475569', backgroundColor: '#fff7ed', padding: '0.75rem 1rem', borderRadius: '8px', border: '1px solid #fed7aa', lineHeight: '1.6' }}>
                                                                                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.72rem', fontWeight: '700', color: '#c2410c', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.35rem' }}>💡 Justificación IA</span>
                                                                                <p style={{ margin: 0 }}>{resp.justificacion_ia}</p>
                                                                            </div>
                                                                        )}
                                                                    </div>
                                                                );
                                                            })}
                                                        </div>
                                                    ) : (
                                                        <div style={{ padding: '2.5rem', textAlign: 'center', backgroundColor: '#f8fafc', borderRadius: '0.875rem', color: '#94a3b8', border: '1px solid #e2e8f0' }}>
                                                            <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>📭</div>
                                                            <p style={{ margin: 0, fontWeight: '500' }}>No hay datos de evaluación detallada guardados.</p>
                                                        </div>
                                                    )}
                                                </div>

                                            </>
                                        );
                                    })()}

                                </div>
                            ) : (
                                <div style={{ textAlign: 'center', padding: '3rem', color: '#ef4444' }}>
                                    <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>⚠️</div>
                                    No se pudo cargar el análisis o aún no se ha generado para esta grabación.
                                </div>
                            )}
                        </div>

                        <div style={{ padding: '1rem 1.5rem', borderTop: '1px solid #e2e8f0', display: 'flex', justifyContent: 'flex-end', background: '#f8fafc', flexShrink: 0 }}>
                            <button
                                onClick={() => setSelectedAnalysis(null)}
                                style={{
                                    padding: '0.6rem 1.5rem', cursor: 'pointer',
                                    border: '1px solid #cbd5e1', background: 'white', fontWeight: '600',
                                    borderRadius: '10px', color: '#475569', fontSize: '0.9rem',
                                    transition: 'all 0.2s', boxShadow: '0 1px 3px rgba(0,0,0,0.06)'
                                }}
                                onMouseEnter={e => { e.currentTarget.style.background = '#f1f5f9'; }}
                                onMouseLeave={e => { e.currentTarget.style.background = 'white'; }}
                            >Cerrar</button>
                        </div>
                    </div>
                    <style>
                        {`
                            @keyframes spin {
                                0% { transform: rotate(0deg); }
                                100% { transform: rotate(360deg); }
                            }
                        `}
                    </style>
                </div>
            )
            }

            {/* USER CREATION MODAL */}
            {
                selectedCashierForDetail && (
                    <CashierDetailModal
                        cashier={selectedCashierForDetail}
                        recordings={allRecordings}
                        onClose={() => setSelectedCashierForDetail(null)}
                    />
                )
            }



            {
                selectedBoxForDetail && (
                    <BoxDetailModal
                        box={selectedBoxForDetail}
                        recordings={allRecordings}
                        onClose={() => setSelectedBoxForDetail(null)}
                    />
                )
            }

            {
                selectedCashierForClients && (
                    <CashierClientsModal
                        cashier={selectedCashierForClients}
                        recordings={allRecordings}
                        onClose={() => setSelectedCashierForClients(null)}
                    />
                )
            }



            {
                showUserModal && (
                    <div className="modal-overlay" style={{
                        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                        backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center',
                        zIndex: 1000
                    }}>
                        <div className="modal-content" style={{
                            backgroundColor: 'white', padding: '2rem', borderRadius: 'var(--radius-lg)',
                            width: '90%', maxWidth: '500px', maxHeight: '80vh', overflowY: 'auto',
                            boxShadow: 'var(--shadow-xl)'
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                                <h2 style={{ fontSize: '1.5rem', color: 'var(--text-primary)' }}>
                                    {isEditingUser ? 'Editar Usuario' : 'Crear Nuevo Usuario'}
                                </h2>
                                <button
                                    onClick={() => {
                                        setShowUserModal(false);
                                        setIsEditingUser(false);
                                        setNewUser({
                                            id: null,
                                            username: "",
                                            password: "",
                                            confirmPassword: "",
                                            nombre: "",
                                            role: "cajero",
                                            cajaAsignada: "",
                                            estado: "activo"
                                        });
                                    }}
                                    style={{ background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer' }}
                                >
                                    ✕
                                </button>
                            </div>

                            <form onSubmit={handleCreateUser} style={{ display: 'grid', gap: '1.5rem' }}>
                                {/* Username */}
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: 'var(--text-primary)' }}>
                                        Nombre de Usuario <span style={{ color: 'red' }}>*</span>
                                    </label>
                                    <input
                                        type="text"
                                        className="form-input"
                                        value={newUser.username}
                                        onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                                        placeholder="ej: cajero2"
                                        required
                                        style={{ width: '100%', padding: '0.5rem', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}
                                    />
                                </div>

                                {/* Password */}
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: 'var(--text-primary)' }}>
                                        Contraseña {isEditingUser ? <span style={{ fontSize: '0.8rem', fontWeight: 'normal' }}>(Dejar en blanco para mantener)</span> : <span style={{ color: 'red' }}>*</span>}
                                    </label>
                                    <input
                                        type="password"
                                        className="form-input"
                                        value={newUser.password}
                                        onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                                        placeholder={isEditingUser ? "Nueva contraseña (opcional)" : "Mínimo 6 caracteres"}
                                        required={!isEditingUser}
                                        minLength={6}
                                        style={{ width: '100%', padding: '0.5rem', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}
                                    />
                                </div>

                                {/* Confirm Password */}
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: 'var(--text-primary)' }}>
                                        Confirmar Contraseña {isEditingUser ? "" : <span style={{ color: 'red' }}>*</span>}
                                    </label>
                                    <input
                                        type="password"
                                        className="form-input"
                                        value={newUser.confirmPassword}
                                        onChange={(e) => setNewUser({ ...newUser, confirmPassword: e.target.value })}
                                        placeholder="Repita la contraseña"
                                        required={!isEditingUser}
                                        minLength={6}
                                        style={{ width: '100%', padding: '0.5rem', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}
                                    />
                                </div>

                                {/* Full Name */}
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: 'var(--text-primary)' }}>
                                        Nombre Completo <span style={{ color: 'red' }}>*</span>
                                    </label>
                                    <input
                                        type="text"
                                        className="form-input"
                                        value={newUser.nombre}
                                        onChange={(e) => setNewUser({ ...newUser, nombre: e.target.value })}
                                        placeholder="ej: María García"
                                        required
                                        style={{ width: '100%', padding: '0.5rem', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}
                                    />
                                </div>

                                {/* Role */}
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: 'var(--text-primary)' }}>
                                        Rol
                                    </label>
                                    <select
                                        className="form-input"
                                        value={newUser.role}
                                        onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
                                        style={{ width: '100%', padding: '0.5rem', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}
                                    >
                                        <option value="cajero">Cajero</option>
                                        <option value="administrador">Administrador</option>
                                    </select>
                                </div>

                                {/* Status */}
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: 'var(--text-primary)' }}>
                                        Estado
                                    </label>
                                    <select
                                        className="form-input"
                                        value={newUser.estado}
                                        onChange={(e) => setNewUser({ ...newUser, estado: e.target.value })}
                                        style={{ width: '100%', padding: '0.5rem', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}
                                    >
                                        <option value="activo">Activo</option>
                                        <option value="inactivo">Inactivo</option>
                                    </select>
                                </div>

                                {/* Buttons */}
                                <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', marginTop: '1rem' }}>
                                    <button
                                        type="button"
                                        className="btn"
                                        onClick={() => {
                                            setShowUserModal(false);
                                            setIsEditingUser(false);
                                            setNewUser({
                                                id: null,
                                                username: "",
                                                password: "",
                                                confirmPassword: "",
                                                nombre: "",
                                                role: "cajero",
                                                cajaAsignada: "",
                                                estado: "activo"
                                            });
                                        }}
                                        style={{ padding: '0.5rem 1rem', cursor: 'pointer', border: '1px solid var(--border-color)', background: 'white' }}
                                    >
                                        Cancelar
                                    </button>
                                    <button
                                        type="submit"
                                        className="btn btn-primary"
                                        style={{ padding: '0.5rem 1rem', cursor: 'pointer' }}
                                    >
                                        {isEditingUser ? 'Guardar Cambios' : 'Crear Usuario'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )
            }

                        {/* SUCURSAL MODAL */}
            {showSucursalModal && (
                <div className="modal-overlay" style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center',
                    justifyContent: 'center', zIndex: 1000
                }}>
                    <div className="modal-content" style={{
                        background: 'white', padding: '2rem', borderRadius: '12px',
                        width: '90%', maxWidth: '500px', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)'
                    }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                            <h3 style={{ margin: 0, fontSize: '1.5rem', color: '#0f172a' }}>
                                {currentSucursal ? "Editar Sucursal" : "Nueva Sucursal"}
                            </h3>
                            <button onClick={() => setShowSucursalModal(false)} style={{
                                background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer', color: '#64748b'
                            }}>✕</button>
                        </div>
                        <form onSubmit={handleSaveSucursal} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            <div>
                                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Nombre de Sucursal</label>
                                <input
                                    type="text"
                                    className="form-input"
                                    value={sucursalForm.nombre}
                                    onChange={(e) => setSucursalForm({ ...sucursalForm, nombre: e.target.value })}
                                    required
                                    style={{ width: '100%', padding: '0.5rem', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}
                                />
                            </div>
                            <div>
                                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Dirección</label>
                                <textarea
                                    className="form-input"
                                    value={sucursalForm.direccion}
                                    onChange={(e) => setSucursalForm({ ...sucursalForm, direccion: e.target.value })}
                                    rows="3"
                                    style={{ width: '100%', padding: '0.5rem', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}
                                />
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
                                <input
                                    type="checkbox"
                                    id="sucursalActiva"
                                    checked={sucursalForm.activa}
                                    onChange={(e) => setSucursalForm({ ...sucursalForm, activa: e.target.checked })}
                                />
                                <label htmlFor="sucursalActiva" style={{ margin: 0, cursor: 'pointer', fontWeight: '600' }}>Sucursal Activa</label>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1.5rem' }}>
                                <button type="button" className="btn btn-outline" onClick={() => setShowSucursalModal(false)} style={{ padding: '0.5rem 1rem', borderRadius: '8px', border: '1px solid #e2e8f0', background: 'white', cursor: 'pointer' }}>
                                    Cancelar
                                </button>
                                <button type="submit" className="btn btn-primary" style={{ padding: '0.5rem 1rem', borderRadius: '8px', background: '#ea580c', color: 'white', border: 'none', cursor: 'pointer', fontWeight: '600' }}>
                                    Guardar Sucursal
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* CONTACT MODAL */}
            {
                showContactModal && (
                    <div className="modal-overlay" style={{
                        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                        backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center',
                        zIndex: 1000
                    }}>
                        <div className="modal-content" style={{
                            backgroundColor: 'white', padding: '2rem', borderRadius: 'var(--radius-lg)',
                            width: '90%', maxWidth: '500px', maxHeight: '80vh', overflowY: 'auto',
                            boxShadow: 'var(--shadow-xl)'
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                                <h2 style={{ fontSize: '1.5rem', color: 'var(--text-primary)' }}>
                                    {currentContact ? 'Editar Contacto' : 'Nuevo Contacto'}
                                </h2>
                                <button
                                    onClick={() => setShowContactModal(false)}
                                    style={{ background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer' }}
                                >
                                    ✕
                                </button>
                            </div>

                            <form onSubmit={handleCreateContact} style={{ display: 'grid', gap: '1rem' }}>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Nombre *</label>
                                    <input
                                        type="text"
                                        className="form-input"
                                        value={contactForm.nombre}
                                        onChange={(e) => setContactForm({ ...contactForm, nombre: e.target.value })}
                                        required
                                        style={{ width: '100%' }}
                                    />
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Apellido *</label>
                                    <input
                                        type="text"
                                        className="form-input"
                                        value={contactForm.apellido}
                                        onChange={(e) => setContactForm({ ...contactForm, apellido: e.target.value })}
                                        required
                                        style={{ width: '100%' }}
                                    />
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Email</label>
                                    <input
                                        type="email"
                                        className="form-input"
                                        value={contactForm.email}
                                        onChange={(e) => setContactForm({ ...contactForm, email: e.target.value })}
                                        style={{ width: '100%' }}
                                    />
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Teléfono</label>
                                    <input
                                        type="tel"
                                        className="form-input"
                                        value={contactForm.telefono}
                                        onChange={(e) => setContactForm({ ...contactForm, telefono: e.target.value })}
                                        style={{ width: '100%' }}
                                    />
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Dirección</label>
                                    <textarea
                                        className="form-input"
                                        value={contactForm.direccion}
                                        onChange={(e) => setContactForm({ ...contactForm, direccion: e.target.value })}
                                        style={{ width: '100%', minHeight: '60px' }}
                                    />
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Rol</label>
                                    <select
                                        className="form-input"
                                        value={contactForm.rol || "Cajero"}
                                        onChange={(e) => setContactForm({ ...contactForm, rol: e.target.value })}
                                        style={{ width: '100%', padding: '0.5rem', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}
                                    >
                                        <option value="Cajero">Cajero</option>
                                        <option value="Administrador">Administrador</option>
                                    </select>
                                </div>
                                {contactForm.rol === 'Cajero' && (
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Sucursal Asignada</label>
                                        <select
                                            className="form-input"
                                            value={contactForm.sucursal_id || ""}
                                            onChange={(e) => setContactForm({ ...contactForm, sucursal_id: e.target.value })}
                                            required
                                            style={{ width: '100%', padding: '0.5rem', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}
                                        >
                                            <option value="">-- Seleccionar Sucursal --</option>
                                            {sucursales.map(s => (
                                                <option key={s.id} value={s.id}>{s.nombre}</option>
                                            ))}
                                        </select>
                                    </div>
                                )}
                                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
                                    <button type="button" className="btn" onClick={() => setShowContactModal(false)}>Cancelar</button>
                                    <button type="submit" className="btn btn-primary">Guardar</button>
                                </div>
                            </form>
                        </div>
                    </div>
                )
            }

            {/* CREATE USER FROM CONTACT MODAL */}
            {
                showCreateUserFromContactModal && (
                    <div className="modal-overlay" style={{
                        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                        backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center',
                        zIndex: 1000
                    }}>
                        <div className="modal-content" style={{
                            backgroundColor: 'white', padding: '2rem', borderRadius: 'var(--radius-lg)',
                            width: '90%', maxWidth: '500px', maxHeight: '80vh', overflowY: 'auto',
                            boxShadow: 'var(--shadow-xl)'
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                                <h2 style={{ fontSize: '1.5rem', color: 'var(--text-primary)' }}>Crear Usuario para {currentContact?.nombre}</h2>
                                <button
                                    onClick={() => setShowCreateUserFromContactModal(false)}
                                    style={{ background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer' }}
                                >
                                    ✕
                                </button>
                            </div>

                            <form onSubmit={handleCreateUserFromContact} style={{ display: 'grid', gap: '1.5rem' }}>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Nombre de Usuario *</label>
                                    <input
                                        type="text"
                                        className="form-input"
                                        value={userFromContactForm.username}
                                        onChange={(e) => setUserFromContactForm({ ...userFromContactForm, username: e.target.value })}
                                        required
                                        style={{ width: '100%' }}
                                    />
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Contraseña *</label>
                                    <input
                                        type="password"
                                        className="form-input"
                                        value={userFromContactForm.password}
                                        onChange={(e) => setUserFromContactForm({ ...userFromContactForm, password: e.target.value })}
                                        required
                                        minLength={6}
                                        style={{ width: '100%' }}
                                    />
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Confirmar Contraseña *</label>
                                    <input
                                        type="password"
                                        className="form-input"
                                        value={userFromContactForm.confirmPassword}
                                        onChange={(e) => setUserFromContactForm({ ...userFromContactForm, confirmPassword: e.target.value })}
                                        required
                                        minLength={6}
                                        style={{ width: '100%' }}
                                    />
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Rol</label>
                                    <select
                                        className="form-input"
                                        value={userFromContactForm.role}
                                        onChange={(e) => setUserFromContactForm({ ...userFromContactForm, role: e.target.value })}
                                        style={{ width: '100%', backgroundColor: '#f1f5f9', cursor: 'not-allowed' }}
                                        disabled
                                    >
                                        <option value="cajero">Cajero</option>
                                        <option value="administrador">Administrador</option>
                                    </select>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
                                    <button type="button" className="btn" onClick={() => setShowCreateUserFromContactModal(false)}>Cancelar</button>
                                    <button type="submit" className="btn btn-primary">Crear Usuario</button>
                                </div>
                            </form>
                        </div>
                    </div>
                )
            }



            {/* Modal de Cajas */}
            {
                showBoxModal && (
                    <div className="modal-overlay">
                        <div className="modal-content">
                            <div className="modal-header">
                                <h2>{currentBox ? "Editar Caja" : "Nueva Caja"}</h2>
                                <button className="close-btn" onClick={() => setShowBoxModal(false)}>×</button>
                            </div>
                            <form onSubmit={handleCreateBox}>
                                <h4 style={{ fontSize: '0.9rem', color: '#64748b', fontWeight: '600', marginBottom: '0.75rem', borderBottom: '1px solid #e2e8f0', paddingBottom: '0.25rem' }}>Información General</h4>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                                    <div className="form-group">
                                        <label>Nombre de la Caja</label>
                                        <input
                                            type="text"
                                            className="form-input"
                                            value={boxForm.name}
                                            onChange={(e) => setBoxForm({ ...boxForm, name: e.target.value })}
                                            required
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label>Sucursal</label>
                                        <select
                                            className="form-input"
                                            value={boxForm.sucursal_id}
                                            onChange={(e) => setBoxForm({ ...boxForm, sucursal_id: e.target.value })}
                                            required
                                        >
                                            <option value="">-- Seleccionar Sucursal --</option>
                                            {sucursales.map(s => (
                                                <option key={s.id} value={s.id}>{s.nombre}</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                                    <div className="form-group">
                                        <label>Cajero Asignado</label>
                                        <select
                                            className="form-input"
                                            value={boxForm.assignedContactId}
                                            onChange={(e) => setBoxForm({ ...boxForm, assignedContactId: e.target.value })}
                                        >
                                            <option value="">-- Sin asignar --</option>
                                            {contacts.filter(contact => {
                                                const isAssigned = boxConfigs.some(b => b.assignedContactId === contact.id && b.id !== (currentBox?.id));
                                                return !isAssigned;
                                            }).map(contact => (
                                                <option key={contact.id} value={contact.id}>
                                                    {contact.nombre} {contact.apellido}
                                                </option>
                                            ))}
                                        </select>
                                    </div>
                                    <div className="form-group">
                                        <label>Estado Operativo</label>
                                        <select
                                            className="form-input"
                                            value={boxForm.estado_operativo}
                                            onChange={(e) => setBoxForm({ ...boxForm, estado_operativo: e.target.value })}
                                        >
                                            <option value="Operativa">Operativa</option>
                                            <option value="Mantenimiento">En Mantenimiento</option>
                                            <option value="Fuera de Servicio">Fuera de Servicio</option>
                                        </select>
                                    </div>
                                </div>
                                <div className="form-group" style={{ marginBottom: '1.5rem' }}>
                                    <label>Motivo o Factor (Opcional)</label>
                                    <textarea
                                        className="form-input"
                                        value={boxForm.motivo_estado}
                                        onChange={(e) => setBoxForm({ ...boxForm, motivo_estado: e.target.value })}
                                        placeholder="Ej: Cable desconectado, sistema lento..."
                                        rows="2"
                                    />
                                </div>
                                
                                <h4 style={{ fontSize: '0.9rem', color: '#64748b', fontWeight: '600', marginTop: '1.5rem', marginBottom: '0.5rem', borderBottom: '1px solid #e2e8f0', paddingBottom: '0.25rem' }}>Horarios y Grabación</h4>

                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                                    <div className="form-group">
                                        <label style={{ fontSize: '0.85rem', fontWeight: '700' }}>Turno Mañana (Inicio)</label>
                                        <input
                                            type="time"
                                            className="form-input"
                                            value={boxForm.turno_manana_inicio?.slice(0, 5) || "07:30"}
                                            onChange={(e) => setBoxForm({ ...boxForm, turno_manana_inicio: e.target.value + ":00" })}
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label style={{ fontSize: '0.85rem', fontWeight: '700' }}>Turno Mañana (Fin)</label>
                                        <input
                                            type="time"
                                            className="form-input"
                                            value={boxForm.turno_manana_fin?.slice(0, 5) || "12:00"}
                                            onChange={(e) => setBoxForm({ ...boxForm, turno_manana_fin: e.target.value + ":00" })}
                                        />
                                    </div>
                                </div>

                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                                    <div className="form-group">
                                        <label style={{ fontSize: '0.85rem', fontWeight: '700' }}>Turno Tarde (Inicio)</label>
                                        <input
                                            type="time"
                                            className="form-input"
                                            value={boxForm.turno_tarde_inicio?.slice(0, 5) || "16:00"}
                                            onChange={(e) => setBoxForm({ ...boxForm, turno_tarde_inicio: e.target.value + ":00" })}
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label style={{ fontSize: '0.85rem', fontWeight: '700' }}>Turno Tarde (Fin)</label>
                                        <input
                                            type="time"
                                            className="form-input"
                                            value={boxForm.turno_tarde_fin?.slice(0, 5) || "19:00"}
                                            onChange={(e) => setBoxForm({ ...boxForm, turno_tarde_fin: e.target.value + ":00" })}
                                        />
                                    </div>
                                </div>

                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.25rem' }}>
                                    <div className="form-group">
                                        <label style={{ fontSize: '0.85rem', fontWeight: '700' }}>Control de Grabación (Desktop)</label>
                                        <select
                                            className="form-input"
                                            value={
                                                !boxForm.grabacion_habilitada 
                                                    ? "apagado" 
                                                    : boxForm.en_pausa 
                                                        ? "pausa" 
                                                        : "grabando"
                                            }
                                            onChange={(e) => {
                                                const val = e.target.value;
                                                if (val === "grabando") {
                                                    setBoxForm({ ...boxForm, grabacion_habilitada: true, en_pausa: false });
                                                } else if (val === "pausa") {
                                                    setBoxForm({ ...boxForm, grabacion_habilitada: true, en_pausa: true });
                                                } else if (val === "apagado") {
                                                    setBoxForm({ ...boxForm, grabacion_habilitada: false, en_pausa: false });
                                                }
                                            }}
                                        >
                                            <option value="grabando">Habilitada (Activa)</option>
                                            <option value="pausa">Pausar Grabación</option>
                                            <option value="apagado">Deshabilitar Grabación</option>
                                        </select>
                                    </div>

                                    <div className="form-group">
                                        <label style={{ fontSize: '0.85rem', fontWeight: '700' }}>Tiempo de Grabación (Minutos)</label>
                                        <select
                                            className="form-input"
                                            value={boxForm.duracion_segmento_minutos}
                                            onChange={(e) => setBoxForm({ ...boxForm, duracion_segmento_minutos: parseInt(e.target.value) || 10 })}
                                        >
                                            <option value={10}>10 Minutos</option>
                                            <option value={20}>20 Minutos</option>
                                            <option value={30}>30 Minutos</option>
                                        </select>
                                        <small style={{ color: '#64748b', fontSize: '0.75rem', marginTop: '0.25rem', display: 'block' }}>
                                            Cada cuántos minutos se cortará el audio.
                                        </small>
                                    </div>
                                </div>

                                <div className="form-group" style={{ marginBottom: '1.25rem' }}>
                                    <label style={{ fontSize: '0.85rem', fontWeight: '700' }}>Micrófono Asignado</label>
                                    {boxForm.lista_microfonos && boxForm.lista_microfonos.length > 0 ? (
                                        <select
                                            className="form-input"
                                            value={boxForm.microfono_asignado || ""}
                                            onChange={(e) => setBoxForm({ ...boxForm, microfono_asignado: e.target.value })}
                                        >
                                            <option value="">-- Predeterminado / Ninguno --</option>
                                            {boxForm.lista_microfonos.map((mic, idx) => (
                                                <option key={idx} value={mic}>{mic}</option>
                                            ))}
                                        </select>
                                    ) : (
                                        <input
                                            type="text"
                                            className="form-input"
                                            placeholder="Nombre del micrófono (opcional)"
                                            value={boxForm.microfono_asignado || ""}
                                            onChange={(e) => setBoxForm({ ...boxForm, microfono_asignado: e.target.value })}
                                        />
                                    )}
                                </div>

                                <div className="modal-actions">
                                    <button type="button" className="btn btn-secondary" onClick={() => setShowBoxModal(false)}>
                                        Cancelar
                                    </button>
                                    <button type="submit" className="btn btn-primary">
                                        {currentBox ? "Guardar Cambios" : "Crear Caja"}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )
            }
        </div >
    );
}
