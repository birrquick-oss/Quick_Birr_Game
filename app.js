/* =========================================================
   QUICK_BIRR GAMES
   Frontend Controller (Full Integration with Backend & Bingo Engine)
   ========================================================= */

const tg = window.Telegram?.WebApp;

/* =========================
   TELEGRAM INIT & STATE
========================= */
let userData = {
    telegram_id: null,
    db_user_id: null,
    first_name: "Guest",
    last_name: "",
    username: "",
    balance: 0.00
};

let selectedBingoCards = [];
let currentGameId = null;
let bingoSocket = null;
let takenCardsList = [];

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
const bingoSelectionView = document.getElementById("bingoSelectionView");
const bingoLiveView = document.getElementById("bingoLiveView");

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
            showPage("bingoSelection");
            render1000BingoCards();
            connectBingoWebSocket();
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
            "ይህ ጨዋታ በቅርብ ቀን ይለቀቃል!",
            "🎮"
        );
    });
});

/* =========================
   BINGO WEBSOCKET INTEGRATION
========================= */
function connectBingoWebSocket() {
    if (bingoSocket && bingoSocket.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/api/bingo/ws`;

    bingoSocket = new WebSocket(wsUrl);

    bingoSocket.onopen = () => {
        console.log("⚡ Bingo WebSocket Connected successfully!");
    };

    bingoSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        switch (data.type) {
            case "countdown":
                currentGameId = data.game_id;
                updateCountdownUI(data);
                break;

            case "taken_cards_update":
                updateTakenCardsUI(data.taken_cards);
                break;

            case "phase_change":
                if (data.phase === "DRAW") {
                    showPage("bingoLive");
                }
                break;

            case "ball":
                renderDrawnBall(data);
                break;

            case "game_over":
                handleGameOver(data);
                break;

            default:
                break;
        }
    };

    bingoSocket.onclose = () => {
        console.log("❌ Bingo WebSocket Connection Closed. Reconnecting...");
        setTimeout(connectBingoWebSocket, 3000);
    };
}

function updateCountdownUI(data) {
    const timerEl = document.getElementById("bingoTimer");
    const countEl = document.getElementById("playerCount");
    const prizeEl = document.getElementById("potAmount");

    if (timerEl) timerEl.textContent = `${data.seconds}s`;
    if (countEl) countEl.textContent = data.player_count || "0";
    if (prizeEl && data.derash_rooms) {
        prizeEl.textContent = `${data.derash_rooms["10"] || 0} ETB`;
    }

    if (data.taken_cards) {
        updateTakenCardsUI(data.taken_cards);
    }
}

function updateTakenCardsUI(takenCards) {
    takenCardsList = takenCards || [];
    document.querySelectorAll(".card-item").forEach(item => {
        const cardNum = parseInt(item.dataset.cardNum);
        if (takenCardsList.includes(cardNum)) {
            item.classList.add("taken");
            item.classList.remove("selected");
        } else {
            item.classList.remove("taken");
        }
    });
}

function renderDrawnBall(data) {
    const ballEl = document.getElementById("currentBall");
    const historyContainer = document.getElementById("ballHistory");

    if (ballEl) {
        ballEl.textContent = data.label;
        ballEl.className = `active-ball ball-${data.letter}`;
    }

    if (historyContainer) {
        const ballBadge = document.createElement("span");
        ballBadge.className = `ball-badge ball-${data.letter}`;
        ballBadge.textContent = data.label;
        historyContainer.prepend(ballBadge);
    }
}

function handleGameOver(data) {
    showMessage(
        "የጨዋታው ፍጻሜ!",
        `${data.message}\nየአሸናፊነት ሽልማት፦ ${data.prize} ETB`,
        "🎉"
    );
    syncAndFetchUser();
    setTimeout(() => {
        showPage("bingoSelection");
        render1000BingoCards();
    }, 5000);
}

/* =========================
   BINGO 1-1000 SELECTION & LOGIC
========================= */
function render1000BingoCards() {
    const gridContainer = document.getElementById("cardsGrid");
    if (!gridContainer) return;

    gridContainer.innerHTML = "";
    selectedBingoCards = [];
    updateSelectedCardsUI();

    const fragment = document.createDocumentFragment();
    for (let i = 1; i <= 1000; i++) {
        const cardBtn = document.createElement("div");
        cardBtn.className = "card-item";
        if (takenCardsList.includes(i)) {
            cardBtn.classList.add("taken");
        }
        cardBtn.textContent = i;
        cardBtn.dataset.cardNum = i;

        cardBtn.addEventListener("click", () => toggleCardSelection(cardBtn, i));
        fragment.appendChild(cardBtn);
    }
    gridContainer.appendChild(fragment);
}

function toggleCardSelection(element, cardNum) {
    if (element.classList.contains("taken")) return;

    const index = selectedBingoCards.indexOf(cardNum);
    if (index > -1) {
        selectedBingoCards.splice(index, 1);
        element.classList.remove("selected");
    } else {
        // Option: allow buying single or multiple cards
        selectedBingoCards.push(cardNum);
        element.classList.add("selected");
    }

    if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.selectionChanged();
    }

    updateSelectedCardsUI();
}

function updateSelectedCardsUI() {
    const countEl = document.getElementById("selectedCount");
    const totalEl = document.getElementById("totalPrice");
    const cardPrice = 10;

    if (countEl) countEl.textContent = selectedBingoCards.length;
    if (totalEl) totalEl.textContent = (selectedBingoCards.length * cardPrice).toFixed(2);
}

// Confirm Bingo Purchases
document.getElementById("buyBingoCardsBtn")?.addEventListener("click", async () => {
    if (selectedBingoCards.length === 0) {
        showMessage("ካርድ አልመረቱም", "እባክዎን ለመጫወት ቢያንስ አንድ የቢንጎ ካርድ ይምረጡ!", "⚠️");
        return;
    }

    if (!currentGameId) {
        showMessage("ማስጠንቀቂያ", "እባክዎን ጨዋታው እስኪጀምር ጥቂት ሰከንድ ይታገሱ!", "⏳");
        return;
    }

    const totalCost = selectedBingoCards.length * 10;
    if (parseFloat(userData.balance) < totalCost) {
        showMessage("በቂ ቀሪ ሂሳብ የለዎትም", "እባክዎን አስቀድመው ዲፖዚት ያድርጉ!", "💰");
        return;
    }

    let successCount = 0;
    for (const cardNum of selectedBingoCards) {
        try {
            const res = await fetch(`/api/bingo/buy-card?user_id=${userData.db_user_id}&card_number=${cardNum}&game_id=${currentGameId}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" }
            });

            const data = await res.json();
            if (res.ok && data.success) {
                successCount++;
                userData.balance = data.new_balance;
                updateBalanceUI(userData.balance);
            } else {
                showMessage("ስህተት", data.detail || data.message || "ካርድ መግዛት አልተቻለም", "❌");
            }
        } catch (err) {
            console.error("Buy Card Error:", err);
        }
    }

    if (successCount > 0) {
        showMessage("ተሳክቷል!", `${successCount} ካርዶች ተገዝተዋል:: መልካም እድል!`, "🎉");
        selectedBingoCards = [];
        updateSelectedCardsUI();
    }
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
            userData.db_user_id = userDataResult.user.id;
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
                    syncAndFetchUser();
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
function hideAllViews() {
    if (homeView) homeView.hidden = true;
    if (profileView) profileView.hidden = true;
    if (bingoSelectionView) bingoSelectionView.hidden = true;
    if (bingoLiveView) bingoLiveView.hidden = true;
}

function showPage(pageName) {
    document.querySelectorAll(".nav-item").forEach(nav => {
        if (nav.dataset.page === pageName) {
            nav.classList.add("active");
        } else {
            nav.classList.remove("active");
        }
    });

    hideAllViews();

    if (pageName === "profile") {
        if (profileView) profileView.hidden = false;
    } else if (pageName === "bingoSelection") {
        if (bingoSelectionView) bingoSelectionView.hidden = false;
    } else if (pageName === "bingoLive") {
        if (bingoLiveView) bingoLiveView.hidden = false;
    } else {
        if (homeView) homeView.hidden = false;
    }

    window.scrollTo({ top: 0, behavior: "smooth" });
}

document.querySelectorAll(".nav-item").forEach(item => {
    item.addEventListener("click", () => {
        const page = item.dataset.page;

        if (page === "home") {
            showPage("home");
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
   COPY TO CLIPBOARD BINDINGS
========================= */
document.querySelectorAll(".account-item").forEach(accItem => {
    accItem.addEventListener("click", () => {
        const accNum = accItem.querySelector(".acc-num")?.innerText.trim();
        if (accNum) copyToClipboard(accNum);
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
        userData.telegram_id = "12345678";
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
        }).catch(() => {
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
