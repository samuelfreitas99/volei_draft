// Funções utilitárias gerais

$(document).ready(function() {
    // Inicializar tooltips
    $('[data-bs-toggle="tooltip"]').tooltip();
    
    // Inicializar popovers
    $('[data-bs-toggle="popover"]').popover();
    
    // Auto-dismiss alerts após 5 segundos
    setTimeout(function() {
        $('.alert:not(.alert-permanent)').alert('close');
    }, 5000);
    
    // Confirmação em links com data-confirm
    $('a[data-confirm]').click(function(e) {
        if (!confirm($(this).data('confirm'))) {
            e.preventDefault();
            e.stopPropagation();
            return false;
        }
    });
    
    // Formatação de telefone
    $('input[type="tel"]').on('input', function() {
        let value = $(this).val().replace(/\D/g, '');
        if (value.length > 0) {
            if (value.length <= 10) {
                value = value.replace(/(\d{2})(\d{4})(\d{0,4})/, '($1) $2-$3');
            } else {
                value = value.replace(/(\d{2})(\d{5})(\d{0,4})/, '($1) $2-$3');
            }
        }
        $(this).val(value);
    });
    
    // Atualizar data/hora no footer
    updateDateTime();
    setInterval(updateDateTime, 60000);
});

function updateDateTime() {
    const now = new Date();
    const options = { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    const dateTimeStr = now.toLocaleDateString('pt-BR', options);
    $('#currentDateTime').text(dateTimeStr);
}

// Função para mostrar notificação toast
function showNotification(title, message, type = 'info', duration = 5000) {
    const toastId = 'toast-' + Date.now();
    const icon = {
        'success': 'check-circle',
        'error': 'exclamation-circle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
    }[type] || 'info-circle';
    
    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-bg-${type} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    <div class="d-flex align-items-center">
                        <i class="fas fa-${icon} me-2"></i>
                        <div>
                            <strong>${title}</strong>
                            <div class="small">${message}</div>
                        </div>
                    </div>
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    // Adicionar ao container de toasts
    let toastContainer = $('.toast-container');
    if (toastContainer.length === 0) {
        toastContainer = $('<div class="toast-container position-fixed bottom-0 end-0 p-3"></div>');
        $('body').append(toastContainer);
    }
    
    toastContainer.append(toastHtml);
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { delay: duration });
    toast.show();
    
    // Remover após ser escondido
    toastElement.addEventListener('hidden.bs.toast', function () {
        $(this).remove();
    });
}

// Função para carregar dados via AJAX
function loadAjaxData(url, containerId, callback) {
    $.ajax({
        url: url,
        type: 'GET',
        beforeSend: function() {
            $(containerId).html(`
                <div class="spinner-container">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Carregando...</span>
                    </div>
                </div>
            `);
        },
        success: function(data) {
            $(containerId).html(data);
            if (callback) callback();
        },
        error: function() {
            $(containerId).html(`
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle"></i>
                    Erro ao carregar dados.
                </div>
            `);
        }
    });
}

// Validação de formulários
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;
    
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            isValid = false;
            field.classList.add('is-invalid');
            
            // Adicionar mensagem de erro
            let errorDiv = field.parentNode.querySelector('.invalid-feedback');
            if (!errorDiv) {
                errorDiv = document.createElement('div');
                errorDiv.className = 'invalid-feedback';
                errorDiv.textContent = 'Este campo é obrigatório.';
                field.parentNode.appendChild(errorDiv);
            }
        } else {
            field.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}

// Função para formatar números
function formatNumber(number, decimals = 0) {
    return new Intl.NumberFormat('pt-BR', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    }).format(number);
}

// Função para formatar data
function formatDate(dateString, format = 'dd/MM/yyyy') {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return dateString;
    
    const day = date.getDate().toString().padStart(2, '0');
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const year = date.getFullYear();
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const seconds = date.getSeconds().toString().padStart(2, '0');
    
    return format
        .replace('dd', day)
        .replace('MM', month)
        .replace('yyyy', year)
        .replace('HH', hours)
        .replace('mm', minutes)
        .replace('ss', seconds);
}

// Socket.IO helpers
let socket = null;

function initSocketIO() {
    if (typeof io !== 'undefined') {
        socket = io();
        
        socket.on('connect', function() {
            console.log('Conectado ao servidor Socket.IO');
        });
        
        socket.on('disconnect', function() {
            console.log('Desconectado do servidor Socket.IO');
        });
        
        socket.on('error', function(error) {
            console.error('Erro Socket.IO:', error);
        });
    }
}

// Exportar funções para uso global
window.App = {
    showNotification: showNotification,
    loadAjaxData: loadAjaxData,
    validateForm: validateForm,
    formatNumber: formatNumber,
    formatDate: formatDate,
    initSocketIO: initSocketIO
};

// Inicializar Socket.IO quando disponível
if (typeof io !== 'undefined') {
    initSocketIO();
}