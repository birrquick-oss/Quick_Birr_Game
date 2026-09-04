/* =========================================================
   QUICK_BIRR GAMES - PART 1/3
   Telegram Init, Global State, Modals & Navigation
   ========================================================= */

const tg = window.Telegram?.WebApp;

/* =========================
   TELEGRAM INIT & GLOBAL STATE
========================= */
let userData = {
    telegram_id: null,
    db_user_id: null,
    first_name: "Guest",
    last_name: "",
    username: "",
    balance: 0.00
};

let selectedBingoCards = [];       // ተጫዋቹ የገዛቸው/የመረጣቸው ካርዶች
let temporarilySelectedCards = []; // ጊዜያዊ ምርጫዎች
let currentGameId = null;
let bingoSocket = null;
let takenCardsList = [];

let currentCardIndex = 0; 
let recentBallsList = []; 
let soundEnabled = true;
let isAutoMark = true;
let markedCellsMap = {}; // { cardNum: Set([num1, num2]) }

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
const bingoGameView = document.getElementById("bingoGameView");

const depositModal = document.getElementById("depositModal");
const withdrawModal = document.getElementById("withdrawModal");

/* =========================
   HELPER FUNCTIONS
========================= */
function getBingoColor(letter) {
    switch(letter) {
        case 'B': return '#2ed573';
        case 'I': return '#ff4757';
        case 'N': return '#ffa500';
        case 'G': return '#1e90ff';
        case 'O': return '#9b59b6';
        default: return '#2f3542';
    }
}

function showToastMessage(message, type) {
    const oldToast = document.getElementById("live-toast");
    if (oldToast) oldToast.remove(); 

    const toast = document.createElement("div");
    toast.id = "live-toast";
    let bgColor = type === "success" ? "#2ecc71" : "#e74c3c";
    
    toast.style = `
        position: fixed; top: 20%; left: 50%; transform: translate(-50%, -50%);
        background: ${bgColor}; color: white; padding: 14px 24px; border-radius: 8px;
        font-size: 16px; font-weight: bold; z-index: 9999; text-align: center;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.4);
    `;
    toast.innerText = message;
    document.body.appendChild(toast);

    setTimeout(() => { if (toast) toast.remove(); }, 2200);
}

function toggleSound() {
    soundEnabled = !soundEnabled;
    const soundText = document.getElementById('soundStatusText');
    const soundBtn = document.getElementById('soundToggleBtn');
    if (soundText) soundText.textContent = soundEnabled ? 'ON' : 'OFF';
    if (soundBtn) soundBtn.style.opacity = soundEnabled ? '1' : '0.5';
}

/* =========================
   MODALS & NAVIGATION
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
    if (depositModal) depositModal.hidden = false;
    if (withdrawModal) withdrawModal.hidden = false;
    if (modal) modal.hidden = true;
}

document.getElementById("modalClose")?.addEventListener("click", closeMessage);
document.getElementById("modalButton")?.addEventListener("click", closeMessage);

document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", () => {
        closeMessage();
        closeModals();
    });
});

document.getElementById("depositButton")?.addEventListener("click", openDepositModal);
document.getElementById("dashDepositBtn")?.addEventListener("click", openDepositModal);
document.getElementById("withdrawButton")?.addEventListener("click", openWithdrawModal);
document.getElementById("dashWithdrawBtn")?.addEventListener("click", openWithdrawModal);

/* =========================
   GAME CARDS CLICK HANDLERS
========================= */
document.querySelectorAll(".game-card").forEach(card => {
    card.addEventListener("click", () => {
        const game = card.dataset.game;

        if (game === "bingo") {
            showPage("bingoSelection");
            render1000BingoCards();
            render75BoardSkeleton();
            connectBingoWebSocket();
            return;
        }

        const names = {
            slots: "Lucky Slots", plinko: "Plinko", roulette: "European Roulette",
            blackjack: "Blackjack", mines: "Mines"
        };
        showMessage(names[game] || "Game", "ይህ ጨዋታ በቅርብ ቀን ይለቀቃል!", "🎮");
    });
});
