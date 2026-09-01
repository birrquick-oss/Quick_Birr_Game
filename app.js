/* =========================================================
   QUICK_BIRR GAMES
   Frontend Controller (Updated with User Init & Modals)
   ========================================================= */

const tg = window.Telegram?.WebApp;

/* =========================
   TELEGRAM INIT
========================= */
let userData = {
    user_id: null,
    first_name: "Guest",
    last_name: "",
    username: "",
    balance: 0.00
};

if (tg) {
    tg.ready();
    tg.expand();

    try {
        tg.setHeaderColor("#0d1119");
        tg.setBackgroundColor("#0d1119");
    } catch (error) {
        console.log("Telegram UI setup skipped");
    }
}

/* =========================
   ELEMENTS
========================= */
const modal = document.getElementById("messageModal");
const modalTitle = document.getElementById("modalTitle");
const modalMessage = document.getElementById("modalMessage");
const modalIcon = document.getElementById("modalIcon");

const balanceEl = document.getElementById("balance");
const dashBalanceEl = document.getElementById("dashBalance");
const profileNameEl = document.getElementById("profileName");
const profilePhoneEl = document.getElementById("profilePhone");

const homeView = document.getElementById("homeView");
const profileView = document.getElementById("profileView");

const depositModal = document.getElementById("depositModal");
const withdrawModal = document.getElementById("withdrawModal");

/* =========================
   MODALS (MESSAGE & FORM MODALS)
========================= */
function showMessage(title, message, icon = "🎮") {
    if (!modal) return;
    modalTitle.textContent = title;
    modalMessage.textContent = message;
    modalIcon.textContent = icon;
    modal.hidden = false;
}

function closeMessage() {
    if (modal) modal.hidden = true;
}

function openDepositModal() {
    if (depositModal) depositModal.hidden = false;
}

function openWithdrawModal() {
    if (withdrawModal) withdrawModal.hidden = false;
}

function closeModals() {
    if (depositModal) depositModal.hidden = true;
    if (withdrawModal) withdrawModal.hidden = true;
}

// Close Button Events
document.getElementById("modalClose")?.addEventListener("click", closeMessage);
document.getElementById("modalButton")?.addEventListener("click", closeMessage);

document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", () => {
        closeMessage();
        closeModals();
    });
});

/* =========================
   DEPOSIT & WITHDRAW ACTIONS
========================= */
document.getElementById("depositButton")?.addEventListener("click", openDepositModal);
document.getElementById("dashDepositBtn")?.addEventListener("click", openDepositModal);

document.getElementById("withdrawButton")?.addEventListener("click", openWithdrawModal);
document.getElementById("dashWithdrawBtn")?.addEventListener("click", openWithdrawModal);

/* =========================
   GAME CARDS
========================= */
document.querySelectorAll(".game-card").forEach(card => {
    card.addEventListener("click", () => {
        const game = card.dataset.game;

        if (game === "bingo") {
            showMessage(
                "QUICK BIRR BINGO",
                "Bingo 1–1000 will be available here.",
                "🎱"
            );
            return;
        }

        const names = {
            slots: "Lucky Slots",
            plinko: "Plinko",
            roulette: "European Roulette",
            blackjack: "Blackjack",
            mines: "Mines"
        };

        showMessage(
            names[game] || "Game",
            "This game is coming soon.",
            "🎮"
        );
    });
});

/* =========================
   PLAY NOW & SEE ALL
========================= */
document.getElementById("playNowButton")?.addEventListener("click", () => {
    if (homeView && homeView.hidden) {
        showPage("home");
    }
    document.querySelector(".games-section")?.scrollIntoView({ behavior: "smooth" });
});

document.getElementById("seeAllButton")?.addEventListener("click", () => {
    document.querySelector(".games-section")?.scrollIntoView({ behavior: "smooth" });
});

/* =========================
   BALANCE FETCH & REFRESH
========================= */
async function fetchUserBalance() {
    if (!userData.user_id) return;

    try {
        const response = await fetch(`/api/user/balance?user_id=${userData.user_id}`);
        if (response.ok) {
            const data = await response.json();
            userData.balance = parseFloat(data.balance || 0).toFixed(2);
            updateBalanceUI(userData.balance);
        }
    } catch (error) {
        console.error("Balance fetch error:", error);
    }
}

function updateBalanceUI(amount) {
    const formatted = `${amount} ETB`;
    if (balanceEl) balanceEl.textContent = formatted;
    if (dashBalanceEl) dashBalanceEl.textContent = formatted;
}

document.getElementById("balanceButton")?.addEventListener("click", () => {
    fetchUserBalance();
});

/* =========================
   BOTTOM NAV & PAGE SWITCHING
========================= */
function showPage(pageName) {
    document.querySelectorAll(".nav-item").forEach(nav => {
        if (nav.dataset.page === pageName) {
            nav.classList.add("active");
        } else {
            nav.classList.remove("active");
        }
    });

    if (pageName === "profile") {
        if (homeView) homeView.hidden = true;
        if (profileView) profileView.hidden = false;
        window.scrollTo({ top: 0, behavior: "smooth" });
    } else {
        if (profileView) profileView.hidden = true;
        if (homeView) homeView.hidden = false;
    }
}

document.querySelectorAll(".nav-item").forEach(item => {
    item.addEventListener("click", () => {
        const page = item.dataset.page;

        if (page === "home") {
            showPage("home");
            window.scrollTo({ top: 0, behavior: "smooth" });
        } else if (page === "games") {
            showPage("home");
            document.querySelector(".games-section")?.scrollIntoView({ behavior: "smooth" });
        } else if (page === "promo") {
            showPage("home");
            document.querySelector(".promo-card")?.scrollIntoView({ behavior: "smooth" });
        } else if (page === "profile") {
            showPage("profile");
        }
    });
});

/* =========================
   TELEGRAM USER INITIALIZATION
========================= */
function loadTelegramUser() {
    if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
        const user = tg.initDataUnsafe.user;
        userData.user_id = user.id;
        userData.first_name = user.first_name || "User";
        userData.last_name = user.last_name || "";
        userData.username = user.username ? `@${user.username}` : "";

        const fullName = `${userData.first_name} ${userData.last_name}`.trim();

        // Top bar እና Profile view ላይ መረጃዎችን መሙላት
        if (profileNameEl) profileNameEl.textContent = fullName;
        if (profilePhoneEl) profilePhoneEl.textContent = userData.username || `ID: ${userData.user_id}`;

        fetchUserBalance();
    } else {
        console.log("Running outside Telegram Mini App context.");
        if (profileNameEl) profileNameEl.textContent = "Guest User";
        if (profilePhoneEl) profilePhoneEl.textContent = "No Telegram ID";
    }
}

/* =========================
   INITIAL EXECUTION
========================= */
document.addEventListener("DOMContentLoaded", () => {
    loadTelegramUser();
    updateBalanceUI("0.00");
    if (document.getElementById("playerCount")) {
        document.getElementById("playerCount").textContent = "0";
    }
});
