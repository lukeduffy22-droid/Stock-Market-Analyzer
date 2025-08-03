// Enhanced JavaScript for AI Stock Market Analyzer

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Enhanced file upload handling
    initializeFileUpload();
    
    // Form validation
    initializeFormValidation();
    
    // Auto-dismiss alerts
    initializeAlerts();
    
    // Loading states
    initializeLoadingStates();
    
    // Table enhancements
    initializeTableEnhancements();
});

function initializeFileUpload() {
    const fileInput = document.getElementById('file');
    const uploadForm = document.getElementById('uploadForm');
    
    if (fileInput) {
        // Drag and drop functionality
        const dropZone = fileInput.parentElement;
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, unhighlight, false);
        });
        
        function highlight(e) {
            dropZone.classList.add('border-primary', 'bg-primary-subtle');
        }
        
        function unhighlight(e) {
            dropZone.classList.remove('border-primary', 'bg-primary-subtle');
        }
        
        dropZone.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (files.length > 0) {
                fileInput.files = files;
                fileInput.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }
        
        // File validation
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                validateFile(file);
                displayFileInfo(file);
            }
        });
    }
}

function validateFile(file) {
    const maxSize = 50 * 1024 * 1024; // 50MB
    const allowedTypes = ['.csv', '.txt', '.tsv'];
    
    // Check file size
    if (file.size > maxSize) {
        showAlert('File size exceeds 50MB limit. Please choose a smaller file.', 'danger');
        document.getElementById('file').value = '';
        return false;
    }
    
    // Check file type
    const fileName = file.name.toLowerCase();
    const isValidType = allowedTypes.some(type => fileName.endsWith(type));
    
    if (!isValidType) {
        showAlert('Please upload a CSV, TXT, or TSV file.', 'warning');
        return false;
    }
    
    return true;
}

function displayFileInfo(file) {
    const fileSize = (file.size / (1024 * 1024)).toFixed(2);
    const fileName = file.name;
    
    // Remove existing file info
    const existingInfo = document.getElementById('fileInfo');
    if (existingInfo) {
        existingInfo.remove();
    }
    
    // Create new file info display
    const fileInfo = document.createElement('div');
    fileInfo.id = 'fileInfo';
    fileInfo.className = 'alert alert-info mt-2 d-flex align-items-center justify-content-between';
    fileInfo.innerHTML = `
        <div>
            <i class="fas fa-file-csv me-2"></i>
            <strong>${fileName}</strong> (${fileSize} MB)
        </div>
        <button type="button" class="btn btn-sm btn-outline-info" onclick="clearFileSelection()">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    document.getElementById('file').parentNode.appendChild(fileInfo);
}

function clearFileSelection() {
    document.getElementById('file').value = '';
    const fileInfo = document.getElementById('fileInfo');
    if (fileInfo) {
        fileInfo.remove();
    }
}

function initializeFormValidation() {
    // Login form validation
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            const email = document.getElementById('email');
            const password = document.getElementById('password');
            
            if (!validateEmail(email.value)) {
                e.preventDefault();
                showFieldError(email, 'Please enter a valid email address.');
                return false;
            }
            
            if (password.value.length < 6) {
                e.preventDefault();
                showFieldError(password, 'Password must be at least 6 characters long.');
                return false;
            }
            
            clearFieldErrors();
        });
    }
}

function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function showFieldError(field, message) {
    field.classList.add('is-invalid');
    
    // Remove existing feedback
    const existingFeedback = field.parentNode.querySelector('.invalid-feedback');
    if (existingFeedback) {
        existingFeedback.remove();
    }
    
    // Add new feedback
    const feedback = document.createElement('div');
    feedback.className = 'invalid-feedback';
    feedback.textContent = message;
    field.parentNode.appendChild(feedback);
}

function clearFieldErrors() {
    document.querySelectorAll('.is-invalid').forEach(field => {
        field.classList.remove('is-invalid');
    });
    
    document.querySelectorAll('.invalid-feedback').forEach(feedback => {
        feedback.remove();
    });
}

function initializeAlerts() {
    // Auto-dismiss success alerts after 5 seconds
    document.querySelectorAll('.alert-success').forEach(alert => {
        setTimeout(() => {
            const alertInstance = bootstrap.Alert.getOrCreateInstance(alert);
            alertInstance.close();
        }, 5000);
    });
}

function showAlert(message, type = 'info', autoDismiss = true) {
    const alertContainer = document.createElement('div');
    alertContainer.className = `alert alert-${type} alert-dismissible fade show`;
    alertContainer.innerHTML = `
        <i class="fas fa-${getIconForAlertType(type)} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert at the top of the main content
    const main = document.querySelector('main');
    if (main) {
        main.insertBefore(alertContainer, main.firstChild);
    }
    
    if (autoDismiss && type === 'success') {
        setTimeout(() => {
            const alertInstance = bootstrap.Alert.getOrCreateInstance(alertContainer);
            alertInstance.close();
        }, 5000);
    }
}

function getIconForAlertType(type) {
    const icons = {
        'success': 'check-circle',
        'danger': 'exclamation-triangle',
        'warning': 'exclamation-circle',
        'info': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

function initializeLoadingStates() {
    // Add loading states to forms
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
                submitBtn.disabled = true;
                
                // Re-enable button if form validation fails
                setTimeout(() => {
                    if (!form.checkValidity()) {
                        submitBtn.innerHTML = originalText;
                        submitBtn.disabled = false;
                    }
                }, 100);
            }
        });
    });
}

function initializeTableEnhancements() {
    // Add sorting functionality to tables
    document.querySelectorAll('.table th').forEach(header => {
        if (header.textContent.trim() && !header.querySelector('button')) {
            header.style.cursor = 'pointer';
            header.addEventListener('click', function() {
                sortTable(header);
            });
        }
    });
}

function sortTable(header) {
    const table = header.closest('table');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const headerIndex = Array.from(header.parentNode.children).indexOf(header);
    
    // Determine sort direction
    const isAscending = !header.classList.contains('sort-desc');
    
    // Clear all sort classes
    header.parentNode.querySelectorAll('th').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
    });
    
    // Add appropriate sort class
    header.classList.add(isAscending ? 'sort-asc' : 'sort-desc');
    
    // Sort rows
    rows.sort((a, b) => {
        const aText = a.children[headerIndex].textContent.trim();
        const bText = b.children[headerIndex].textContent.trim();
        
        // Try to parse as numbers
        const aNum = parseFloat(aText.replace(/[₹,]/g, ''));
        const bNum = parseFloat(bText.replace(/[₹,]/g, ''));
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return isAscending ? aNum - bNum : bNum - aNum;
        }
        
        // Sort as strings
        return isAscending ? aText.localeCompare(bText) : bText.localeCompare(aText);
    });
    
    // Reorder DOM
    rows.forEach(row => tbody.appendChild(row));
}

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR'
    }).format(amount);
}

function formatPercentage(value) {
    return new Intl.NumberFormat('en-IN', {
        style: 'percent',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value / 100);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Export functions for global use
window.clearFileSelection = clearFileSelection;
window.showAlert = showAlert;
window.formatCurrency = formatCurrency;
window.formatPercentage = formatPercentage;
