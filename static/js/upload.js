const uploadForm = document.getElementById('uploadForm');
const fileInput = document.getElementById('archivo');
const dropZone = document.getElementById('dropZone');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const removeFileBtn = document.getElementById('removeFile');
const submitBtn = document.getElementById('submitBtn');
const progressContainer = document.querySelector('.progress-container');
const progressBar = document.querySelector('.progress-bar');
const logoutBtn = document.getElementById('logoutBtn');

// Variables para control de progreso
let progressInterval = null;
let safetyTimeout = null;
let formSubmitted = false;

// Clase para manejar mensajes flash
class FlashMessagesManager {
    constructor() {
        this.container = document.getElementById('flashMessages');
        this.persistentMessages = new Set(); // Para rastrear mensajes persistentes
    }

    // Crear nuevo mensaje
    create(message, type = 'info', autoDismiss = true, persistent = false) {
        // Si no es persistente, limpiar solo mensajes no persistentes
        if (!persistent) {
            this.clearNonPersistent();
        }

        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show flash-message`;
        alertDiv.setAttribute('data-type', type);
        if (autoDismiss && !persistent) {
            alertDiv.setAttribute('data-auto-dismiss', 'true');
        }
        if (persistent) {
            alertDiv.setAttribute('data-persistent', 'true');
            this.persistentMessages.add(alertDiv);
        }

        const iconClass = this.getIconClass(type);
        alertDiv.innerHTML = `
            <i class="bi bi-${iconClass} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        this.container.appendChild(alertDiv);

        // Configurar auto-dismiss solo si no es persistente
        if (autoDismiss && !persistent) {
            const delay = type === 'danger' ? 4000 : 5000;
            this.setupAutoDismiss(alertDiv, delay);
        }

        // Animar entrada
        setTimeout(() => {
            alertDiv.classList.add('show');
        }, 10);

        return alertDiv;
    }

    // Obtener clase de icono según el tipo
    getIconClass(type) {
        const icons = {
            'success': 'check-circle',
            'danger': 'exclamation-triangle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    // Configurar auto-dismiss para un mensaje
    setupAutoDismiss(alertElement, delay = 5000) {
        // Para mensajes de advertencia (warning), usar 4 segundos
        if (alertElement.getAttribute('data-type') === 'warning') {
            delay = 4000;
        }
        // Para mensajes de error (danger), usar 4 segundos
        else if (alertElement.getAttribute('data-type') === 'danger') {
            delay = 4000;
        }
        
        const timer = setTimeout(() => {
            this.dismiss(alertElement);
        }, delay);

        // Pausar el timer al hacer hover
        alertElement.addEventListener('mouseenter', () => {
            clearTimeout(timer);
        });

        // Reanudar el timer al salir del hover
        alertElement.addEventListener('mouseleave', () => {
            setTimeout(() => {
                this.dismiss(alertElement);
            }, 2000);
        });
    }

    // Descartar mensaje
    dismiss(alertElement) {
        if (alertElement && alertElement.parentNode) {
            // Remover de conjunto de persistentes si existe
            this.persistentMessages.delete(alertElement);
            
            alertElement.classList.remove('show');
            setTimeout(() => {
                if (alertElement.parentNode) {
                    alertElement.remove();
                }
            }, 150);
        }
    }

    // Limpiar mensajes por tipo (respetando persistentes)
    clearByType(type) {
        const messages = this.container.querySelectorAll(`[data-type="${type}"]`);
        messages.forEach(message => {
            // Solo eliminar si no es persistente
            if (!message.hasAttribute('data-persistent')) {
                this.dismiss(message);
            }
        });
    }

    // Limpiar solo mensajes no persistentes
    clearNonPersistent() {
        const messages = this.container.querySelectorAll('.flash-message:not([data-persistent])');
        messages.forEach(message => this.dismiss(message));
    }

    // Limpiar todos los mensajes (incluyendo persistentes)
    clearAll(includePersistent = false) {
        if (includePersistent) {
            const messages = this.container.querySelectorAll('.flash-message');
            messages.forEach(message => this.dismiss(message));
            this.persistentMessages.clear();
        } else {
            this.clearNonPersistent();
        }
    }

    // Marcar mensaje existente como persistente
    makePersistent(alertElement) {
        if (alertElement) {
            alertElement.setAttribute('data-persistent', 'true');
            alertElement.removeAttribute('data-auto-dismiss');
            this.persistentMessages.add(alertElement);
        }
    }
}

// Inicializar gestor de mensajes
const flashManager = new FlashMessagesManager();

// Limpiar mensajes existentes del HTML al cargar la página
document.addEventListener('DOMContentLoaded', () => {
    // Buscar alertas existentes en el HTML
    const existingAlerts = document.querySelectorAll('.alert');
    
    existingAlerts.forEach((alert, index) => {
        // Solo eliminar si no es un mensaje flash generado por JavaScript
        if (!alert.classList.contains('flash-message')) {
            if (index === 0) {
                // Marcar el primer mensaje como persistente
                alert.classList.add('flash-message');
                alert.setAttribute('data-persistent', 'true');
                flashManager.persistentMessages.add(alert);
            } else {
                // Eliminar inmediatamente otros mensajes sin mostrarlos
                alert.style.display = 'none';
                alert.remove();
            }
        }
    });
});

// Función para mostrar mensajes (con opción de persistencia)
function showMessage(message, type = 'info', autoDismiss = true, persistent = false) {
    return flashManager.create(message, type, autoDismiss, persistent);
}

// Función para mostrar mensaje persistente (que no se auto-elimina)
function showPersistentMessage(message, type = 'info') {
    return flashManager.create(message, type, false, true);
}

// Función para formatear el tamaño del archivo
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Función para validar archivo CSV
function validateCSVFile(file) {
    if (!file.name.toLowerCase().endsWith('.csv')) {
        showMessage('Por favor selecciona un archivo CSV válido (.csv)', 'danger');
        return false;
    }
    
    const maxSize = 16 * 1024 * 1024; // 16MB
    if (file.size > maxSize) {
        showMessage('El archivo es demasiado grande. Tamaño máximo permitido: 16MB', 'danger');
        return false;
    }
    
    return true;
}

// Función para mostrar información del archivo
function showFileInfo(file) {
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    fileInfo.classList.remove('d-none');
    dropZone.style.display = 'none';
}

// Función para ocultar información del archivo
function hideFileInfo() {
    fileInfo.classList.add('d-none');
    dropZone.style.display = 'block';
    fileInput.value = '';
    
    // Limpiar solo mensajes de éxito (no persistentes)
    flashManager.clearByType('success');
}

// Event listeners para drag and drop
dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        const file = files[0];
        if (validateCSVFile(file)) {
            fileInput.files = files;
            showFileInfo(file);
        }
    }
});

// Event listener para input de archivo
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        if (validateCSVFile(file)) {
            showFileInfo(file);
        } else {
            e.target.value = '';
        }
    }
});

// Event listener para remover archivo
removeFileBtn.addEventListener('click', hideFileInfo);

// Event listener para envío del formulario
uploadForm.addEventListener('submit', (e) => {
    e.preventDefault();
    
    // Validación crítica: verificar si hay archivo seleccionado
    if (!fileInput.files || fileInput.files.length === 0) {
        showMessage('Por favor, selecciona un archivo CSV antes de continuar', 'danger');
        
        // Resaltar la zona de drop para llamar la atención
        dropZone.style.border = '2px solid #e53e3e';
        dropZone.style.backgroundColor = '#fed7d7';
        
        // Quitar el resaltado después de 3 segundos
        setTimeout(() => {
            dropZone.style.border = '2px dashed #cbd5e0';
            dropZone.style.backgroundColor = '#f8fafc';
        }, 3000);
        
        return;
    }

    // Validar nuevamente el archivo seleccionado
    const file = fileInput.files[0];
    if (!validateCSVFile(file)) {
        return;
    }
    
    // Si llegamos aquí, el archivo es válido - continuar con el envío
    formSubmitted = true;
    
    // Mostrar estado de carga
    showLoadingState();
    
    // Mostrar barra de progreso
    progressContainer.style.display = 'block';
    
    // Iniciar simulación de progreso
    startProgressSimulation();
    
    // Enviar formulario con AJAX
    submitFormWithAjax();
});

// Función para mostrar estado de carga
function showLoadingState() {
    const spinner = submitBtn.querySelector('.spinner-border');
    const buttonText = submitBtn.querySelector('.button-text');
    
    spinner.style.display = 'inline-block';
    buttonText.textContent = 'Procesando archivo...';
    submitBtn.disabled = true;
}

// Función para ocultar estado de carga
function hideLoadingState() {
    const spinner = submitBtn.querySelector('.spinner-border');
    const buttonText = submitBtn.querySelector('.button-text');
    
    spinner.style.display = 'none';
    buttonText.textContent = 'Generar reporte de impresiones';
    submitBtn.disabled = false;
    progressContainer.style.display = 'none';
    progressBar.style.width = '0%';
    
    // Limpiar intervalos y timeouts
    clearProgressTimers();
}

// Función para limpiar timers de progreso
function clearProgressTimers() {
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
    if (safetyTimeout) {
        clearTimeout(safetyTimeout);
        safetyTimeout = null;
    }
}

// Función para iniciar simulación de progreso
function startProgressSimulation() {
    let progress = 0;
    let currentPhase = 0;
    
    const phases = [
        { end: 15, message: 'Validando archivo...', speed: 2 },
        { end: 35, message: 'Leyendo datos CSV...', speed: 1.5 },
        { end: 60, message: 'Procesando información...', speed: 1 },
        { end: 85, message: 'Generando reporte Excel...', speed: 1.2 },
        { end: 95, message: 'Finalizando proceso...', speed: 0.5 }
    ];
    
    const buttonText = submitBtn.querySelector('.button-text');
    
    progressInterval = setInterval(() => {
        if (currentPhase < phases.length) {
            const phase = phases[currentPhase];
            
            // Incrementar progreso gradualmente
            const increment = phase.speed;
            progress = Math.min(progress + increment, phase.end);
            
            // Actualizar mensaje si es necesario
            if (Math.floor(progress) >= phase.end - 2) {
                buttonText.textContent = phase.message;
                if (progress >= phase.end) {
                    currentPhase++;
                }
            }
        } else {
            // Fase final - mantener en 95% hasta que termine el servidor
            progress = Math.min(progress + 0.1, 98);
        }
        
        progressBar.style.width = progress + '%';
        
    }, 300);

    // Timeout de seguridad
    safetyTimeout = setTimeout(() => {
        if (formSubmitted && submitBtn.disabled) {
            clearProgressTimers();
            hideLoadingState();
            showMessage('El proceso está tomando más tiempo del esperado. Por favor, verifica tu conexión e intenta nuevamente.', 'warning');
            formSubmitted = false;
        }
    }, 45000);
}

// Event listener para botón de logout  
logoutBtn.addEventListener('click', (e) => {
    e.preventDefault();
    
    if (confirm('¿Estás seguro de que deseas cerrar sesión?')) {
        const spinner = logoutBtn.querySelector('.spinner-border');
        const logoutText = logoutBtn.querySelector('.logout-text');
        
        spinner.style.display = 'inline-block';
        logoutText.textContent = 'Cerrando sesión...';
        logoutBtn.disabled = true;
        
        setTimeout(() => {
            window.location.href = "/logout";
        }, 1000);
    }
});

// Función para extraer mensajes flash del HTML - MEJORADA
function extractFlashMessagesFromHTML(html) {
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    
    const alerts = tempDiv.querySelectorAll('.alert');
    const messages = [];
    
    alerts.forEach(alert => {
        let type = 'info';
        if (alert.classList.contains('alert-danger')) {
            type = 'danger';
        } else if (alert.classList.contains('alert-success')) {
            type = 'success';
        } else if (alert.classList.contains('alert-warning')) {
            type = 'warning';
        }
        
        const messageText = alert.textContent || alert.innerText;
        if (messageText) {
            const cleanMessage = messageText.replace(/×|Error!|Éxito!/g, '').trim();
            if (cleanMessage) {
                messages.push({ message: cleanMessage, type: type });
            }
        }
    });
    
    return messages;
}

// Función mejorada para enviar formulario con AJAX
function submitFormWithAjax() {
    const formData = new FormData(uploadForm);
    
    fetch('/subir_csv', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        console.log('Respuesta del servidor:', response.status, response.statusText);
        
        if (response.ok) {
            const contentType = response.headers.get('content-type');
            const contentDisposition = response.headers.get('content-disposition');
            
            if (contentDisposition && contentDisposition.includes('attachment')) {
                return response.blob().then(blob => {
                    completeProgress();
                    
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = extractFilenameFromHeader(contentDisposition) || 'reporte_impresiones.xlsx';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    
                    showMessage('¡Reporte generado y descargado exitosamente!', 'success');
                    
                    setTimeout(() => {
                        resetForm();
                    }, 2000);
                });
            } else {
                return response.text().then(html => {
                    console.log('HTML recibido:', html.substring(0, 500) + '...');
                    
                    const flashMessages = extractFlashMessagesFromHTML(html);
                    console.log('Mensajes flash extraídos:', flashMessages);
                    
                    if (flashMessages.length > 0) {
                        // CAMBIO CLAVE: Solo mostrar el PRIMER mensaje de error
                        const firstMessage = flashMessages[0];
                        handleProcessingError(firstMessage.message, firstMessage.type);
                    } else {
                        window.location.reload();
                    }
                });
            }
        } else {
            return response.text().then(html => {
                console.log('HTML de error recibido:', html.substring(0, 500) + '...');
                
                const flashMessages = extractFlashMessagesFromHTML(html);
                console.log('Mensajes de error extraídos:', flashMessages);
                
                if (flashMessages.length > 0) {
                    // CAMBIO CLAVE: Solo mostrar el PRIMER mensaje de error
                    const errorMessage = flashMessages[0];
                    handleProcessingError(errorMessage.message, errorMessage.type);
                } else {
                    handleGenericHttpError(response.status);
                }
            }).catch(textError => {
                console.error('Error al procesar respuesta HTML:', textError);
                handleGenericHttpError(response.status);
            });
        }
    })
    .catch(error => {
        console.error('Error de red:', error);
        let errorMessage = 'Error de conexión. Verifica tu conexión a internet e intenta nuevamente.';
        
        if (error.name === 'TypeError') {
            errorMessage = 'No se pudo conectar con el servidor. Verifica tu conexión.';
        } else if (error.message.includes('timeout')) {
            errorMessage = 'La conexión tardó demasiado tiempo. Intenta con un archivo más pequeño.';
        }
        
        handleProcessingError(errorMessage, 'danger');
    });
}

// Función para manejar errores HTTP genéricos
function handleGenericHttpError(status) {
    let errorMessage = 'Error del servidor';
    let type = 'danger';
    
    if (status === 400) {
        errorMessage = 'Archivo CSV inválido o formato incorrecto';
    } else if (status === 413) {
        errorMessage = 'El archivo es demasiado grande';
    } else if (status === 422) {
        errorMessage = 'El archivo CSV no contiene los encabezados requeridos. Verifica que el archivo tenga la estructura correcta.';
    } else if (status >= 500) {
        errorMessage = 'Error interno del servidor. Verifica el formato de tu archivo CSV.';
    }
    
    handleProcessingError(errorMessage, type);
}

// Función mejorada para manejar errores de procesamiento
function handleProcessingError(errorMessage, type = 'danger') {
    console.log('Manejando error:', errorMessage, 'Tipo:', type);
    
    clearProgressTimers();
    hideLoadingState();
    
    // CAMBIO CLAVE: Limpiar TODOS los mensajes antes de mostrar el nuevo
    flashManager.clearAll(false); // No limpiar persistentes
    
    // Para errores de encabezados, mostrar solo el mensaje simple de advertencia
    if (errorMessage.includes('encabezados') || errorMessage.includes('estructura') || errorMessage.includes('CSV no contiene')) {
        showMessage('Nota: Asegúrese de que el CSV tenga los encabezados correctos', 'warning', true, false);
    } else {
        // Para otros errores, mostrar el mensaje original
        showMessage(errorMessage, 'danger', true, false);
    }
    
    formSubmitted = false;
}

// Función para extraer nombre de archivo del header
function extractFilenameFromHeader(contentDisposition) {
    const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
    if (filenameMatch && filenameMatch[1]) {
        return filenameMatch[1].replace(/['"]/g, '');
    }
    return null;
}

// Función para completar el progreso
function completeProgress() {
    clearProgressTimers();
    
    progressBar.style.width = '100%';
    const buttonText = submitBtn.querySelector('.button-text');
    buttonText.textContent = '¡Proceso completado!';
    
    setTimeout(() => {
        hideLoadingState();
    }, 1500);
}

// Función para resetear el formulario
function resetForm() {
    hideFileInfo();
    formSubmitted = false;
    flashManager.clearByType('success');
}

// Detectar cuando la página se recarga o cambia (procesamiento exitoso)
window.addEventListener('beforeunload', () => {
    clearProgressTimers();
});

// Detectar cuando la página se oculta (navegación exitosa)
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        clearProgressTimers();
    }
});

window.addEventListener('dragover', (e) => e.preventDefault());
window.addEventListener('drop', (e) => e.preventDefault());