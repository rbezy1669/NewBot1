document.addEventListener('DOMContentLoaded', function() {
    window.tg = window.Telegram.WebApp;
    window.user = window.tg?.initDataUnsafe?.user;

    if (!window.tg || !window.user) {
        console.warn("Telegram WebApp не инициализирован");
        return;
    }

    console.log("Telegram user:", window.user);

    initTelegramApp();
    setupNavigation();
    loadUserData();
    loadReadingsHistory();
});

function initTelegramApp() {
    window.tg.ready();
    window.tg.expand();

    document.documentElement.style.setProperty('--tg-theme-bg-color', window.tg.themeParams.bg_color || '#ffffff');
    document.documentElement.style.setProperty('--tg-theme-text-color', window.tg.themeParams.text_color || '#000000');
    document.documentElement.style.setProperty('--tg-theme-hint-color', window.tg.themeParams.hint_color || '#999999');
    document.documentElement.style.setProperty('--tg-theme-button-color', window.tg.themeParams.button_color || '#2481cc');
    document.documentElement.style.setProperty('--tg-theme-button-text-color', window.tg.themeParams.button_text_color || '#ffffff');
    document.documentElement.style.setProperty('--tg-theme-secondary-bg-color', window.tg.themeParams.secondary_bg_color || '#f1f1f1');

    if (window.user) {
        const userNameEl = document.getElementById('userName');
        if (userNameEl) {
            userNameEl.textContent = window.user.first_name + (window.user.last_name ? ' ' + window.user.last_name : '');
        }
    }

    window.tg.MainButton.setText('Готово');
    window.tg.MainButton.hide();
}

function setupNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');
    const sections = document.querySelectorAll('.content-section');

    navButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetSection = button.dataset.section;

            navButtons.forEach(btn => btn.classList.remove('active'));
            sections.forEach(section => section.classList.remove('active'));

            button.classList.add('active');
            const sectionEl = document.getElementById(targetSection + '-section');
            if (sectionEl) sectionEl.classList.add('active');

            window.tg.HapticFeedback.impactOccurred('light');
        });
    });
}

async function loadUserData() {
    try {
        if (!window.user) return;

        const response = await fetch(`/api/user/${window.user.id}`);
        if (response.ok) {
            const userData = await response.json();

            const accountEl = document.getElementById('accountNumber');
            if (accountEl) {
                accountEl.textContent = userData.account_number || `${window.user.id}${Math.floor(Math.random() * 1000)}`;
            }

            if (userData.last_reading) {
                const lastReadingEl = document.getElementById('lastReading');
                if (lastReadingEl) {
                    lastReadingEl.textContent = userData.last_reading.value + ' кВт·ч';
                }
            }
        } else {
            const accountEl = document.getElementById('accountNumber');
            if (accountEl) {
                accountEl.textContent = `${window.user.id}${Math.floor(Math.random() * 1000)}`;
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки данных пользователя:', error);
    }
}

async function loadReadingsHistory() {
    try {
        const historyContainer = document.getElementById('historyList');

        if (!window.user) {
            if (historyContainer) historyContainer.innerHTML = '<div class="loading">Требуется авторизация в Telegram</div>';
            return;
        }

        const response = await fetch(`/api/readings/${window.user.id}`);

        if (response.ok) {
            const readings = await response.json();
            displayReadingsHistory(readings);
        } else {
            displayReadingsHistory(generateDemoReadings());
        }
    } catch (error) {
        console.error('Ошибка загрузки истории:', error);
        const historyContainer = document.getElementById('historyList');
        if (historyContainer) historyContainer.innerHTML = '<div class="loading">Ошибка загрузки данных</div>';
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
    if (!historyContainer) return;

    if (!readings || readings.length === 0) {
        historyContainer.innerHTML = '<div class="loading">История показаний пуста</div>';
        return;
    }

    const historyHTML = readings.map(reading => {
        const date = new Date(reading.date);
        const formattedDate = date.toLocaleDateString('ru-RU', {
            day: '2-digit', month: '2-digit', year: 'numeric'
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

document.getElementById('readingsForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const readingInput = document.getElementById('currentReading');
    if (!readingInput) return;

    const readingValue = readingInput.value;
    if (!readingValue || readingValue <= 0) {
        showNotification('Введите корректные показания', 'error');
        return;
    }

    window.tg.HapticFeedback.impactOccurred('medium');

    try {
        await submitReading(readingValue);
        showNotification('Показания успешно переданы!');
        readingInput.value = '';
        setTimeout(() => loadReadingsHistory(), 1000);
    } catch (error) {
        console.error('Ошибка отправки показаний:', error);
        showNotification('Ошибка отправки показаний', 'error');
    }
});

async function submitReading(value) {
    if (!window.user) throw new Error('Пользователь не авторизован');

    const response = await fetch('/api/readings', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ telegram_id: window.user.id, reading_value: parseInt(value), user_data: window.user })
    });

    if (!response.ok) throw new Error('Ошибка сервера');
    return response.json();
}

function showNotification(message, type = 'success') {
    const existing = document.querySelector('.notification');
    if (existing) existing.remove();

    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => notification.classList.add('show'), 100);
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function orderMeterReplacement() {
    window.tg.HapticFeedback.impactOccurred('light');
    if (window.user) {
        window.tg.sendData(JSON.stringify({ action: 'order_meter_replacement', user_id: window.user.id }));
    } else {
        showNotification('Требуется авторизация в Telegram', 'error');
    }
}

function orderConsultation() {
    window.tg.HapticFeedback.impactOccurred('light');
    if (window.user) {
        window.tg.sendData(JSON.stringify({ action: 'order_consultation', user_id: window.user.id }));
    } else {
        showNotification('Требуется авторизация в Telegram', 'error');
    }
}

function openChat() {
    window.tg.HapticFeedback.impactOccurred('light');
    if (window.user) {
        window.tg.sendData(JSON.stringify({ action: 'open_support_chat', user_id: window.user.id }));
    } else {
        showNotification('Требуется авторизация в Telegram', 'error');
    }
}

if (window.tg?.onEvent) {
    window.tg.onEvent('mainButtonClicked', () => window.tg.close());
    window.tg.onEvent('backButtonClicked', () => window.tg.close());
}

window.addEventListener('resize', function() {
    const vh = window.innerHeight * 0.01;
    document.documentElement.style.setProperty('--vh', `${vh}px`);
});

document.addEventListener('touchstart', function(event) {
    if (event.touches.length > 1) event.preventDefault();
});

let lastTouchEnd = 0;
document.addEventListener('touchend', function(event) {
    const now = Date.now();
    if (now - lastTouchEnd <= 300) event.preventDefault();
    lastTouchEnd = now;
}, false);

if (window.user?.id === 123456789) {
    console.log('Telegram WebApp Debug Info:', {
        platform: window.tg.platform,
        version: window.tg.version,
        user: window.user,
        themeParams: window.tg.themeParams,
        isExpanded: window.tg.isExpanded,
        viewportHeight: window.tg.viewportHeight,
        viewportStableHeight: window.tg.viewportStableHeight
    });
}