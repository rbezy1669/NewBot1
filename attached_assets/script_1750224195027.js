const promoList = [
  {
    id: 1,
    title: "Скидка 15% на оплату электроэнергии онлайн",
    description: "Оплачивайте счета через личный кабинет и получайте скидку 15%. Быстро и удобно!",
    type: "discount",
  },
  {
    id: 2,
    title: "Бесплатная консультация по энергосбережению",
    description: "Наши специалисты помогут снизить расходы на электроэнергию в вашем доме.",
    type: "consult",
  },
  {
    id: 3,
    title: "Акция для новых клиентов",
    description: "Подключайтесь к Энергосбыту и получите скидку 10% на первый счет.",
    type: "promo",
  },
  {
    id: 4,
    title: "Программа лояльности",
    description: "Накопите баллы за оплату и обменяйте их на полезные подарки и услуги.",
    type: "loyalty",
  },
];

const promoListContainer = document.getElementById("promoList");
const filterButtons = document.querySelectorAll(".filter-btn");
const subscribeForm = document.getElementById("subscribeForm");
const emailInput = document.getElementById("emailInput");
const subscribeMessage = document.getElementById("subscribeMessage");

// Показываем карточки с анимацией
function animateCard(card, delay) {
  setTimeout(() => {
    card.classList.add("show");
  }, delay);
}

function renderPromos(filter = "all") {
  promoListContainer.innerHTML = "";
  const filteredPromos =
    filter === "all"
      ? promoList
      : promoList.filter((promo) => promo.type === filter);

  if (filteredPromos.length === 0) {
    promoListContainer.innerHTML = "<p>Акций не найдено.</p>";
    return;
  }

  filteredPromos.forEach((promo, index) => {
    const card = document.createElement("div");
    card.className = "promo-card";
    card.tabIndex = 0; // для доступа с клавиатуры
    card.onclick = () => showPromoDetails(promo.id);
    card.onkeypress = (e) => {
      if (e.key === "Enter" || e.key === " ") {
        showPromoDetails(promo.id);
      }
    };

    card.innerHTML = `
      <div class="promo-title">${promo.title}</div>
      <div class="promo-desc">${promo.description}</div>
    `;

    promoListContainer.appendChild(card);

    animateCard(card, index * 150);
  });
}

function showPromoDetails(id) {
  const promo = promoList.find((p) => p.id === id);
  if (promo) {
    alert(`${promo.title}\n\n${promo.description}`);
  }
}

// Фильтрация
filterButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    filterButtons.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    renderPromos(btn.dataset.type);
  });
});

// Подписка на новости
subscribeForm.addEventListener("submit", (e) => {
  e.preventDefault();
  subscribeMessage.textContent = "";
  const email = emailInput.value.trim();

  if (!email) {
    subscribeMessage.textContent = "Введите email.";
    emailInput.focus();
    return;
  }

  if (!validateEmail(email)) {
    subscribeMessage.textContent = "Введите корректный email.";
    emailInput.focus();
    return;
  }

  // Здесь можно отправлять email на сервер
  subscribeMessage.textContent = "Спасибо за подписку!";
  subscribeForm.reset();
});

function validateEmail(email) {
  // Простая проверка email
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email.toLowerCase());
}

// Инициализация страницы
renderPromos();
