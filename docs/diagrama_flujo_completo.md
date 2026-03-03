# 🔄 Diagrama de Flujo Completo - JobFit Agent

Este documento contiene el diagrama de flujo detallado y completo del agente JobFit, mostrando todos los procesos, decisiones y componentes del sistema.

---

## 🎯 Flujo Principal del Agente

### 🚀 Vista General del Sistema

```mermaid
graph TB
    %% Inicio del sistema
    START([🚀 Inicio JobFit Agent]) --> LAUNCHER[🔧 start_jobfit.bat]
    LAUNCHER --> VENV[⚙️ Activar entorno virtual]
    VENV --> DEPS[📦 Instalar dependencias]
    DEPS --> UI_START[🌐 Iniciar Gradio UI]
    UI_START --> READY[✅ Sistema listo - Puerto 7860]
    
    %% Entrada del usuario
    READY --> USER_INPUT{👤 ¿Qué hace el usuario?}
    
    %% Opción 1: Solo auditar oferta
    USER_INPUT -->|📊 Auditar Oferta| AUDIT_FLOW[🔍 Flujo de Auditoría]
    
    %% Opción 2: Matching completo
    USER_INPUT -->|🎯 Adaptar CV| MATCH_FLOW[📊 Flujo de Matching]
    
    %% Flujo de Auditoría
    AUDIT_FLOW --> INPUT_JOB[📝 Ingresar oferta]
    INPUT_JOB --> JOB_TYPE{🔗 ¿Tipo de entrada?}
    
    JOB_TYPE -->|URL| SCRAPE[🌐 Web Scraping]
    JOB_TYPE -->|Texto| DIRECT_TEXT[📝 Procesamiento directo]
    
    SCRAPE --> CLEAN_HTML[🧹 Limpiar HTML]
    DIRECT_TEXT --> PARSE_JOB[📋 Parsear oferta]
    CLEAN_HTML --> PARSE_JOB
    
    PARSE_JOB --> AI_CHECK{🤖 ¿LM Studio disponible?}
    AI_CHECK -->|Sí| AI_EXTRACT[🧠 Extracción con IA]
    AI_CHECK -->|No| RULES_EXTRACT[📏 Extracción con reglas]
    
    AI_EXTRACT --> SCORE_REALISM[📊 Scoring de realismo]
    RULES_EXTRACT --> SCORE_REALISM
    
    SCORE_REALISM --> AUDIT_RESULT[📈 Mostrar resultado auditoría]
    AUDIT_RESULT --> END_AUDIT[✅ Fin auditoría]
    
    %% Flujo de Matching
    MATCH_FLOW --> UPLOAD_CV[📄 Subir CV]
    UPLOAD_CV --> CV_FORMAT{📁 ¿Formato CV?}
    
    CV_FORMAT -->|PDF| PDF_PARSE[📑 Parsear PDF]
    CV_FORMAT -->|DOCX| DOCX_PARSE[📋 Parsear DOCX]
    CV_FORMAT -->|TXT| TXT_PARSE[📝 Parsear TXT]
    
    PDF_PARSE --> CV_CLEAN[🧹 Limpiar texto CV]
    DOCX_PARSE --> CV_CLEAN
    TXT_PARSE --> CV_CLEAN
    
    CV_CLEAN --> JOB_INPUT[📝 Ingresar oferta trabajo]
    JOB_INPUT --> PARSE_JOB_MATCH[📋 Parsear oferta]
    
    PARSE_JOB_MATCH --> AI_CHECK2{🤖 ¿LM Studio disponible?}
    AI_CHECK2 -->|Sí| AI_EXTRACT2[🧠 Extracción IA]
    AI_CHECK2 -->|No| RULES_EXTRACT2[📏 Extracción reglas]
    
    AI_EXTRACT2 --> SEMANTIC_MATCH[🎯 Análisis semántico]
    RULES_EXTRACT2 --> SEMANTIC_MATCH
    
    SEMANTIC_MATCH --> LOAD_EMBEDDINGS[📊 Cargar modelo embeddings]
    LOAD_EMBEDDINGS --> CALCULATE_SIM[🔍 Calcular similitud]
    CALCULATE_SIM --> MATCH_SCORE[📈 Score de matching]
    
    MATCH_SCORE --> SHOW_ANALYSIS[📊 Mostrar análisis]
    SHOW_ANALYSIS --> USER_CHOICE{👤 ¿Generar CV adaptado?}
    
    USER_CHOICE -->|No| ANALYSIS_ONLY[📊 Solo mostrar análisis]
    USER_CHOICE -->|Sí| ADAPT_CV[📝 Adaptar CV]
    
    %% Adaptación de CV
    ADAPT_CV --> ATS_OPT[⚡ Optimizador ATS]
    ATS_OPT --> NO_STUFF[🚫 NO keyword stuffing]
    NO_STUFF --> PRESERVE_ORIG[✨ Preservar contenido original]
    PRESERVE_ORIG --> CLEAN_FORMAT[🧹 Formato limpio]
    CLEAN_FORMAT --> GENERATE_TXT[📝 Generar TXT]
    GENERATE_TXT --> GENERATE_DOCX[📋 Generar DOCX]
    GENERATE_DOCX --> REMOVE_EMOJIS[🚫 Eliminar emojis]
    REMOVE_EMOJIS --> SAVE_FILES[💾 Guardar archivos]
    SAVE_FILES --> AUTO_DOWNLOAD[⬇️ Descarga automática]
    
    ANALYSIS_ONLY --> FINAL_RESULT[📈 Resultado final]
    AUTO_DOWNLOAD --> FINAL_RESULT
    
    FINAL_RESULT --> LOG_ACTIVITY[📝 Log actividad]
    LOG_ACTIVITY --> END_PROCESS[✅ Proceso completado]
    END_AUDIT --> END_PROCESS
    
    END_PROCESS --> READY
    
    %% Estilos
    classDef startEnd fill:#e8f5e8,stroke:#4caf50,stroke-width:3px
    classDef process fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    classDef decision fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    classDef ai fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px
    classDef error fill:#ffebee,stroke:#f44336,stroke-width:2px
    classDef success fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    
    class START,READY,END_PROCESS startEnd
    class LAUNCHER,VENV,DEPS,UI_START,UPLOAD_CV,CV_CLEAN,ADAPT_CV process
    class USER_INPUT,JOB_TYPE,CV_FORMAT,AI_CHECK,AI_CHECK2,USER_CHOICE decision
    class AI_EXTRACT,AI_EXTRACT2,SEMANTIC_MATCH ai
    class FINAL_RESULT,AUTO_DOWNLOAD success
```

---

## 🔍 Flujo Detallado por Componente

### 📊 1. Análisis Semántico Detallado

```mermaid
graph TD
    START_SEM[🎯 Inicio análisis semántico] --> LOAD_MODEL[📊 Cargar all-MiniLM-L6-v2]
    LOAD_MODEL --> PREPARE_CV[📄 Preparar texto CV]
    PREPARE_CV --> PREPARE_JOB[📋 Preparar requisitos]
    
    PREPARE_JOB --> EXTRACT_REQ[🔍 Extraer requisitos individuales]
    EXTRACT_REQ --> REQ_LOOP{🔄 Para cada requisito}
    
    REQ_LOOP --> EMBED_REQ[🧠 Embedding requisito]
    EMBED_REQ --> EMBED_CV[🧠 Embedding CV completo]
    EMBED_CV --> CALC_SIM[📊 Calcular similitud coseno]
    
    CALC_SIM --> THRESHOLD{🎯 ¿Similitud > 0.10?}
    THRESHOLD -->|Sí| COVERED[✅ Requisito CUBIERTO]
    THRESHOLD -->|No| MISSING[❌ Requisito FALTANTE]
    
    COVERED --> PRIORITY_CHECK{🔴 ¿Es obligatorio?}
    MISSING --> PRIORITY_CHECK2{🟡 ¿Es deseable?}
    
    PRIORITY_CHECK -->|Sí| HIGH_WEIGHT[📈 Peso alto en score]
    PRIORITY_CHECK -->|No| MED_WEIGHT[📊 Peso medio en score]
    PRIORITY_CHECK2 -->|Sí| LOW_WEIGHT[📉 Peso bajo en score]
    PRIORITY_CHECK2 -->|No| MIN_WEIGHT[📉 Peso mínimo en score]
    
    HIGH_WEIGHT --> UPDATE_SCORE[📊 Actualizar score total]
    MED_WEIGHT --> UPDATE_SCORE
    LOW_WEIGHT --> UPDATE_SCORE
    MIN_WEIGHT --> UPDATE_SCORE
    
    UPDATE_SCORE --> MORE_REQ{🔄 ¿Más requisitos?}
    MORE_REQ -->|Sí| REQ_LOOP
    MORE_REQ -->|No| FINAL_CALC[📈 Cálculo final]
    
    FINAL_CALC --> GENERATE_REPORT[📋 Generar reporte]
    GENERATE_REPORT --> RETURN_ANALYSIS[🎯 Retornar análisis]
    
    %% Estilos
    classDef start fill:#e8f5e8
    classDef process fill:#e3f2fd
    classDef decision fill:#fff3e0
    classDef success fill:#c8e6c9
    classDef warning fill:#ffebee
    
    class START_SEM start
    class COVERED success
    class MISSING warning
    class RETURN_ANALYSIS success
```

### 🤖 2. Integración LM Studio Detallada

```mermaid
graph TD
    LM_START[🤖 Inicio LM Studio Client] --> CHECK_CONN[🔍 Verificar conexión]
    CHECK_CONN --> PING_SERVER{🏓 ¿Servidor responde?}
    
    PING_SERVER -->|No| FALLBACK_MODE[⚠️ Activar modo fallback]
    PING_SERVER -->|Sí| LIST_MODELS[📋 Listar modelos disponibles]
    
    LIST_MODELS --> MODEL_CHECK{🧠 Conectar al servidor}
    MODEL_CHECK -->|Sí| USE_LLAMA3[✅ Usando LM Studio]
    MODEL_CHECK -->|Sí| USE_MIXTRAL[✅ Usando LM Studio]
    MODEL_CHECK -->|No| INSTALL_MODEL[📥 Modelo no disponible]
    
    USE_LLAMA3 --> SEND_PROMPT[📤 Enviar prompt]
    USE_MIXTRAL --> SEND_PROMPT
    INSTALL_MODEL --> SEND_PROMPT
    
    SEND_PROMPT --> WAIT_RESPONSE[⏳ Esperar respuesta]
    WAIT_RESPONSE --> PARSE_JSON[🔍 Parsear JSON]
    
    PARSE_JSON --> VALID_JSON{✅ ¿JSON válido?}
    VALID_JSON -->|No| RETRY_PARSE[🔄 Reintentar parsing]
    VALID_JSON -->|Sí| EXTRACT_DATA[📊 Extraer datos]
    
    RETRY_PARSE --> RETRY_COUNT{🔢 ¿Intentos < 3?}
    RETRY_COUNT -->|Sí| PARSE_JSON
    RETRY_COUNT -->|No| FALLBACK_PARSE[📏 Usar fallback]
    
    EXTRACT_DATA --> VALIDATE_DATA[✅ Validar datos]
    VALIDATE_DATA --> RETURN_AI[🧠 Retornar resultado IA]
    
    FALLBACK_MODE --> RULES_ENGINE[📏 Motor de reglas]
    FALLBACK_PARSE --> RULES_ENGINE
    RULES_ENGINE --> BASIC_EXTRACT[📊 Extracción básica]
    BASIC_EXTRACT --> RETURN_FALLBACK[⚠️ Retornar resultado básico]
    
    %% Estilos
    classDef ai fill:#f3e5f5
    classDef success fill:#c8e6c9
    classDef warning fill:#fff3e0
    classDef error fill:#ffebee
    
    class LM_START,USE_LM USE_LM,USE_LM_FALLBACK ai
    class RETURN_AI success
    class FALLBACK_MODE,RETURN_FALLBACK warning
    class RETRY_PARSE error
```

### 📝 3. Generación de CV Optimizado

```mermaid
graph TD
    CV_START[📝 Inicio adaptación CV] --> RECEIVE_DATA[📥 Recibir CV + análisis]
    RECEIVE_DATA --> ATS_OPT[⚡ ATSOptimizer]
    
    ATS_OPT --> ANTI_STUFF[🚫 Verificar NO keyword stuffing]
    ANTI_STUFF --> PRESERVE[✨ Preservar contenido original]
    PRESERVE --> NATURAL_OPT[🌿 Optimización natural]
    
    NATURAL_OPT --> CLEAN_TEXT[🧹 Limpiar formato]
    CLEAN_TEXT --> REMOVE_EMOJI_CONTACT[📧 Limpiar emojis contacto]
    REMOVE_EMOJI_CONTACT --> STRUCTURE[📊 Estructurar secciones]
    
    STRUCTURE --> GEN_TXT[📄 Generar archivo TXT]
    GEN_TXT --> GEN_DOCX[📋 Generar archivo DOCX]
    
    GEN_DOCX --> CORP_FORMAT[🎨 Aplicar formato corporativo]
    CORP_FORMAT --> CLEAN_FINAL[🧹 Limpieza final]
    CLEAN_FINAL --> SAVE_EXPORTS[💾 Guardar en exports/]
    
    SAVE_EXPORTS --> AUTO_DL[⬇️ Preparar descarga automática]
    AUTO_DL --> SUCCESS_CV[✅ CV optimizado listo]
    
    %% Anti-patterns que se evitan
    ANTI_PATTERNS[❌ Anti-patterns evitados:]
    FAKE_COMP[🚫 Competencias falsas]
    KEYWORD_STUFF[🚫 Keyword stuffing]
    FAKE_EXP[🚫 Experiencia inventada]
    
    ANTI_STUFF -.-> ANTI_PATTERNS
    ANTI_PATTERNS -.-> FAKE_COMP
    ANTI_PATTERNS -.-> KEYWORD_STUFF
    ANTI_PATTERNS -.-> FAKE_EXP
    
    %% Estilos
    classDef good fill:#c8e6c9
    classDef process fill:#e3f2fd
    classDef avoid fill:#ffebee
    
    class NATURAL_OPT,PRESERVE,SUCCESS_CV good
    class CV_START,GEN_TXT,GEN_DOCX process
    class FAKE_COMP,KEYWORD_STUFF,FAKE_EXP avoid
```

---

## 🔧 Flujos de Error y Recuperación

### ⚠️ Gestión de Errores del Sistema

```mermaid
graph TD
    ERROR_START[❌ Error detectado] --> ERROR_TYPE{🔍 ¿Tipo de error?}
    
    ERROR_TYPE -->|Archivo| FILE_ERROR[📁 Error de archivo]
    ERROR_TYPE -->|Red| NETWORK_ERROR[🌐 Error de red]
    ERROR_TYPE -->|IA| AI_ERROR[🤖 Error de IA]
    ERROR_TYPE -->|Parsing| PARSE_ERROR[📋 Error de parsing]
    
    FILE_ERROR --> FILE_FIX{🔧 ¿Se puede reparar?}
    FILE_FIX -->|Sí| RETRY_FILE[🔄 Reintentar lectura]
    FILE_FIX -->|No| FILE_FALLBACK[📄 Usar formato alternativo]
    
    NETWORK_ERROR --> NET_RETRY[🔄 Reintentar conexión]
    NET_RETRY --> NET_COUNT{🔢 ¿Intentos < 3?}
    NET_COUNT -->|Sí| NET_RETRY
    NET_COUNT -->|No| OFFLINE_MODE[🔌 Modo offline]
    
    AI_ERROR --> AI_FALLBACK[📏 Usar reglas internas]
    PARSE_ERROR --> MANUAL_PARSE[🔧 Parsing manual]
    
    RETRY_FILE --> SUCCESS_RECOVER[✅ Recuperación exitosa]
    FILE_FALLBACK --> SUCCESS_RECOVER
    OFFLINE_MODE --> LIMITED_FUNC[⚠️ Funcionalidad limitada]
    AI_FALLBACK --> LIMITED_FUNC
    MANUAL_PARSE --> SUCCESS_RECOVER
    
    SUCCESS_RECOVER --> LOG_RECOVERY[📝 Log recuperación]
    LIMITED_FUNC --> LOG_LIMITATION[📝 Log limitación]
    
    LOG_RECOVERY --> CONTINUE[▶️ Continuar proceso]
    LOG_LIMITATION --> CONTINUE
    
    CONTINUE --> NOTIFY_USER[📢 Notificar usuario]
    NOTIFY_USER --> END_ERROR[✅ Error manejado]
    
    %% Estilos
    classDef error fill:#ffebee
    classDef warning fill:#fff3e0
    classDef success fill:#c8e6c9
    classDef process fill:#e3f2fd
    
    class ERROR_START,FILE_ERROR,NETWORK_ERROR,AI_ERROR,PARSE_ERROR error
    class LIMITED_FUNC,OFFLINE_MODE warning
    class SUCCESS_RECOVER,END_ERROR success
    class RETRY_FILE,NET_RETRY,CONTINUE process
```

---

## 📊 Métricas y Monitoring

### 📈 Flujo de Monitoreo del Sistema

```mermaid
graph TD
    MONITOR_START[📊 Inicio monitoreo] --> COLLECT_METRICS[📈 Recopilar métricas]
    
    COLLECT_METRICS --> TIME_METRICS[⏱️ Tiempos de respuesta]
    COLLECT_METRICS --> MEM_METRICS[💾 Uso de memoria]
    COLLECT_METRICS --> SUCCESS_METRICS[✅ Tasa de éxito]
    COLLECT_METRICS --> ERROR_METRICS[❌ Tasa de errores]
    
    TIME_METRICS --> LOG_TIMES[📝 Log tiempos]
    MEM_METRICS --> LOG_MEMORY[📝 Log memoria]
    SUCCESS_METRICS --> LOG_SUCCESS[📝 Log éxitos]
    ERROR_METRICS --> LOG_ERRORS[📝 Log errores]
    
    LOG_TIMES --> ANALYZE[📊 Análisis automático]
    LOG_MEMORY --> ANALYZE
    LOG_SUCCESS --> ANALYZE
    LOG_ERRORS --> ANALYZE
    
    ANALYZE --> THRESHOLD_CHECK{🎯 ¿Umbrales OK?}
    
    THRESHOLD_CHECK -->|Sí| NORMAL_OPS[✅ Operación normal]
    THRESHOLD_CHECK -->|No| ALERT_SYSTEM[🚨 Sistema de alertas]
    
    ALERT_SYSTEM --> AUTO_RECOVERY[🔧 Recuperación automática]
    AUTO_RECOVERY --> RECOVERY_SUCCESS{✅ ¿Recuperación OK?}
    
    RECOVERY_SUCCESS -->|Sí| NORMAL_OPS
    RECOVERY_SUCCESS -->|No| MANUAL_INT[👤 Intervención manual]
    
    NORMAL_OPS --> WAIT_INTERVAL[⏳ Esperar intervalo]
    MANUAL_INT --> WAIT_INTERVAL
    
    WAIT_INTERVAL --> COLLECT_METRICS
    
    %% Estilos
    classDef monitor fill:#e8f5e8
    classDef metrics fill:#e3f2fd
    classDef alert fill:#ffebee
    classDef success fill:#c8e6c9
    
    class MONITOR_START,COLLECT_METRICS monitor
    class TIME_METRICS,MEM_METRICS,SUCCESS_METRICS,ERROR_METRICS metrics
    class ALERT_SYSTEM,MANUAL_INT alert
    class NORMAL_OPS,RECOVERY_SUCCESS success
```

---

## 🎯 Casos de Uso Específicos

### 👤 Caso 1: Usuario Nuevo

```mermaid
journey
    title Primer uso de JobFit Agent
    section Instalación
      Descargar código: 5: Usuario
      Ejecutar start_jobfit.bat: 3: Usuario
      Esperar instalación: 2: Sistema
      Ver interfaz web: 5: Usuario
    section Primera prueba
      Subir CV de ejemplo: 4: Usuario
      Copiar oferta de trabajo: 4: Usuario
      Ver análisis inicial: 5: Usuario
      Descargar CV adaptado: 5: Usuario
    section Aprendizaje
      Leer manual de usuario: 3: Usuario
      Probar diferentes ofertas: 4: Usuario
      Optimizar CV original: 5: Usuario
```

### 🏢 Caso 2: Recruiter Profesional

```mermaid
journey
    title Recruiter evaluando candidatos
    section Preparación
      Configurar criterios: 4: Recruiter
      Crear oferta estándar: 4: Recruiter
      Auditar realismo oferta: 5: Sistema
    section Evaluación masiva
      Recibir CVs candidatos: 3: Recruiter
      Procesar lote de CVs: 5: Sistema
      Revisar scores de matching: 4: Recruiter
      Filtrar top candidatos: 5: Recruiter
    section Toma de decisiones
      Analizar gaps principales: 4: Sistema
      Priorizar entrevistas: 5: Recruiter
      Contactar candidatos: 5: Recruiter
```

---

<div align="center">

**🎯 Diagrama Completo del Agente JobFit**

*Sistema inteligente de matching CV-Trabajo con IA local*

📚 [Manual de Usuario](manual_usuario.md) | 🏗️ [Arquitectura](architecture.md) | 🧪 [Testing](testing_guide.md)

</div>