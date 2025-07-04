/**
 * Sistema de carga y procesamiento de archivos CSV - VERSIÓN CORREGIDA SIN CANCELACIÓN AL CAMBIAR PESTAÑA
 */

// ===================================================================
// 1. CONFIGURACIÓN Y CONSTANTES
// ===================================================================

const CONFIG = {
    MAX_FILE_SIZE: 16 * 1024 * 1024, // 16MB
    SAFETY_TIMEOUT: 30000, // 30 segundos
    PROGRESS_INTERVAL: 300,
    AUTO_DISMISS_DELAYS: {
        success: 5000,
        info: 5000,
        warning: 4000,
        danger: 4000
    }
};

// ===================================================================
// 2. VARIABLES GLOBALES
// ===================================================================

let elements = {};
let progressInterval = null;
let safetyTimeout = null;
let formSubmitted = false;
let abortController = null;
let flashManager = null;

// ===================================================================
// 3. CLASE PARA MANEJO DE MENSAJES FLASH
// ===================================================================

class FlashMessagesManager {
    constructor() {
        this.container = document.getElementById('flashMessages');
        this.persistentMessages = new Set();
        this.activeTimers = new Map();
    }

    create(message, type = 'info', autoDismiss = true, persistent = false) {
        if (!persistent) {
            this.clearNonPersistent();
        }

        const alertDiv = this.createAlertElement(message, type, autoDismiss, persistent);
        this.container.appendChild(alertDiv);

        if (autoDismiss && !persistent) {
            const delay = CONFIG.AUTO_DISMISS_DELAYS[type] || CONFIG.AUTO_DISMISS_DELAYS.info;
            this.setupAutoDismiss(alertDiv, delay);
        }

        setTimeout(() => alertDiv.classList.add('show'), 10);
        return alertDiv;
    }

    createAlertElement(message, type, autoDismiss, persistent) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show flash-message`;
        alertDiv.setAttribute('data-type', type);
        alertDiv.setAttribute('role', 'alert');
        
        if (autoDismiss && !persistent) {
            alertDiv.setAttribute('data-auto-dismiss', 'true');
        }
        if (persistent) {
            alertDiv.setAttribute('data-persistent', 'true');
            this.persistentMessages.add(alertDiv);
        }

        const iconClass = this.getIconClass(type);
        alertDiv.innerHTML = `
            <i class="bi bi-${iconClass} me-2" aria-hidden="true"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Cerrar mensaje"></button>
        `;

        return alertDiv;
    }

    getIconClass(type) {
        const icons = {
            'success': 'check-circle',
            'danger': 'exclamation-triangle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    setupAutoDismiss(alertElement, delay) {
        const timer = setTimeout(() => this.dismiss(alertElement), delay);
        this.activeTimers.set(alertElement, timer);

        alertElement.addEventListener('mouseenter', () => {
            const currentTimer = this.activeTimers.get(alertElement);
            if (currentTimer) {
                clearTimeout(currentTimer);
                this.activeTimers.delete(alertElement);
            }
        });

        alertElement.addEventListener('mouseleave', () => {
            const newTimer = setTimeout(() => this.dismiss(alertElement), 2000);
            this.activeTimers.set(alertElement, newTimer);
        });
    }

    dismiss(alertElement) {
        if (alertElement?.parentNode) {
            const timer = this.activeTimers.get(alertElement);
            if (timer) {
                clearTimeout(timer);
                this.activeTimers.delete(alertElement);
            }

            this.persistentMessages.delete(alertElement);
            alertElement.classList.remove('show');
            setTimeout(() => alertElement.remove(), 150);
        }
    }

    clearByType(type) {
        this.container.querySelectorAll(`[data-type="${type}"]`)
            .forEach(message => {
                if (!message.hasAttribute('data-persistent')) {
                    this.dismiss(message);
                }
            });
    }

    clearNonPersistent() {
        this.container.querySelectorAll('.flash-message:not([data-persistent])')
            .forEach(message => this.dismiss(message));
    }

    clearAll(includePersistent = false) {
        if (includePersistent) {
            this.container.querySelectorAll('.flash-message')
                .forEach(message => this.dismiss(message));
            this.persistentMessages.clear();
        } else {
            this.clearNonPersistent();
        }
    }

    clearAllTimers() {
        this.activeTimers.forEach(timer => clearTimeout(timer));
        this.activeTimers.clear();
    }
}

// ===================================================================
// 4. FUNCIONES UTILITARIAS
// ===================================================================

const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const showMessage = (message, type = 'info', autoDismiss = true, persistent = false) => {
    return flashManager.create(message, type, autoDismiss, persistent);
};

const extractFilenameFromHeader = (contentDisposition) => {
    const filenameMatch = contentDisposition?.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
    return filenameMatch?.[1]?.replace(/['"]/g, '') || null;
};

const preventGlobalDragDrop = (e) => e.preventDefault();

// ===================================================================
// 5. VALIDACIÓN DE ARCHIVOS
// ===================================================================

const validateCSVFile = (file) => {
    // Limpiar mensajes de error previos
    flashManager.clearByType('danger');
    
    if (!file.name.toLowerCase().endsWith('.csv')) {
        showMessage('Por favor selecciona un archivo CSV válido (.csv)', 'danger');
        return false;
    }
    
    if (file.size > CONFIG.MAX_FILE_SIZE) {
        const maxSizeMB = CONFIG.MAX_FILE_SIZE / (1024 * 1024);
        showMessage(`El archivo es demasiado grande. Tamaño máximo permitido: ${maxSizeMB}MB`, 'danger');
        return false;
    }
    
    if (file.size === 0) {
        showMessage('El archivo está vacío. Por favor selecciona un archivo válido.', 'danger');
        return false;
    }
    
    return true;
};

// ===================================================================
// 6. GESTIÓN DE INFORMACIÓN DEL ARCHIVO
// ===================================================================

const showFileInfo = (file) => {
    elements.fileName.textContent = file.name;
    elements.fileSize.textContent = formatFileSize(file.size);
    elements.fileInfo.classList.remove('d-none');
    elements.dropZone.style.display = 'none';
};

const hideFileInfo = () => {
    elements.fileInfo.classList.add('d-none');
    elements.dropZone.style.display = 'block';
    elements.fileInput.value = '';
    flashManager.clearByType('success');
};

// ===================================================================
// 7. GESTIÓN DE ESTADOS DE CARGA
// ===================================================================

const showLoadingState = () => {
    if (elements.cancelBtn) {
        elements.cancelBtn.classList.remove('d-none');
    }
    
    const spinner = elements.submitBtn.querySelector('.spinner-border');
    const buttonText = elements.submitBtn.querySelector('.button-text');
    
    if (spinner) spinner.style.display = 'inline-block';
    if (buttonText) buttonText.textContent = 'Procesando archivo...';
    elements.submitBtn.disabled = true;
};

const hideLoadingState = () => {
    if (elements.cancelBtn) {
        elements.cancelBtn.classList.add('d-none');
    }
    
    const spinner = elements.submitBtn.querySelector('.spinner-border');
    const buttonText = elements.submitBtn.querySelector('.button-text');
    
    if (spinner) spinner.style.display = 'none';
    if (buttonText) buttonText.textContent = 'Generar reporte de impresiones';
    elements.submitBtn.disabled = false;
    elements.progressContainer.style.display = 'none';
    elements.progressBar.style.width = '0%';
    
    elements.progressBar.setAttribute('aria-valuenow', '0');
    
    clearProgressTimers();
};

// ===================================================================
// 8. GESTIÓN DE PROGRESO
// ===================================================================

const clearProgressTimers = () => {
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
    if (safetyTimeout) {
        clearTimeout(safetyTimeout);
        safetyTimeout = null;
    }
};

const startProgressSimulation = () => {
    let progress = 0;
    let currentPhase = 0;
    
    const phases = [
        { end: 15, message: 'Validando archivo...', speed: 2 },
        { end: 35, message: 'Leyendo datos CSV...', speed: 1.5 },
        { end: 60, message: 'Procesando información...', speed: 1 },
        { end: 85, message: 'Generando reporte Excel...', speed: 1.2 },
        { end: 95, message: 'Finalizando proceso...', speed: 0.5 }
    ];
    
    const buttonText = elements.submitBtn.querySelector('.button-text');
    
    if (buttonText && !buttonText.hasAttribute('aria-live')) {
        buttonText.setAttribute('aria-live', 'polite');
    }
    
    elements.progressBar.setAttribute('role', 'progressbar');
    elements.progressBar.setAttribute('aria-valuenow', '0');
    elements.progressBar.setAttribute('aria-valuemin', '0');
    elements.progressBar.setAttribute('aria-valuemax', '100');
    
    progressInterval = setInterval(() => {
        if (!formSubmitted) {
            clearInterval(progressInterval);
            return;
        }
        
        if (currentPhase < phases.length) {
            const phase = phases[currentPhase];
            const increment = phase.speed;
            progress = Math.min(progress + increment, phase.end);
            
            if (Math.floor(progress) >= phase.end - 2) {
                if (buttonText) buttonText.textContent = phase.message;
            }
        } else {
            progress = Math.min(progress + 0.1, 98);
        }
        
        if (currentPhase < phases.length && progress >= phases[currentPhase].end) {
            currentPhase++;
        }
        
        elements.progressBar.style.width = progress + '%';
        elements.progressBar.setAttribute('aria-valuenow', Math.floor(progress));
        
    }, CONFIG.PROGRESS_INTERVAL);

    safetyTimeout = setTimeout(() => {
        if (formSubmitted && elements.submitBtn.disabled) {
            clearProgressTimers();
            hideLoadingState();
            showMessage('El proceso está tomando más tiempo del esperado. Por favor, intenta nuevamente.', 'warning');
            formSubmitted = false;
        }
    }, CONFIG.SAFETY_TIMEOUT);
};

const completeProgress = () => {
    clearProgressTimers();
    
    elements.progressBar.style.width = '100%';
    elements.progressBar.setAttribute('aria-valuenow', '100');
    const buttonText = elements.submitBtn.querySelector('.button-text');
    if (buttonText) buttonText.textContent = '¡Proceso completado!';
    
    setTimeout(hideLoadingState, 1500);
};

// ===================================================================
// 9. PROCESAMIENTO DE RESPUESTAS HTTP
// ===================================================================

const extractFlashMessagesFromHTML = (html) => {
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    
    const alerts = tempDiv.querySelectorAll('.alert');
    const messages = [];
    
    alerts.forEach(alert => {
        let type = 'info';
        if (alert.classList.contains('alert-danger')) type = 'danger';
        else if (alert.classList.contains('alert-success')) type = 'success';
        else if (alert.classList.contains('alert-warning')) type = 'warning';
        
        const messageText = alert.textContent || alert.innerText;
        if (messageText) {
            const cleanMessage = messageText.replace(/×|Error!|Éxito!/g, '').trim();
            if (cleanMessage) {
                messages.push({ message: cleanMessage, type: type });
            }
        }
    });
    
    return messages;
};

const downloadBlob = (blob, contentDisposition) => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = extractFilenameFromHeader(contentDisposition) || 'reporte_impresiones.xlsx';
    a.setAttribute('aria-label', `Descargar ${a.download}`);
    
    document.body.appendChild(a);
    a.click();
    
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
};

const handleHTMLResponse = (response) => {
    return response.text().then(html => {
        const flashMessages = extractFlashMessagesFromHTML(html);
        if (flashMessages.length > 0) {
            const firstMessage = flashMessages[0];
            handleProcessingError(firstMessage.message, firstMessage.type);
        } else {
            window.location.reload();
        }
    });
};

const handleErrorResponse = (response) => {
    return response.text().then(html => {
        const flashMessages = extractFlashMessagesFromHTML(html);
        if (flashMessages.length > 0) {
            const errorMessage = flashMessages[0];
            handleProcessingError(errorMessage.message, errorMessage.type);
        } else {
            handleGenericHttpError(response.status);
        }
    }).catch(() => handleGenericHttpError(response.status));
};

// ===================================================================
// 10. MANEJO DE ERRORES
// ===================================================================

const handleProcessingError = (errorMessage, type = 'danger') => {
    console.log('Manejando error:', errorMessage, 'Tipo:', type);
    
    clearProgressTimers();
    hideLoadingState();
    
    flashManager.clearNonPersistent();
    
    if (errorMessage.includes('encabezados') || errorMessage.includes('estructura') || errorMessage.includes('CSV no contiene')) {
        setTimeout(() => {
            showMessage('Nota: Asegúrese de que el CSV tenga los encabezados correctos', 'warning', true, false);
        }, 100);
    } else {
        showMessage(errorMessage, type, true, false);
    }
    
    formSubmitted = false;
};

// Reset completo después de cancelar CON BORRADO DE ARCHIVO
const resetFormAfterCancel = () => {
    formSubmitted = false;
    hideLoadingState();
    clearProgressTimers();
    
    // Borrar el archivo seleccionado
    hideFileInfo();
    
    // Limpiar mensajes flash
    flashManager.clearAll(false);
    
    // Mostrar mensaje de cancelación sin persistencia
    showMessage('Operación cancelada. Archivo removido.', 'info', true, false);
    
    console.log('Formulario reseteado después de cancelación - archivo borrado');
};

const handleNetworkError = (error) => {
    console.error('Error de red:', error);
    let errorMessage = 'Error de conexión. Verifica tu conexión a internet e intenta nuevamente.';
    let messageType = 'danger';
    
    if (error.name === 'AbortError') {
        errorMessage = 'Generación de reporte cancelada';
        messageType = 'info';
        
        resetFormAfterCancel();
        return;
    } else if (error.name === 'TypeError') {
        errorMessage = 'No se pudo conectar con el servidor. Verifica tu conexión.';
    } else if (error.message.includes('timeout')) {
        errorMessage = 'La conexión tardó demasiado tiempo. Intenta con un archivo más pequeño.';
    }
    
    handleProcessingError(errorMessage, messageType);
};

const handleGenericHttpError = (status) => {
    let errorMessage = 'Error del servidor';
    
    if (status === 400) {
        errorMessage = 'Archivo CSV inválido o formato incorrecto';
    } else if (status === 413) {
        errorMessage = 'El archivo es demasiado grande';
    } else if (status === 422) {
        errorMessage = 'El archivo CSV no contiene los encabezados requeridos. Verifica que el archivo tenga la estructura correcta.';
    } else if (status >= 500) {
        errorMessage = 'Error interno del servidor. Verifica el formato de tu archivo CSV.';
    }
    
    handleProcessingError(errorMessage, 'danger');
};

// ===================================================================
// 11. ENVÍO DEL FORMULARIO Y AJAX
// ===================================================================

const submitFormWithAjax = () => {
    const formData = new FormData(elements.uploadForm);
    
    abortController = new AbortController();
    const timeoutId = setTimeout(() => {
        if (formSubmitted) {
            abortController.abort();
        }
    }, CONFIG.SAFETY_TIMEOUT);
    
    fetch('/subir_csv', {
        method: 'POST',
        body: formData,
        signal: abortController.signal
    })
    .then(response => {
        clearTimeout(timeoutId);
        console.log('Respuesta del servidor:', response.status, response.statusText);
        
        if (response.ok) {
            return handleSuccessResponse(response);
        } else {
            return handleErrorResponse(response);
        }
    })
    .catch(error => {
        clearTimeout(timeoutId);
        handleNetworkError(error);
    })
    .finally(() => {
        abortController = null;
    });
};

const handleSuccessResponse = (response) => {
    const contentDisposition = response.headers.get('content-disposition');
    
    if (contentDisposition?.includes('attachment')) {
        return response.blob().then(blob => {
            if (blob.size === 0) {
                throw new Error('El archivo descargado está vacío');
            }
            
            completeProgress();
            downloadBlob(blob, contentDisposition);
            showMessage('¡Reporte generado y descargado exitosamente!', 'success');
            
            setTimeout(resetForm, 4000);
        });
    } else {
        return handleHTMLResponse(response);
    }
};

const resetForm = () => {
    hideFileInfo();
    formSubmitted = false;
    
    flashManager.clearByType('success');
    flashManager.clearByType('info');
    
    hideLoadingState();
    
    console.log('Formulario completamente reseteado');
};

// ===================================================================
// 12. EVENT LISTENERS
// ===================================================================

const setupDragAndDropListeners = () => {
    elements.dropZone.addEventListener('click', () => elements.fileInput.click());
    
    elements.dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        elements.dropZone.classList.add('dragover');
    });
    
    elements.dropZone.addEventListener('dragleave', () => {
        elements.dropZone.classList.remove('dragover');
    });
    
    elements.dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        elements.dropZone.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            if (validateCSVFile(file)) {
                elements.fileInput.files = files;
                showFileInfo(file);
            }
        }
    });
};

const setupFileInputListener = () => {
    elements.fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            if (validateCSVFile(file)) {
                showFileInfo(file);
            } else {
                e.target.value = '';
            }
        }
    });
};

const setupFormSubmitListener = () => {
    elements.uploadForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        if (formSubmitted) {
            showMessage('Ya hay una operación en curso. Por favor espera o cancela la operación actual.', 'warning');
            return;
        }
        
        flashManager.clearByType('danger');
        flashManager.clearByType('warning');
        
        if (!elements.fileInput.files || elements.fileInput.files.length === 0) {
            showMessage('Por favor, selecciona un archivo CSV antes de continuar', 'danger');
            highlightDropZone();
            return;
        }

        const file = elements.fileInput.files[0];
        if (!validateCSVFile(file)) return;
        
        formSubmitted = true;
        showLoadingState();
        elements.progressContainer.style.display = 'block';
        startProgressSimulation();
        submitFormWithAjax();
    });
};

const cancelOperationAndRemoveFile = () => {
    console.log('Cancelando operación y removiendo archivo...');
    
    if (abortController && formSubmitted) {
        abortController.abort();
        return;
    }
    
    if (!formSubmitted) {
        resetFormAfterCancel();
    }
};

const setupControlButtonsListeners = () => {
    elements.removeFileBtn.addEventListener('click', () => {
        if (formSubmitted) {
            cancelOperationAndRemoveFile();
        } else {
            hideFileInfo();
            flashManager.clearNonPersistent();
            showMessage('Archivo removido', 'info', true, false);
        }
    });

    if (elements.cancelBtn) {
        elements.cancelBtn.addEventListener('click', () => {
            if (abortController && formSubmitted) {
                console.log('Cancelando operación mediante botón Cancelar...');
                abortController.abort();
            } else if (formSubmitted) {
                console.log('Forzando cancelación mediante botón Cancelar...');
                resetFormAfterCancel();
            }
        });
    }

    elements.logoutBtn.addEventListener('click', handleLogout);
};

const highlightDropZone = () => {
    elements.dropZone.style.border = '2px solid #e53e3e';
    elements.dropZone.style.backgroundColor = '#fed7d7';
    
    setTimeout(() => {
        elements.dropZone.style.border = '2px dashed #cbd5e0';
        elements.dropZone.style.backgroundColor = '#f8fafc';
    }, 3000);
};

const handleLogout = (e) => {
    e.preventDefault();
    
    if (confirm('¿Estás seguro de que deseas cerrar sesión?')) {
        const spinner = elements.logoutBtn.querySelector('.spinner-border');
        const logoutText = elements.logoutBtn.querySelector('.logout-text');
        
        if (spinner) spinner.style.display = 'inline-block';
        if (logoutText) logoutText.textContent = 'Cerrando sesión...';
        elements.logoutBtn.disabled = true;
        
        setTimeout(() => {
            window.location.href = "/logout";
        }, 1000);
    }
};

const setupEventListeners = () => {
    setupDragAndDropListeners();
    setupFileInputListener();
    setupFormSubmitListener();
    setupControlButtonsListeners();
};

// ===================================================================
// 13. INICIALIZACIÓN Y LIMPIEZA - CORREGIDA
// ===================================================================

const initializeDOMElements = () => {
    elements = {
        uploadForm: document.getElementById('uploadForm'),
        fileInput: document.getElementById('archivo'),
        dropZone: document.getElementById('dropZone'),
        fileInfo: document.getElementById('fileInfo'),
        fileName: document.getElementById('fileName'),
        fileSize: document.getElementById('fileSize'),
        removeFileBtn: document.getElementById('removeFile'),
        submitBtn: document.getElementById('submitBtn'),
        progressContainer: document.querySelector('.progress-container'),
        progressBar: document.querySelector('.progress-bar'),
        logoutBtn: document.getElementById('logoutBtn'),
        cancelBtn: document.getElementById('cancelBtn')
    };
};

const processExistingAlerts = () => {
    const existingAlerts = document.querySelectorAll('.alert');
    existingAlerts.forEach((alert, index) => {
        if (!alert.classList.contains('flash-message')) {
            if (index === 0) {
                alert.classList.add('flash-message');
                alert.setAttribute('data-persistent', 'true');
                alert.setAttribute('role', 'alert');
                flashManager.persistentMessages.add(alert);
            } else {
                alert.style.display = 'none';
                alert.remove();
            }
        }
    });
};

const setupGlobalDragDropPrevention = () => {
    if (!window.dragDropListenersAdded) {
        window.addEventListener('dragover', preventGlobalDragDrop);
        window.addEventListener('drop', preventGlobalDragDrop);
        window.dragDropListenersAdded = true;
    }
};

// FUNCIÓN CORREGIDA: Listeners de limpieza sin interferir con el cambio de pestañas
const setupCleanupListeners = () => {
    // Solo limpiar cuando realmente se cierre la ventana/pestaña
    window.addEventListener('beforeunload', () => {
        if (formSubmitted && abortController) {
            abortController.abort();
        }
        flashManager?.clearAllTimers();
        clearProgressTimers();
        formSubmitted = false;
    });
    
    // CORREGIDO: Solo limpiar timers al cambiar de pestaña, NO mostrar mensajes de cancelación
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            // Solo limpiar timers cuando la pestaña se oculta
            // NO cancelar operaciones ni mostrar mensajes
            flashManager?.clearAllTimers();
            // NO llamar clearProgressTimers() aquí porque puede interrumpir operaciones válidas
        }
        // Cuando la pestaña vuelve a ser visible, no hacer nada especial
        // Las operaciones en curso deben continuar normalmente
    });
    
    // CORREGIDO: Verificar estado solo cuando la ventana se enfoca
    window.addEventListener('focus', () => {
        // Solo resetear si hay un estado inconsistente (botón deshabilitado sin operación)
        if (!formSubmitted && elements.submitBtn.disabled) {
            console.log('Detectado estado inconsistente, corrigiendo...');
            hideLoadingState();
            formSubmitted = false;
        }
    });
};

// ===================================================================
// 14. FUNCIONALIDAD DE LOGIN
// ===================================================================

const setupLoginFunctionality = () => {
    const passwordInput = document.getElementById('password');
    const togglePassword = document.getElementById('togglePassword');
    
    if (passwordInput && togglePassword) {
        togglePassword.addEventListener('click', function() {
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);
            
            this.classList.toggle('bi-eye');
            this.classList.toggle('bi-eye-slash');
        });
    }

    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        const submitBtn = loginForm.querySelector('button[type="submit"]');
        const spinner = submitBtn.querySelector('.spinner-border');
        const buttonText = submitBtn.querySelector('.button-text');
        
        loginForm.addEventListener('submit', function() {
            if (spinner) spinner.classList.remove('d-none');
            if (buttonText) buttonText.innerHTML = '<i class="bi bi-arrow-repeat me-2"></i>Verificando...';
            submitBtn.disabled = true;
        });
    }

    const successAlerts = document.querySelectorAll('.alert-success');
    successAlerts.forEach(alert => {
        setTimeout(() => {
            alert.classList.remove('show');
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.remove();
                }
            }, 150);
        }, 3000);
    });

    const firstInput = document.querySelector('.is-invalid') || document.getElementById('usuario');
    if (firstInput) {
        firstInput.focus();
    }
};

// ===================================================================
// 15. PUNTO DE ENTRADA PRINCIPAL
// ===================================================================

document.addEventListener('DOMContentLoaded', () => {
    initializeDOMElements();
    flashManager = new FlashMessagesManager();
    processExistingAlerts();
    setupEventListeners();
    setupGlobalDragDropPrevention();
    setupCleanupListeners();
    setupLoginFunctionality();
    
    console.log('Sistema de carga CSV inicializado correctamente - SIN CANCELACIÓN AL CAMBIAR PESTAÑA');
});