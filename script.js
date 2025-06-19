// Global variables
let tg = window.Telegram?.WebApp;
let currentUser = null;
let selectedMeterType = 'electric';
let consumptionChart = null;

// Initialize Telegram WebApp
function initTelegramApp() {
    if (tg) {
        tg.ready();
        tg.expand();
        tg.setHeaderColor('#667eea');
        tg.setBackgroundColor('#ffffff');
        
        // Apply Telegram theme
        if (tg.themeParams) {
            document.documentElement.style.setProperty('--tg-bg-color', tg.themeParams.bg_color || '#ffffff');
            document.documentElement.style.setProperty('--tg-text-color', tg.themeParams.text_color || '#000000');
            document.documentElement.style.setProperty('--tg-button-color', tg.themeParams.button_color || '#2ea6ff');
        }
        
        // Set main button
        tg.MainButton.setText('ПЕРЕДАТЬ ПОКАЗАНИЯ');
        tg.MainButton.onClick(submitReading);
        
        console.log('Telegram WebApp инициализирован');
    } else {
        console.warn('Telegram WebApp не инициализирован');
        // Fallback for web testing
        currentUser = {
            id: 'demo_user',
            first_name: 'Демо',
            last_name: 'Пользователь'
        };
        updateUserInfo();
    }
}

// Load user data
async function loadUserData() {
    try {
        const telegramId = tg?.initDataUnsafe?.user?.id || 'demo_user';
        
        // Update user info
        const user = tg?.initDataUnsafe?.user || {
            first_name: 'Демо',
            last_name: 'Пользователь'
        };
        
        currentUser = user;
        updateUserInfo();
        
        // Load user statistics
        await loadUserStats(telegramId);
        
    } catch (error) {
        console.error('Ошибка загрузки данных пользователя:', error);
        // showNotification('Ошибка загрузки данных пользователя', 'error');
    }
}

// Update user info display
function updateUserInfo() {
    if (!currentUser) return;
    
    const fullName = `${currentUser.first_name || ''} ${currentUser.last_name || ''}`.trim();
    const avatar = (currentUser.first_name || 'У')[0].toUpperCase();
    
    document.getElementById('userAvatar').textContent = avatar;
    document.getElementById('userName').textContent = fullName || 'Пользователь';
    document.getElementById('userStatus').textContent = 'Система готова к работе';
}

// Load user statistics
async function loadUserStats(telegramId) {
    try {
        const response = await fetch(`/api/readings/${telegramId}`);
        if (response.ok) {
            const data = await response.json();
            updateStatsDisplay(data.readings || []);
            updateHistoryDisplay(data.readings || []);
            updateChart(data.readings || []);
            updateDebtBlock();
        } else {
            // Generate demo data for display
            const demoReadings = generateDemoReadings();
            updateStatsDisplay(demoReadings);
            updateHistoryDisplay(demoReadings);
            updateChart(demoReadings);
    updateDebtBlock();
        }
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
        // Show demo data on error
        const demoReadings = generateDemoReadings();
        updateStatsDisplay(demoReadings);
        updateHistoryDisplay(demoReadings);
        updateChart(demoReadings);
    updateDebtBlock();
    }
}

// Generate demo readings for display
function generateDemoReadings() {
    const readings = [];
    const now = new Date();
    
    for (let i = 0; i < 12; i++) {
        const date = new Date(now);
        date.setMonth(date.getMonth() - i);
        
        readings.push({
            id: i + 1,
            reading_value: 1250 + Math.floor(Math.random() * 200) + (i * 50),
            meter_type: 'electric',
            reading_date: date.toISOString(),
            status: 'processed'
        });
    }
    
    return readings.reverse();
}

// Update statistics display
function updateStatsDisplay(readings) {
    if (!readings || readings.length === 0) {
        document.getElementById('currentReading').textContent = '-';
        document.getElementById('monthlyUsage').textContent = '-';
        document.getElementById('totalReadings').textContent = '0';
        document.getElementById('nextPayment').textContent = '-';
        return;
    }
    
    const latest = readings[readings.length - 1];
    const previous = readings[readings.length - 2];
    
    const currentReading = latest?.reading_value || 0;
    const monthlyUsage = previous ? (currentReading - previous.reading_value) : 0;
    const totalReadings = readings.length;
    const estimatedPayment = monthlyUsage * 5.5; // Примерная стоимость за кВт/ч
    
    document.getElementById('currentReading').textContent = currentReading.toLocaleString();
    document.getElementById('monthlyUsage').textContent = monthlyUsage > 0 ? `${monthlyUsage} кВт/ч` : '-';
    document.getElementById('totalReadings').textContent = totalReadings;
    document.getElementById('nextPayment').textContent = estimatedPayment > 0 ? `${Math.round(estimatedPayment)} ₽` : '-';
}

// Update history display
function updateHistoryDisplay(readings) {
    const historyList = document.getElementById('historyList');
    
    if (!readings || readings.length === 0) {
        historyList.innerHTML = `
            <div style="text-align: center; padding: 20px; color: #666;">
                История показаний пуста
            </div>
        `;
        return;
    }
    
    const historyHTML = readings.slice(-10).reverse().map(reading => {
        const date = new Date(reading.reading_date).toLocaleDateString('ru-RU');
        const meterIcon = getMeterIcon(reading.meter_type);
        const statusColor = getStatusColor(reading.status);
        
        return `
            <div class="history-item">
                <div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span>${meterIcon}</span>
                        <span class="history-date">${date}</span>
                    </div>
                    <div style="font-size: 12px; color: ${statusColor}; margin-top: 2px;">
                        ${getStatusText(reading.status)}
                    </div>
                </div>
                <div class="history-value">
                    ${reading.reading_value.toLocaleString()}
                </div>
            </div>
        `;
    }).join('');
    
    historyList.innerHTML = historyHTML;
}

// Get meter icon
function getMeterIcon(type) {
    switch (type) {
        case 'electric': return '⚡';
        case 'gas': return '🔥';
        case 'water': return '💧';
        default: return '📊';
    }
}

// Get status color
function getStatusColor(status) {
    switch (status) {
        case 'processed': return '#28a745';
        case 'submitted': return '#ffc107';
        case 'verified': return '#007bff';
        default: return '#6c757d';
    }
}

// Get status text
function getStatusText(status) {
    switch (status) {
        case 'processed': return 'Обработано';
        case 'submitted': return 'Отправлено';
        case 'verified': return 'Проверено';
        default: return 'Неизвестно';
    }
}

// Update chart
function updateChart(readings) {
    const ctx = document.getElementById('consumptionChart');
    if (!ctx) return;
    
    // Destroy existing chart
    if (consumptionChart) {
        consumptionChart.destroy();
    }
    
    const labels = readings.slice(-6).map(r => {
        const date = new Date(r.reading_date);
        return date.toLocaleDateString('ru-RU', { month: 'short', day: 'numeric' });
    });
    
    const data = readings.slice(-6).map(r => r.reading_value);
    
    consumptionChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Показания счётчика',
                data: data,
                borderColor: '#007aff',
                backgroundColor: 'rgba(0, 122, 255, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#007aff',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: false,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                }
            }
        }
    });
}

// Tab switching
function showTab(tabName) {
    // Remove active class from all tabs and contents
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // Add active class to selected tab and content
    event.target.classList.add('active');
    document.getElementById(`${tabName}-tab`).classList.add('active');
    
    // Load data for specific tabs
    if (tabName === 'history' && !consumptionChart) {
        setTimeout(() => {
            const telegramId = tg?.initDataUnsafe?.user?.id || 'demo_user';
            loadUserStats(telegramId);
        }, 100);
    }
}

// Meter type selection
document.addEventListener('DOMContentLoaded', function() {
    const meterTypes = document.querySelectorAll('.meter-type');
    meterTypes.forEach(type => {
        type.addEventListener('click', function() {
            meterTypes.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            selectedMeterType = this.dataset.type;
        });
    });
});

// Submit reading
async function submitReading() {
    const readingValue = document.getElementById('readingValue').value;
    const readingNote = document.getElementById('readingNote').value;
    
    if (!readingValue || readingValue <= 0) {
        showNotification('Пожалуйста, введите корректные показания', 'error');
        return;
    }
    
    const telegramId = tg?.initDataUnsafe?.user?.id || 'demo_user';
    
    // Show loading state
    const submitBtn = document.querySelector('.btn-primary');
    const submitText = document.getElementById('submitText');
    const submitLoading = document.getElementById('submitLoading');
    
    submitBtn.disabled = true;
    submitText.style.display = 'none';
    submitLoading.style.display = 'inline-block';
    
    try {
        const response = await fetch('/api/readings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                telegram_id: parseInt(telegramId),
                reading_value: parseInt(readingValue),
                meter_type: selectedMeterType,
                notes: readingNote
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            showNotification('Показания успешно переданы!', 'success');
            
            // Clear form
            document.getElementById('readingValue').value = '';
            document.getElementById('readingNote').value = '';
            
            // Refresh data
            await loadUserStats(telegramId);
            
            // Haptic feedback
            if (tg?.HapticFeedback) {
                tg.HapticFeedback.impactOccurred('medium');
            }
            
            // Hide main button
            if (tg?.MainButton) {
                tg.MainButton.hide();
            }
            
        } else {
            const error = await response.json();
            throw new Error(error.detail || 'Ошибка при передаче показаний');
        }
        
    } catch (error) {
        console.error('Ошибка отправки показаний:', error);
        showNotification('Ошибка при передаче показаний. Попробуйте еще раз.', 'error');
    } finally {
        // Restore button state
        submitBtn.disabled = false;
        submitText.style.display = 'inline';
        submitLoading.style.display = 'none';
    }
}

// Quick reading function
function quickReading() {
    showTab('readings');
    document.getElementById('readingValue').focus();
}

// Service ordering
async function orderService(serviceType) {
    const telegramId = tg?.initDataUnsafe?.user?.id || 'demo_user';
    
    const serviceNames = {
        'meter_replacement': 'Замена счётчика',
        'consultation': 'Консультация',
        'inspection': 'Проверка счётчика',
        'repair': 'Ремонт'
    };
    
    const serviceName = serviceNames[serviceType] || serviceType;
    
    try {
        const response = await fetch('/api/service-request', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                telegram_id: parseInt(telegramId),
                service_type: serviceType,
                description: `Заявка на ${serviceName.toLowerCase()}`
            })
        });
        
        if (response.ok) {
            showNotification(`Заявка на "${serviceName}" успешно создана!`, 'success');
            
            if (tg?.HapticFeedback) {
                tg.HapticFeedback.impactOccurred('light');
            }
        } else {
            const errorData = await response.json().catch(() => ({ detail: 'Неизвестная ошибка' }));
            throw new Error(errorData.detail || 'Ошибка при создании заявки');
        }
        
    } catch (error) {
        console.error('Ошибка заказа услуги:', error);
        showNotification('Ошибка при создании заявки. Попробуйте еще раз.', 'error');
    }
}

// Support functions
function openSupport() {
    if (tg) {
        tg.openTelegramLink('https://t.me/energosbyt_support_bot');
    } else {
        showNotification('Поддержка доступна только в Telegram', 'info');
    }
}

function openFAQ() {
    showNotification('Раздел FAQ в разработке', 'info');
}

// Show notification
function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    const notificationText = document.getElementById('notificationText');
    
    notificationText.textContent = message;
    notification.className = `notification ${type}`;
    notification.classList.add('show');
    
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

// Monitor reading input
document.addEventListener('DOMContentLoaded', function() {
    const readingInput = document.getElementById('readingValue');
    if (readingInput) {
        readingInput.addEventListener('input', function() {
            const value = this.value;
            if (value && value > 0) {
                if (tg?.MainButton) {
                    tg.MainButton.show();
                }
            } else {
                if (tg?.MainButton) {
                    tg.MainButton.hide();
                }
            }
        });
    }
});

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initTelegramApp();
    loadUserData();
    
    // Add smooth scrolling
    document.documentElement.style.scrollBehavior = 'smooth';
});

// Handle visibility changes
document.addEventListener('visibilitychange', function() {
    if (!document.hidden) {
        // Refresh data when app becomes visible
        const telegramId = tg?.initDataUnsafe?.user?.id || 'demo_user';
        loadUserStats(telegramId);
    }
});

// Error handling for network issues
window.addEventListener('online', function() {
    showNotification('Соединение восстановлено', 'success');
});

window.addEventListener('offline', function() {
    showNotification('Соединение потеряно', 'error');
});
function updateDebtBlock() {
  const stat = document.getElementById("statDebt");
  if (stat) {
    stat.innerText = "-3 876,55 ₽";
    stat.style.color = "red";
    stat.style.fontWeight = "bold";
  }
}




function updateDebtBlock() {
  const stat = document.getElementById("statDebt");
  if (stat) {
    stat.innerText = "-3 876,55 ₽";
    stat.style.color = "red";
    stat.style.fontWeight = "bold";
  }
}

updateDebtBlock();
