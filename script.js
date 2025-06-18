window.Telegram.WebApp.ready();

const tg = window.Telegram.WebApp;
const user = tg.initDataUnsafe?.user;

if (user) {
  document.getElementById("username").innerText = `👤 ${user.first_name}`;
  document.getElementById("userName").innerText = `👤 ${user.first_name}`;
} else {
  document.getElementById("username").innerText = "❗ Требуется авторизация в Telegram";
  document.getElementById("userName").innerText = "❗ Неизвестный пользователь";
}


// Инициализация приложения
document.addEventListener('DOMContentLoaded', function() {
    initTelegramApp();
    setupNavigation();
    loadUserData();
    loadReadingsHistory();
});

function initTelegramApp() {
    // Настройка Telegram WebApp
    tg.ready();
    tg.expand();
    
    // Применение темы Telegram
    document.documentElement.style.setProperty('--tg-theme-bg-color', tg.themeParams.bg_color || '#ffffff');
    document.documentElement.style.setProperty('--tg-theme-text-color', tg.themeParams.text_color || '#000000');
    document.documentElement.style.setProperty('--tg-theme-hint-color', tg.themeParams.hint_color || '#999999');
    document.documentElement.style.setProperty('--tg-theme-button-color', tg.themeParams.button_color || '#2481cc');
    document.documentElement.style.setProperty('--tg-theme-button-text-color', tg.themeParams.button_text_color || '#ffffff');
    document.documentElement.style.setProperty('--tg-theme-secondary-bg-color', tg.themeParams.secondary_bg_color || '#f1f1f1');
    
    // Отображение информации о пользователе
    if (user) {
        document.getElementById('userName').textContent = user.first_name + (user.last_name ? ' ' + user.last_name : '');
    }
    
    // Настройка главной кнопки
    tg.MainButton.setText('Готово');
    tg.MainButton.hide();
}

function setupNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');
    const sections = document.querySelectorAll('.content-section');
    
    navButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetSection = button.dataset.section;
            
            // Убираем активные классы
            navButtons.forEach(btn => btn.classList.remove('active'));
            sections.forEach(section => section.classList.remove('active'));
            
            // Добавляем активные классы
            button.classList.add('active');
            document.getElementById(targetSection + '-section').classList.add('active');
            
            // Haptic feedback
            tg.HapticFeedback.impactOccurred('light');
        });
    });
}

async function loadUserData() {
    try {
        if (!user) return;
        
        const response = await fetch(`/api/user/${user.id}`);
        if (response.ok) {
            const userData = await response.json();
            
            // Отображение лицевого счета
            document.getElementById('accountNumber').textContent = userData.account_number || `${user.id}${Math.floor(Math.random() * 1000)}`;
            
            // Последние показания
            if (userData.last_reading) {
                document.getElementById('lastReading').textContent = userData.last_reading.value + ' кВт·ч';
            }
        } else {
            // Генерируем временные данные для демонстрации
            document.getElementById('accountNumber').textContent = `${user.id}${Math.floor(Math.random() * 1000)}`;
        }
    } catch (error) {
        console.error('Ошибка загрузки данных пользователя:', error);
    }
}

async function loadReadingsHistory() {
    try {
        const historyContainer = document.getElementById('historyList');
        
        if (!user) {
            historyContainer.innerHTML = '<div class="loading">Требуется авторизация в Telegram</div>';
            return;
        }
        
        const response = await fetch(`/api/readings/${user.id}`);
        
        if (response.ok) {
            const readings = await response.json();
            displayReadingsHistory(readings);
        } else {
            // Отображаем демо-данные
            const demoReadings = generateDemoReadings();
            displayReadingsHistory(demoReadings);
        }
    } catch (error) {
        console.error('Ошибка загрузки истории:', error);
        document.getElementById('historyList').innerHTML = '<div class="loading">Ошибка загрузки данных</div>';
    }
}

function generateDemoReadings() {
    const readings = [];
    const currentDate = new Date();
    
    for (let i = 0; i < 6; i++) {
        const date = new Date(currentDate);
        date.setMonth(date.getMonth() - i);
        
        readings.push({
            id: i + 1,
            value: 12000 + (i * 150) + Math.floor(Math.random() * 100),
            date: date.toISOString(),
            status: 'confirmed'
        });
    }
    
    return readings.reverse();
}

function displayReadingsHistory(readings) {
    const historyContainer = document.getElementById('historyList');
    
    if (!readings || readings.length === 0) {
        historyContainer.innerHTML = '<div class="loading">История показаний пуста</div>';
        return;
    }
    
    const historyHTML = readings.map(reading => {
        const date = new Date(reading.date);
        const formattedDate = date.toLocaleDateString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
        
        return `
            <div class="history-item">
                <div>
                    <div class="history-value">${reading.value.toLocaleString('ru-RU')} кВт·ч</div>
                    <div class="history-date">${formattedDate}</div>
                </div>
                <div class="history-status">Принято</div>
            </div>
        `;
    }).join('');
    
    historyContainer.innerHTML = historyHTML;
}

// Обработка формы показаний
document.getElementById('readingsForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const readingValue = document.getElementById('currentReading').value;
    
    if (!readingValue || readingValue <= 0) {
        showNotification('Введите корректные показания', 'error');
        return;
    }
    
    // Haptic feedback
    tg.HapticFeedback.impactOccurred('medium');
    
    try {
        await submitReading(readingValue);
        showNotification('Показания успешно переданы!');
        
        // Очистка формы
        document.getElementById('currentReading').value = '';
        
        // Обновление истории
        setTimeout(() => {
            loadReadingsHistory();
        }, 1000);
        
    } catch (error) {
        console.error('Ошибка отправки показаний:', error);
        showNotification('Ошибка отправки показаний', 'error');
    }
});

async function submitReading(value) {
    if (!user) {
        throw new Error('Пользователь не авторизован');
    }
    
    const response = await fetch('/api/readings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            telegram_id: user.id,
            reading_value: parseInt(value),
            user_data: user
        })
    });
    
    if (!response.ok) {
        throw new Error('Ошибка сервера');
    }
    
    return response.json();
}

function showNotification(message, type = 'success') {
    // Удаляем предыдущие уведомления
    const existingNotification = document.querySelector('.notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // Создаем новое уведомление
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Показываем уведомление
    setTimeout(() => {
        notification.classList.add('show');
    }, 100);
    
    // Скрываем через 3 секунды
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

// Функции для услуг
function orderMeterReplacement() {
    tg.HapticFeedback.impactOccurred('light');
    
    if (user) {
        // Отправляем данные боту
        tg.sendData(JSON.stringify({
            action: 'order_meter_replacement',
            user_id: user.id
        }));
    } else {
        showNotification('Требуется авторизация в Telegram', 'error');
    }
}

function orderMeterCheck() {
    tg.HapticFeedback.impactOccurred('light');
    
    if (user) {
        tg.sendData(JSON.stringify({
            action: 'order_meter_check',
            user_id: user.id
        }));
    } else {
        showNotification('Требуется авторизация в Telegram', 'error');
    }
}

function orderConsultation() {
    tg.HapticFeedback.impactOccurred('light');
    
    if (user) {
        tg.sendData(JSON.stringify({
            action: 'order_consultation',
            user_id: user.id
        }));
    } else {
        showNotification('Требуется авторизация в Telegram', 'error');
    }
}

function openChat() {
    tg.HapticFeedback.impactOccurred('light');
    
    if (user) {
        tg.sendData(JSON.stringify({
            action: 'open_support_chat',
            user_id: user.id
        }));
    } else {
        showNotification('Требуется авторизация в Telegram', 'error');
    }
}

// Обработка событий Telegram WebApp
tg.onEvent('mainButtonClicked', function() {
    tg.close();
});

tg.onEvent('backButtonClicked', function() {
    tg.close();
});

// Обработка изменения viewport
window.addEventListener('resize', function() {
    // Корректировка высоты при открытии клавиатуры
    const vh = window.innerHeight * 0.01;
    document.documentElement.style.setProperty('--vh', `${vh}px`);
});

// Предотвращение масштабирования
document.addEventListener('touchstart', function(event) {
    if (event.touches.length > 1) {
        event.preventDefault();
    }
});

let lastTouchEnd = 0;
document.addEventListener('touchend', function(event) {
    const now = (new Date()).getTime();
    if (now - lastTouchEnd <= 300) {
        event.preventDefault();
    }
    lastTouchEnd = now;
}, false);

// Дебаг информация (только в режиме разработки)
if (tg.initDataUnsafe?.user?.id === 123456789) {
    console.log('Telegram WebApp Debug Info:', {
        platform: tg.platform,
        version: tg.version,
        user: user,
        themeParams: tg.themeParams,
        isExpanded: tg.isExpanded,
        viewportHeight: tg.viewportHeight,
        viewportStableHeight: tg.viewportStableHeight
    });
}