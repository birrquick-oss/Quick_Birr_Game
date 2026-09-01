/* =========================================================
   QUICK_BIRR GAMES
   Frontend Controller (Full Integration with Backend)
   ========================================================= */

const tg = window.Telegram?.WebApp;

/* =========================
   TELEGRAM INIT & STATE
========================= */
let userData = {
    telegram_id: null,
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
    if (!modal) {
        alert(`${title}\n${message}`);
        return;
    }
    if (modalTitle) modalTitle.textContent = title;
    if (modalMessage) modalMessage.textContent = message;
    if (modalIcon) modalIcon.textContent = icon;
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
   BALANCE FETCH & USER SYNC
========================= */
async function syncAndFetchUser() {
    if (!userData.telegram_id) return;

    try {
        // 1. Get or Create user in Backend
        const userRes = await fetch('/api/users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_id: String(userData.telegram_id),
                telegram_username: userData.username,
                first_name: userData.first_name
            })
        });
        
        const userDataResult = await userRes.json();
        
        if (userDataResult.success && userDataResult.user) {
            userData.balance = parseFloat(userDataResult.user.balance || 0).toFixed(2);
            updateBalanceUI(userData.balance);
        }
    } catch (error) {
        console.error("User sync/balance fetch error:", error);
    }
}

function updateBalanceUI(amount) {
    const formatted = `${amount} ETB`;
    if (balanceEl) balanceEl.textContent = formatted;
    if (dashBalanceEl) dashBalanceEl.textContent = formatted;
}

document.getElementById("balanceButton")?.addEventListener("click", () => {
    syncAndFetchUser();
});

/* =========================
   FORM SUBMISSIONS (API CALLS)
========================= */
function setupFormSubmitListeners() {
    // Deposit Form Submit
    const depositForm = document.getElementById("deposit-form") || document.querySelector("#depositModal form");
    if (depositForm) {
        depositForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            const bankName = document.getElementById("deposit-bank")?.value || "CBE";
            const amount = parseFloat(document.getElementById("deposit-amount")?.value);
            const smsData = document.getElementById("deposit-sms")?.value;

            if (!amount || amount <= 0 || !smsData) {
                showMessage("የተሳሳተ መረጃ", "እባክዎን የገንዘብ መጠን እና የባንክ SMS መረጃውን በትክክል ይሙሉ!", "⚠️");
                return;
            }

            const payload = {
                telegram_id: String(userData.telegram_id),
                telegram_name: userData.first_name,
                amount: amount,
                bank_name: bankName,
                sms_data: smsData
            };

            try {
                const res = await fetch("/api/users/deposit", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();

                if (data.success) {
                    closeModals();
                    depositForm.reset();
                    showMessage("ተልኳል!", data.message, "✅");
                } else {
                    showMessage("ስህተት", data.message, "❌");
                }
            } catch (err) {
                console.error("Deposit Error:", err);
                showMessage("ስህተት", "የዲፖዚት ጥያቄ መላክ አልተቻለም!", "❌");
            }
        });
    }

    // Withdraw Form Submit
    const withdrawForm = document.getElementById("withdraw-form") || document.querySelector("#withdrawModal form");
    if (withdrawForm) {
        withdrawForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            const bankName = document.getElementById("withdraw-bank")?.value || "CBE";
            const accountNumber = document.getElementById("withdraw-account")?.value;
            const amount = parseFloat(document.getElementById("withdraw-amount")?.value);

            if (!amount || amount <= 0 || !accountNumber) {
                showMessage("የተሳሳተ መረጃ", "እባክዎን የባንክ ሂሳብ ቁጥር እና የማውጫ መጠን በትክክል ይሙሉ!", "⚠️");
                return;
            }

            const payload = {
                telegram_id: String(userData.telegram_id),
                amount: amount,
                bank_name: bankName,
                account_number: accountNumber
            };

            try {
                const res = await fetch("/api/users/withdraw", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();

                if (data.success) {
                    closeModals();
                    withdrawForm.reset();
                    showMessage("ተመዝግቧል!", data.message, "✅");
                    syncAndFetchUser(); // refresh balance
                } else {
                    showMessage("ስህተት", data.message, "❌");
                }
            } catch (err) {
                console.error("Withdraw Error:", err);
                showMessage("ስህተት", "የማውጫ ጥያቄ መላክ አልተቻለም!", "❌");
            }
        });
    }
}

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
        userData.telegram_id = user.id;
        userData.first_name = user.first_name || "User";
        userData.last_name = user.last_name || "";
        userData.username = user.username ? `@${user.username}` : "";

        const fullName = `${userData.first_name} ${userData.last_name}`.trim();

        if (profileNameEl) profileNameEl.textContent = fullName;
        if (profilePhoneEl) profilePhoneEl.textContent = userData.username || `ID: ${userData.telegram_id}`;

        syncAndFetchUser();
    } else {
        console.log("Running outside Telegram Mini App context.");
        userData.telegram_id = "12345678"; // Test Telegram ID for Local Browser
        if (profileNameEl) profileNameEl.textContent = "Guest User";
        if (profilePhoneEl) profilePhoneEl.textContent = "No Telegram ID";
        syncAndFetchUser();
    }
}

/* =========================
   INITIAL EXECUTION
========================= */
document.addEventListener("DOMContentLoaded", () => {
    loadTelegramUser();
    setupFormSubmitListeners();
    updateBalanceUI("0.00");
    if (document.getElementById("playerCount")) {
        document.getElementById("playerCount").textContent = "1";
    }
});

/* =========================
   COPY TO CLIPBOARD LOGIC
========================= */
function copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => {
            showCopyToast();
        }).catch(err => {
            fallbackCopyTextToClipboard(text);
        });
    } else {
        fallbackCopyTextToClipboard(text);
    }
}

function fallbackCopyTextToClipboard(text) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.left = "-999999px";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
        document.execCommand('copy');
        showCopyToast();
    } catch (err) {
        console.error('Fallback: Copying failed', err);
    }
    document.body.removeChild(textArea);
}

function showCopyToast() {
    if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
    }
    
    showMessage("Copied!", "የአካውንት ቁጥሩ ተገልብጧል (Copied)", "📋");
}
