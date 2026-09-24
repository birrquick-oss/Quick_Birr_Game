/* =========================================================
   QUICK_BIRR GAMES - PART 1
   Init, State, Elements, Helpers, Modals & Base WS
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
    balance: "0.00"
};

let selectedBingoCards = [];       
let temporarilySelectedCards = []; 
let currentGameId = null;
let currentDerashAmount = "0.00";
let bingoSocket = null;
let takenCardsList = [];

let recentBallsList = []; 

// 🎰 Lucky Slots
let selectedSlotBet = 10;
let slotSpinning = false;

const slotSymbols = [
    "🍒",
    "🍋",
    "🔔",
    "⭐",
    "💎",
    "7️⃣"
];

let selectedPlinkoBet = 10;
let plinkoPlaying = false;

const plinkoMultipliers = [
    0,
    0.5,
    1,
    2,
    5,
    10,
    5,
    2,
    1,
    0.5,
    0
];

// 🎡 Roulette
let selectedRouletteBet = 10;
let rouletteSpinning = false;
// 🃏 Blackjack
let selectedBlackjackBet = 10;
let blackjackPlaying = false;
// 💎 Mines
let selectedMinesBet = 10;
let selectedMinesCount = 3;
let minesPlaying = false;
let currentMinesGameId = null;

let soundEnabled = true;
let isAutoMark = true;
let markedCellsMap = {}; 
let winnerAutoCloseTimer = null;
let currentCardIndex = 0;

// 🏆 የቅርብ አሸናፊዎች ግሎባል ተغيرዎች (እዚህ ጋር ቢገቡ ይመረጣል)
let recentWinners = [];
let currentWinnerIndex = 0;

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
const slotsView = document.getElementById("slotsView");
const plinkoView = document.getElementById("plinkoView");
const rouletteView = document.getElementById("rouletteView");
const blackjackView = document.getElementById("blackjackView");
const minesView = document.getElementById("minesView");

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
    
    toast.style.cssText = `
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
    if (depositModal) depositModal.hidden = true;
    if (withdrawModal) withdrawModal.hidden = true;
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
            render600BingoCards();
            clear75Board();
            connectBingoWebSocket();
            return;
        }

        if (game === "slots") {
            showPage("slots");
            updateSlotsBalance();
            return;
        }

        if (game === "plinko") {
            showPage("plinko");
            updatePlinkoBalance();
            return;
        }

        if (game === "roulette") {
            showPage("roulette");
            updateRouletteBalance();
            return;
        }

        if (game === "blackjack") {
            showPage("blackjack");
            updateBlackjackBalance();
            return;
        }
       
        if (game === "mines") {
            showPage("mines");
            updateMinesBalance();
            return;
        }


        const names = {
            slots: "Lucky Slots", plinko: "Plinko", roulette: "European Roulette",
            blackjack: "Blackjack", mines: "Mines"
        };
        showMessage(names[game] || "Game", "ይህ ጨዋታ በቅርብ ቀን ይለቀቃል!", "🎮");
    });
});

/* =========================
   BINGO WEBSOCKET INTEGRATION
========================= */
function connectBingoWebSocket() {
    if (bingoSocket && bingoSocket.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    bingoSocket = new WebSocket(wsUrl);

    bingoSocket.onopen = () => {
        console.log("⚡ Bingo WebSocket Connected successfully!");
        refreshTakenCards();
    };

    bingoSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        /* =========================
           BINGO COUNTDOWN / PICK
        ========================= */
        if (
            (data.type === "countdown" || data.type === "time_update") &&
            (data.phase === "PICK" || !data.phase)
        ) {
            currentGameId = data.game_id || currentGameId;
            updateCountdownUI(data);
            recentBallsList = [];
        }

        /* =========================
           TAKEN CARDS
        ========================= */
        if (data.type === "taken_cards_update") {
            updateTakenCardsUI(data.taken_cards);
        }

        /* =========================
           BINGO GAME START
           
           ⚠️ IMPORTANT:
           Only open Bingo Live if the user
           is already inside Bingo.
        ========================= */
        if (
            data.type === "phase_change" &&
            (data.phase === "DRAW" || data.phase === "GAME_START")
        ) {
            const userIsInBingo =
                bingoSelectionView &&
                !bingoSelectionView.hidden;

            const userIsWatchingBingo =
                bingoGameView &&
                !bingoGameView.hidden;

            if (userIsInBingo || userIsWatchingBingo) {
                showPage("bingoLive");
                clear75Board();
                currentCardIndex = 0;
                renderMyBoughtCards();
                updateRecentBallsUI();
            }
        }

        /* =========================
           BINGO BALL DRAW
           
           ⚠️ IMPORTANT:
           Do NOT force the user into Bingo
           if they are playing Slots/another game.
        ========================= */
        if (data.type === "ball") {

            const userIsWatchingBingo =
                bingoGameView &&
                !bingoGameView.hidden;

            if (userIsWatchingBingo) {
                handleBallDraw(data);
            }
        }

        /* =========================
           BINGO GAME OVER
           
           Only show Bingo result if the
           user is currently watching Bingo.
        ========================= */
        if (data.type === "game_over") {

            const userIsWatchingBingo =
                bingoGameView &&
                !bingoGameView.hidden;

            if (userIsWatchingBingo) {
                handleGameOver(data);
            }
        }
    };

    bingoSocket.onclose = () => {
        console.log("❌ Bingo WebSocket Connection Closed. Reconnecting...");
        setTimeout(connectBingoWebSocket, 2000);
    };
}

function updateCountdownUI(data) {
    const timerEl = document.getElementById("selectionTimer"); 
    const countEl = document.getElementById("playerCount");
    const takenCountEl = document.getElementById("takenCardsCount");
    const jackpotEl = document.getElementById("jackpotAmountText");
    const phaseGameId = document.getElementById("phase1GameId");

    if (timerEl) timerEl.textContent = `${data.seconds !== undefined ? data.seconds : data.time}`;
    if (countEl && data.player_count !== undefined) countEl.textContent = data.player_count;
    if (takenCountEl && data.taken_cards) takenCountEl.textContent = data.taken_cards.length;
    if (phaseGameId && data.game_id) phaseGameId.textContent = `#${data.game_id}`;
    
    if (data.derash_rooms) {
        currentDerashAmount = `${data.derash_rooms["10"] || 0}.00`;
        if (jackpotEl) jackpotEl.textContent = `${currentDerashAmount} ETB`;
    }

    if (data.taken_cards) {
        updateTakenCardsUI(data.taken_cards);
    }
}

async function refreshTakenCards() {
    try {
        const response = await fetch(`/api/cards/status?bet_amount=10`);
        if (response.ok) {
            const takenCards = await response.json();
            updateTakenCardsUI(takenCards);
        }
    } catch (e) {
        console.error("⚠️ የተሸጡ ካርዶችን ማደስ አልተቻለም፦", e);
    }
}

function updateTakenCardsUI(takenCards) {
    takenCardsList = takenCards || [];
    document.querySelectorAll("#cardsGrid .card-item").forEach(item => {
        const cardNum = parseInt(item.dataset.cardNum);
        if (takenCardsList.includes(cardNum)) {
            item.classList.add("taken");
            item.classList.remove("selected");
        } else {
            item.classList.remove("taken");
        }
    });
}

/* =========================================================
   QUICK_BIRR GAMES - PART 2
   Ball Handling, Winners Modal & Card Rendering
   ========================================================= */

function handleBallDraw(data) {
    const ballElement = document.getElementById(`ball-${data.number}`);
    const letter = data.label ? data.label.charAt(0) : (data.number <= 15 ? 'B' : data.number <= 30 ? 'I' : data.number <= 45 ? 'N' : data.number <= 60 ? 'G' : 'O');
    const color = getBingoColor(letter);
    
    if (ballElement) {
        ballElement.classList.add("drawn");
        ballElement.style.background = color;
        ballElement.style.color = "#fff";
        ballElement.style.boxShadow = `0 0 10px ${color}`;
    }

    // የጠራውን ኳስ በሁለተኛው ገፅ እና ቦርድ ላይ መመዝገብ
    renderDrawnBall(data, letter, color);
}

function renderDrawnBall(data, letter, color) {
    const callBadge = document.getElementById("callCountBadge");
    const gameIdBadge = document.getElementById("gameIdBadge");
    const liveDerashText = document.getElementById("liveDerashText");

    // 1. Call (የተጠሩ ቁጥሮች ብዛት) መመዝገቢያ
    if (callBadge) {
        const currentCall = data.call_count || recentBallsList.length + 1;
        callBadge.textContent = `Call ${currentCall}`;
    }
    
    // 2. Game ID መመዝገቢያ
    const activeGameId = data.game_id || currentGameId || 0;
    if (gameIdBadge) {
        gameIdBadge.textContent = `Game #${activeGameId}`;
    }

    // 3. የደራሽ አማውንት (መጠን) መመዝገቢያ
    if (data.derash_amount !== undefined && data.derash_amount !== null) {
        currentDerashAmount = `${parseFloat(data.derash_amount).toFixed(2)}`;
    }
    if (liveDerashText) {
        liveDerashText.textContent = `ደራሽ ${currentDerashAmount} ETB`;
    }

    const activeCell = document.getElementById(`cell-ball-${data.number}`);
    if (activeCell) {
        activeCell.classList.add("called");
        activeCell.style.background = color;
        activeCell.style.color = "#fff";
    }
   
    if (soundEnabled) {
        let audio = new Audio(`/static/sounds/${data.number}.mp3.mp3`);
        audio.play().catch(e => {
            console.log("🔊 ድምፅ ማጫወት አልተቻለም፦", e);
        });
    }

    recentBallsList.unshift({ label: data.label || `${letter}${data.number}`, letter: letter, num: data.number });
    if (recentBallsList.length > 10) recentBallsList.pop();
    updateRecentBallsUI(); 

    if (isAutoMark) {
        const matchingCells = document.querySelectorAll(`.cell-${data.number}`);
        matchingCells.forEach(cell => {
            cell.classList.add("marked-auto");
            cell.style.background = color;
            cell.style.color = "#fff";
            cell.style.boxShadow = `0 0 12px ${color}`;
        });
    }

    if (document.getElementById("callCount")) {
        document.getElementById("callCount").innerText = data.call_count || recentBallsList.length;
    }
}

function handleGameOver(data) {
    if (soundEnabled && typeof playWinSound === "function") playWinSound();

    const winnersList = data.winners || [];
    const titleText = winnersList.length > 1 ? `🎉 ${winnersList.length} አሸናፊዎች! 🎉` : "🎉 BINGO! 🎉";
    const messageText = data.message || "ጨዋታው ተጠናቋል!";

    let allWinnersHtml = "";

    if (winnersList.length > 0) {
        winnersList.forEach((winner) => {
            const wName = winner.telegram_name || `User_${winner.winner_id || winner.telegram_id}`;
            const phoneNum = winner.phone_number || "ስልክ አልተመዘገበም";
            const cNum = winner.card_number || "N/A";
            const pAmt = winner.prize || 0;
            const cardMatrixNumbers = winner.card_numbers || [];
            const winningNumbers = winner.winning_numbers || [];

            let gridHtml = "";
            if (cardMatrixNumbers.length === 25) {
                gridHtml = `<div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; margin: 15px auto; max-width: 250px; background: #111; padding: 10px; border-radius: 10px;">`;
                cardMatrixNumbers.forEach((num) => {
                    const isWinningNum = winningNumbers.includes(num);
                    const isFreeSpace = num === 0 || num === "★" || num === "FREE";
                    const displayNum = isFreeSpace ? "★" : num;

                    let cellStyle = `aspect-ratio: 1; display: flex; justify-content: center; align-items: center; font-weight: bold; font-size: 14px; border-radius: 6px; transition: all 0.3s;`;
                    if (isWinningNum || isFreeSpace) {
                        cellStyle += `background: #ffbc00; color: black; box-shadow: 0 0 12px #ffbc00; border: 1px solid #fff; scale: 1.05;`;
                    } else {
                        cellStyle += `background: #252634; color: #666; border: 1px solid #333;`;
                    }
                    gridHtml += `<div style="${cellStyle}">${displayNum}</div>`;
                });
                gridHtml += `</div>`;
            }

            allWinnersHtml += `
                <div style="background:#161622; padding:15px; border-radius:15px; margin-bottom: 20px; border: 1px solid #2a2b3d; text-align: left;">
                    <div style="font-size:16px; margin-bottom: 10px;">
                        <p style="margin:4px 0;">👤 <b>ስም፦</b> <span style="color:#00ffcc; float:right; font-weight:bold;">${wName}</span></p>
                        <p style="margin:4px 0;">📞 <b>ስልክ፦</b> <span style="color:#3aafaa; float:right; font-weight:bold;">${phoneNum}</span></p>
                        <p style="margin:4px 0;">🎫 <b>ካርቴላ፦</b> <span style="color:#ffbc00; float:right; font-weight:bold;">#${cNum}</span></p>
                    </div>
                    ${gridHtml}
                    <div style="background: rgba(0,255,0,0.1); border: 1px dashed #00ff00; padding: 8px; border-radius: 10px; text-align: center; margin-top: 10px;">
                        <span style="font-size:22px; color:#00ff00; font-weight:bold;">+${pAmt} ETB</span>
                    </div>
                </div>
            `;
        });
    } else {
        const winnerName = data.telegram_name || data.winner_name || "ተጫዋች";
        const phoneNum = data.phone_number || "ስልክ አልተመዘገበም";
        const cardNum = data.card_number || "N/A";
        const prize = data.prize || 0;
        const cardMatrixNumbers = data.card_numbers || []; 
        const winningNumbers = data.winning_numbers || []; 

        let gridHtml = "";
        if (cardMatrixNumbers.length === 25) {
            gridHtml = `<div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; margin: 15px auto; max-width: 250px; background: #111; padding: 10px; border-radius: 10px;">`;
            cardMatrixNumbers.forEach((num) => {
                const isWinningNum = winningNumbers.includes(num);
                const isFreeSpace = num === 0 || num === "★" || num === "FREE";
                const displayNum = isFreeSpace ? "★" : num;

                let cellStyle = `aspect-ratio: 1; display: flex; justify-content: center; align-items: center; font-weight: bold; font-size: 14px; border-radius: 6px; transition: all 0.3s;`;
                if (isWinningNum || isFreeSpace) {
                    cellStyle += `background: #ffbc00; color: black; box-shadow: 0 0 12px #ffbc00; border: 1px solid #fff; scale: 1.05;`;
                } else {
                    cellStyle += `background: #252634; color: #666; border: 1px solid #333;`;
                }
                gridHtml += `<div style="${cellStyle}">${displayNum}</div>`;
            });
            gridHtml += `</div>`;
        }

        allWinnersHtml = `
            <div style="background:#161622; padding:15px; border-radius:15px; border: 1px solid #2a2b3d; text-align: left;">
                <div style="font-size:16px; margin-bottom: 10px;">
                    <p style="margin:4px 0;">👤 <b>ስም፦</b> <span style="color:#00ffcc; float:right; font-weight:bold;">${winnerName}</span></p>
                    <p style="margin:4px 0;">📞 <b>ስልክ፦</b> <span style="color:#3aafaa; float:right; font-weight:bold;">${phoneNum}</span></p>
                    <p style="margin:4px 0;">🎫 <b>ካርቴላ፦</b> <span style="color:#ffbc00; float:right; font-weight:bold;">#${cardNum}</span></p>
                </div>
                ${gridHtml}
                <div style="background: rgba(0,255,0,0.1); border: 1px dashed #00ff00; padding: 10px; border-radius: 10px; text-align: center; margin-top: 10px;">
                    <span style="font-size:24px; color:#00ff00; font-weight:bold;">+${prize} ETB</span>
                </div>
            </div>
        `;
    }

    const oldModal = document.getElementById('winnerModal');
    if (oldModal) oldModal.remove();

    const modalHtml = `
        <div id="winnerModal" style="position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.9); display:flex; justify-content:center; align-items:center; z-index:9999; color:white; font-family:sans-serif;">
            <div style="background:#1e1e2e; padding:25px; border-radius:20px; text-align:center; max-width:90%; width:360px; border:2px solid #ffbc00; box-shadow: 0 0 30px rgba(255,188,0,0.3); display: flex; flex-direction: column; max-height: 85vh;">
                <h2 style="color:#ffbc00; margin:0 0 5px 0; font-size:24px; font-weight:900;">${titleText}</h2>
                <p style="font-size:12px; color:#aaa; margin: 0 0 10px 0;">${messageText}</p>
                <hr style="border-color:#2a2b3d; margin:5px 0 15px 0; width:100%;">
                
                <div style="overflow-y: auto; flex-grow: 1; padding-right: 5px; margin-bottom: 15px; scrollbar-width: thin;">
                    ${allWinnersHtml}
                </div>

                <button onclick="closeWinnerModalAndReset();" style="background:#ffbc00; color:black; border:none; padding:14px; font-size:16px; font-weight:bold; border-radius:10px; width:100%; cursor:pointer; flex-shrink: 0;">እሺ (ቀጥል)</button>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    winnerAutoCloseTimer = setTimeout(() => {
        closeWinnerModalAndReset();
    }, 5000);

    selectedBingoCards = []; 
    temporarilySelectedCards = [];
    refreshTakenCards(); 
}

function render600BingoCards() {
    const gridContainer = document.getElementById("cardsGrid");
    if (!gridContainer) return;

    gridContainer.innerHTML = "";
    selectedBingoCards = [];
    temporarilySelectedCards = [];
    updateSelectedCardsUI();

    const fragment = document.createDocumentFragment();
    for (let i = 1; i <= 600; i++) {
        const cardBtn = document.createElement("div");
        cardBtn.className = "card-item";
        cardBtn.id = `pick-card-${i}`;
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
    if (selectedBingoCards.includes(cardNum)) return;

    if (temporarilySelectedCards.includes(cardNum)) {
        temporarilySelectedCards = temporarilySelectedCards.filter(id => id !== cardNum);
        element.classList.remove("selected");
    } else {
        if (temporarilySelectedCards.length + selectedBingoCards.length >= 10) {
            showToastMessage("⚠️ በአንድ ጨዋታ መግዛት የሚችሉት ከፍተኛው የካርቴላ መጠን 10 ብቻ ነው!", "error");
            return;
        }
        temporarilySelectedCards.push(cardNum);
        element.classList.add("selected");
    }

    if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.selectionChanged();
    }

    updateSelectedCardsUI();
}

function updateSelectedCardsUI() {
    const countBtn = document.getElementById("mySelectedCount");
    if (countBtn) countBtn.textContent = temporarilySelectedCards.length + selectedBingoCards.length;
}

/* =========================================================
   QUICK_BIRR GAMES - PART 3
   Card Confirmation, Manual/Auto Play, Forms & Initialization
   ========================================================= */

document.getElementById("confirmCardsBtn")?.addEventListener("click", async () => {
    if (temporarilySelectedCards.length === 0) {
        showToastMessage("⚠️ እባክህ መጀመሪያ የሚገዙትን የካርቴላ ቁጥሮች ይምረጡ!", "error");
        return;
    }

    for (let cardNumber of [...temporarilySelectedCards]) {
        try {
            const response = await fetch("/api/cards/pick", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    telegram_id: String(userData.telegram_id),
                    card_number: cardNumber,
                    bet_amount: 10
                })
            });
            const result = await response.json();

            if (result.success === false) {
                showToastMessage("⚠️ " + result.message, "error");
                const btn = document.getElementById(`pick-card-${cardNumber}`);
                if (btn) btn.classList.remove("selected");
                temporarilySelectedCards = temporarilySelectedCards.filter(id => id !== cardNumber);
                continue; 
            }

            if (result.success === true) {
                selectedBingoCards.push(cardNumber);
                temporarilySelectedCards = temporarilySelectedCards.filter(id => id !== cardNumber);
                
                const btn = document.getElementById(`pick-card-${cardNumber}`);
                if (btn) {
                    btn.classList.remove("selected");
                    btn.classList.add("taken");
                }

                if (result.current_balance !== undefined) {
                    userData.balance = parseFloat(result.current_balance).toFixed(2);
                    updateBalanceUI(userData.balance);
                } else {
                    syncAndFetchUser();
                }

                showToastMessage("🎉 ካርቴላው በተሳካ ሁኔታ ተገዝቷል!", "success");
            }
        } catch (e) {
            console.error(e);
            showToastMessage("⚠️ የቴክኒክ ስህተት አጋጥሟል!", "error");
        }
    }
    updateSelectedCardsUI();
});

function handleManualCellClick(cellElement, cellNumber, activeCardNum) {
    if (!activeCardNum) activeCardNum = selectedBingoCards[currentCardIndex];
    if (!markedCellsMap[activeCardNum]) markedCellsMap[activeCardNum] = new Set();

    const isBallDrawn = recentBallsList.some(b => b.num === cellNumber);

    if (isBallDrawn) {
        markedCellsMap[activeCardNum].add(cellNumber);
        let letterPrefix = cellNumber <= 15 ? 'B' : cellNumber <= 30 ? 'I' : cellNumber <= 45 ? 'N' : cellNumber <= 60 ? 'G' : 'O';
        const ballColor = getBingoColor(letterPrefix);
        cellElement.style.background = ballColor;
        cellElement.style.color = "#fff";
        cellElement.classList.add("marked-manual");
    } else {
        const oldBg = cellElement.style.background;
        cellElement.style.background = "#ff4757";
        setTimeout(() => { cellElement.style.background = oldBg; }, 250);
    }
}

document.getElementById("claimBingoBtn")?.addEventListener("click", () => {
    if (!bingoSocket || bingoSocket.readyState !== WebSocket.OPEN) {
        showToastMessage("⚠️ WebSocket አልተገናኘም!", "error");
        return;
    }

    if (selectedBingoCards.length === 0) {
        showToastMessage("⚠️ ምንም የተገዛ ካርቴላ የለም!", "error");
        return;
    }

    selectedBingoCards.forEach(cardNum => {
        bingoSocket.send(JSON.stringify({
            type: "claim_bingo",
            telegram_id: String(userData.telegram_id),
            card_number: cardNum,
            game_id: currentGameId
        }));
    });

    showToastMessage("🔥 የ BINGO ጥያቄ ተልኳል! በመፈተሽ ላይ...", "success");
});

function clear75Board() {
    markedCellsMap = {};

    const containers = {
        "b": document.getElementById("b-container"),
        "i": document.getElementById("i-container"),
        "n": document.getElementById("n-container"),
        "g": document.getElementById("g-container"),
        "o": document.getElementById("o-container")
    };
    Object.values(containers).forEach(c => { if(c) c.innerHTML = ""; });

    for (let num = 1; num <= 75; num++) {
        const numDiv = document.createElement("div");
        numDiv.className = "board-num";
        numDiv.id = `ball-${num}`;
        numDiv.innerText = num;

        if (num <= 15 && containers["b"]) containers["b"].appendChild(numDiv);
        else if (num <= 30 && containers["i"]) containers["i"].appendChild(numDiv);
        else if (num <= 45 && containers["n"]) containers["n"].appendChild(numDiv);
        else if (num <= 60 && containers["g"]) containers["g"].appendChild(numDiv);
        else if (containers["o"]) containers["o"].appendChild(numDiv);
    }
}

function updateRecentBallsUI() {
    const recentRow = document.querySelector(".recent-balls-row");
    if (!recentRow) return;
    recentRow.innerHTML = ""; 

    if (recentBallsList.length === 0) {
        recentRow.innerHTML = "<div style='color:#aaa; font-size:12px; text-align:center; width:100%;'>ኳሶች እዚህ ይደረደራሉ...</div>";
        return;
    }
    for (let i = recentBallsList.length - 1; i >= 0; i--) {
        const ball = recentBallsList[i];
        const ballDiv = document.createElement("div");
        ballDiv.className = (i === 0) ? "overlapping-ball current-live-ball" : "overlapping-ball";
        ballDiv.innerHTML = `<span class="b-letter">${ball.letter}</span><span class="b-number">${ball.label.substring(1)}</span>`;
        const color = getBingoColor(ball.letter);
        ballDiv.style.backgroundColor = color;
        ballDiv.style.boxShadow = `0 0 10px ${color}`;
        recentRow.appendChild(ballDiv);
    }

    if (isAutoMark && recentBallsList.length > 0) {
        autoMarkAllBoughtCards();
    }
}

function autoMarkAllBoughtCards() {
    if (!selectedBingoCards || selectedBingoCards.length === 0) return;
    
    const drawnNumbers = recentBallsList.map(b => b.num);

    selectedBingoCards.forEach(cardNum => {
        if (!markedCellsMap[cardNum]) {
            markedCellsMap[cardNum] = new Set();
        }
        drawnNumbers.forEach(num => {
            markedCellsMap[cardNum].add(num);
        });
    });
}

async function renderMyBoughtCards() {
    const container = document.getElementById("playerBingoCard");
    if (!container) return;
    container.innerHTML = "";

    if (selectedBingoCards.length === 0) {
        container.innerHTML = "<div style='color:white; text-align:center; padding:20px;'>በዚህ ዙር ምንም ካርቴላ አልገዙም!</div>";
        return;
    }
    const activeCardNum = selectedBingoCards[currentCardIndex];

    if (!markedCellsMap[activeCardNum]) {
        markedCellsMap[activeCardNum] = new Set();
    }

    if (isAutoMark) {
        recentBallsList.forEach(b => {
            markedCellsMap[activeCardNum].add(b.num);
        });
    }

    try {
        const res = await fetch(`/api/cards/get_matrix?card_number=${activeCardNum}`);
        const data = await res.json();
        const matrix = data.matrix;

        const mainSliderLayout = document.createElement("div");
        mainSliderLayout.className = "main-slider-layout";

        let html = `
            <button class="side-nav-btn" onclick="moveSlider(-1)">◀</button>
            <div class="card-display-center">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; width: 100%; padding: 0 5px;">
                    <div class="card-title-label" style="color: #ffd700; font-weight: bold; font-size: 13px;">
                        ካርድ #${activeCardNum} (${currentCardIndex + 1}/${selectedBingoCards.length})
                    </div>
                    <button id="toggleMarkBtn" onclick="toggleMarkingMode()" style="background: ${isAutoMark ? '#2ed573' : '#718093'}; color: white; border: none; padding: 4px 8px; font-size: 11px; font-weight: bold; border-radius: 4px;">
                        ${isAutoMark ? "🤖 Auto: ON" : "🖐 Manual"}
                    </button>
                </div>
                <div class="bingo-header-letters">
                    <span style="background:${getBingoColor('B')}">B</span>
                    <span style="background:${getBingoColor('I')}">I</span>
                    <span style="background:${getBingoColor('N')}">N</span>
                    <span style="background:${getBingoColor('G')}">G</span>
                    <span style="background:${getBingoColor('O')}">O</span>
                </div>
                <div class="bingo-card-grid-5x5">
        `;

        matrix.forEach(row => {
            row.forEach(cell => {
                if (cell === "FREE") {
                    html += `<div class="bingo-cell free-star">★</div>`;
                } else {
                    const isMarkedInState = markedCellsMap[activeCardNum].has(cell);
                    const isAlreadyDrawn = recentBallsList.some(b => b.num === cell);

                    if (isMarkedInState || (isAlreadyDrawn && isAutoMark)) {
                        let letterPrefix = cell <= 15 ? 'B' : cell <= 30 ? 'I' : cell <= 45 ? 'N' : cell <= 60 ? 'G' : 'O';
                        const savedColor = getBingoColor(letterPrefix);
                        
                        markedCellsMap[activeCardNum].add(cell);

                        html += `<div class="bingo-cell cell-${cell} marked-auto" style="background:${savedColor} !important; color:#fff;" onclick="handleManualCellClick(this, ${cell}, ${activeCardNum})">${cell}</div>`;
                    } else {
                        html += `<div class="bingo-cell cell-${cell}" onclick="handleManualCellClick(this, ${cell}, ${activeCardNum})">${cell}</div>`;
                    }
                }
            });
        });
        html += `</div></div><button class="side-nav-btn" onclick="moveSlider(1)">▶</button>`;
        mainSliderLayout.innerHTML = html;
        container.appendChild(mainSliderLayout);
    } catch (e) { console.log(e); }
}

function moveSlider(direction) {
    if (selectedBingoCards.length <= 1) return;
    currentCardIndex += direction;
    if (currentCardIndex < 0) currentCardIndex = selectedBingoCards.length - 1;
    if (currentCardIndex >= selectedBingoCards.length) currentCardIndex = 0;
    renderMyBoughtCards();
}

function toggleMarkingMode() {
    isAutoMark = !isAutoMark;
    if (isAutoMark) {
        autoMarkAllBoughtCards();
    }
    renderMyBoughtCards(); 
}

function closeWinnerModalAndReset() {
    if (winnerAutoCloseTimer) clearTimeout(winnerAutoCloseTimer);
    const winnerModalEl = document.getElementById('winnerModal');
    if (winnerModalEl) winnerModalEl.remove();
    showPage('bingoSelection');
    render600BingoCards();
}

async function syncAndFetchUser() {
    if (!userData.telegram_id || userData.telegram_id === "12345678") return;

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
        console.error("User sync error:", error);
    }
}

function updateBalanceUI(amount) {
    const formatted = `${parseFloat(amount || 0).toFixed(2)} ETB`;
    if (balanceEl) balanceEl.textContent = formatted;
    if (dashBalanceEl) dashBalanceEl.textContent = formatted;
}

document.getElementById("balanceButton")?.addEventListener("click", syncAndFetchUser);

function setupFormSubmitListeners() {
    const depositForm = document.getElementById("deposit-form");
    if (depositForm) {
        depositForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            const bankName = document.getElementById("deposit-bank")?.value || "CBE";
            const amount = parseFloat(document.getElementById("deposit-amount")?.value);
            const smsData = document.getElementById("deposit-sms")?.value;

            if (!amount || amount < 50 || !smsData) {
                showMessage("የተሳሳተ መረጃ", "እባክዎን አነስተኛውን 50 ETB እና የባንክ SMS መረጃውን በትክክል ይሙሉ!", "⚠️");
                return;
            }

            const activeTgUser = window.Telegram?.WebApp?.initDataUnsafe?.user;
            const finalTgId = activeTgUser?.id ? String(activeTgUser.id) : String(userData.telegram_id || "");
            const finalTgName = activeTgUser?.first_name || userData.first_name || "ተጫዋች";

            if (!finalTgId || finalTgId === "12345678" || finalTgId === "null" || finalTgId === "undefined") {
                showMessage("የቴሌግራም ችግር", "እባክዎን አፕሊኬሽኑን በቴሌግራም ቦት በኩል 'Play Now' በማለት እንደገና ይክፈቱት!", "⚠️");
                return;
            }

            const payload = {
                telegram_id: finalTgId,
                telegram_name: finalTgName,
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
                    showMessage("ተልኳል!", data.message || "የዲፖዚት ጥያቄዎ ለአድሚን ደርሷል!", "✅");
                } else {
                    showMessage("ስህተት", data.message || "ጥያቄውን ማስተናገድ አልተቻለም", "❌");
                }
            } catch (err) {
                console.error("Deposit Error:", err);
                showMessage("ስህተት", "የዲፖዚት ጥያቄ መላክ አልተቻለም!", "❌");
            }
        });
    }

    const withdrawForm = document.getElementById("withdraw-form");
    if (withdrawForm) {
        withdrawForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            const bankName = document.getElementById("withdraw-bank")?.value || "CBE";
            const accountNumber = document.getElementById("withdraw-account")?.value;
            const amount = parseFloat(document.getElementById("withdraw-amount")?.value);

            if (!amount || amount < 100 || !accountNumber) {
                showMessage("የተሳሳተ መረጃ", "እባክዎን አነስተኛውን 100 ETB እና የባንክ አካውንት ቁጥር በትክክል ይሙሉ!", "⚠️");
                return;
            }

            const activeTgUser = window.Telegram?.WebApp?.initDataUnsafe?.user;
            const finalTgId = activeTgUser?.id ? String(activeTgUser.id) : String(userData.telegram_id || "");

            if (!finalTgId || finalTgId === "12345678" || finalTgId === "null" || finalTgId === "undefined") {
                showMessage("የቴሌግራም ችግር", "እባክዎን አፕሊኬሽኑን በቴሌግራም ቦት በኩል እንደገና ይክፈቱት!", "⚠️");
                return;
            }

            const payload = {
                telegram_id: finalTgId,
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
                    showMessage("ተመዝግቧል!", data.message || "የማውጫ ጥያቄዎ ተመዝግቧል!", "✅");
                    syncAndFetchUser();
                } else {
                    showMessage("ስህተት", data.message || "ጥያቄውን ማስተናገድ አልተቻለም", "❌");
                }
            } catch (err) {
                console.error("Withdraw Error:", err);
                showMessage("ስህተት", "የማውጫ ጥያቄ መላክ አልተቻለም!", "❌");
            }
        });
    }
}

/* =========================================================
   VIEW MANAGEMENT FUNCTIONS
========================================================= */
function hideAllViews() {
    if (homeView) homeView.hidden = true;
    if (profileView) profileView.hidden = true;
    if (bingoSelectionView) bingoSelectionView.hidden = true;
    if (bingoGameView) bingoGameView.hidden = true;
    if (slotsView) slotsView.hidden = true;
    if (plinkoView) plinkoView.hidden = true;
    if (rouletteView) rouletteView.hidden = true;
    if (blackjackView) blackjackView.hidden = true;
    if (minesView) minesView.hidden = true;
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
        if (bingoGameView) bingoGameView.hidden = false;
    } else if (pageName === "slots") {
        if (slotsView) slotsView.hidden = false;
        if (typeof updateSlotsBalance === "function") updateSlotsBalance();
    } else if (pageName === "plinko") {
        if (plinkoView) plinkoView.hidden = false;
        if (typeof updatePlinkoBalance === "function") updatePlinkoBalance(); 
    } else if (pageName === "roulette") {
        if (rouletteView) rouletteView.hidden = false;
        if (typeof updateRouletteBalance === "function") updateRouletteBalance();
    } else if (pageName === "blackjack") {
        if (blackjackView) blackjackView.hidden = false;
        if (typeof updateBlackjackBalance === "function") updateBlackjackBalance();
    } else if (pageName === "mines") {
        if (minesView) minesView.hidden = false;
        if (typeof updateMinesBalance === "function") updateMinesBalance();
    } else {
        if (homeView) homeView.hidden = false;
    }

    window.scrollTo({ top: 0, behavior: "smooth" });
}

document.querySelectorAll(".nav-item").forEach(item => {
    item.addEventListener("click", () => {
        const page = item.dataset.page;
        if (page === "home") showPage("home");
        else if (page === "games") {
            showPage("home");
            document.querySelector(".games-section")?.scrollIntoView({ behavior: "smooth" });
        } else if (page === "profile") showPage("profile");
    });
});

function loadTelegramUser() {
    const webApp = window.Telegram?.WebApp;
    if (webApp) {
        webApp.ready();
        webApp.expand();
    }

    const tgUser = webApp?.initDataUnsafe?.user;

    if (tgUser && tgUser.id) {
        userData.telegram_id = String(tgUser.id);
        userData.first_name = tgUser.first_name || "User";
        userData.last_name = tgUser.last_name || "";
        userData.username = tgUser.username ? `@${tgUser.username}` : "";

        const fullName = `${userData.first_name} ${userData.last_name}`.trim();

        if (profileNameEl) profileNameEl.textContent = fullName;
        if (profilePhoneEl) profilePhoneEl.textContent = userData.username || `ID: ${userData.telegram_id}`;

        syncAndFetchUser();
    } else {
        console.warn("Telegram WebApp user not found, retrying...");
        setTimeout(() => {
            const retryUser = window.Telegram?.WebApp?.initDataUnsafe?.user;
            if (retryUser && retryUser.id) {
                userData.telegram_id = String(retryUser.id);
                userData.first_name = retryUser.first_name || "User";
                userData.username = retryUser.username ? `@${retryUser.username}` : "";
                syncAndFetchUser();
            }
        }, 500);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    loadTelegramUser();
    setupFormSubmitListeners();
    updateBalanceUI("0.00");
    render600BingoCards();
   
 // 🏆 የቅርብ አሸናፊዎችን ዳታ መሳብ እና ሰዓት ቆጣሪ ማስጀመር
    fetchRecentWinners();
    setInterval(rotateWinnerDisplay, 3500);
    setInterval(fetchRecentWinners, 60000);
});

// =========================================================
// 🏆 RECENT WINNERS TICKER LOGIC
// =========================================================

// 1. ከ Backend አሸናፊዎችን መሳብ
async function fetchRecentWinners() {
    try {
        const response = await fetch('/api/games/recent_winners');
        if (!response.ok) return;
        const data = await response.json();
        if (data && data.length > 0) {
            recentWinners = data;
        }
    } catch (err) {
        console.error("Winners fetching failed:", err);
    }
}

// 2. ጽሁፉን ተራ በተራ በ Animation መቀየር
function rotateWinnerDisplay() {
    const winAmountEl = document.getElementById('winAmountText');
    if (!winAmountEl || recentWinners.length === 0) return;

    // <small>WIN</small> የሚለውን ለማግኘት
    const winLabelEl = winAmountEl.previousElementSibling; 

    // Fade Out ለማድረግ
    winAmountEl.style.transition = "opacity 0.4s ease";
    if (winLabelEl) winLabelEl.style.transition = "opacity 0.4s ease";
    
    winAmountEl.style.opacity = "0";
    if (winLabelEl) winLabelEl.style.opacity = "0";

    setTimeout(() => {
        const winner = recentWinners[currentWinnerIndex];
        
        // <small> የሚለውን ወደ አሸናፊው ስም መቀየር
        if (winLabelEl) {
            winLabelEl.innerText = winner.name;
            winLabelEl.style.opacity = "1";
        }

        // <strong id="winAmountText"> የሚለውን ወደ ገንዘቡ መጠን መቀየር
        winAmountEl.innerText = `${Number(winner.amount).toFixed(2)} ETB`;
        winAmountEl.style.opacity = "1";

        // ወደ ሚቀጥለው አሸናፊ መሸጋገር
        currentWinnerIndex = (currentWinnerIndex + 1) % recentWinners.length;
    }, 400);
}

// =========================================================
// 🎰 LUCKY SLOTS
// =========================================================

function updateSlotsBalance() {
    const slotsBalanceEl = document.getElementById("slotsBalance");

    if (!slotsBalanceEl) return;

    const balance = parseFloat(userData.balance || 0);

    slotsBalanceEl.textContent =
        `${balance.toFixed(2)} ETB`;
}


// ---------------------------------------------------------
// BET BUTTONS
// ---------------------------------------------------------

document.querySelectorAll(".slot-bet-btn").forEach(button => {
    button.addEventListener("click", () => {

        if (slotSpinning) return;

        const bet = parseFloat(button.dataset.slotBet);

        if (!bet) return;

        selectedSlotBet = bet;

        document.querySelectorAll(".slot-bet-btn").forEach(btn => {
            btn.classList.remove("active");
        });

        button.classList.add("active");

        const resultText =
            document.getElementById("slotResultText");

        if (resultText) {
            resultText.textContent =
                `${selectedSlotBet} ETB selected — Ready to spin 🎰`;
        }

        if (window.Telegram?.WebApp?.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.selectionChanged();
        }
    });
});


// ---------------------------------------------------------
// SPIN ANIMATION
// ---------------------------------------------------------

function startSlotAnimation() {

    const reels = [
        document.getElementById("slotReel1"),
        document.getElementById("slotReel2"),
        document.getElementById("slotReel3")
    ];

    reels.forEach(reel => {
        if (reel) {
            reel.classList.add("spinning");
        }
    });

    const animationInterval = setInterval(() => {

        reels.forEach(reel => {

            if (!reel) return;

            const randomIndex =
                Math.floor(Math.random() * slotSymbols.length);

            reel.textContent =
                slotSymbols[randomIndex];
        });

    }, 90);

    return {
        stop: () => {
            clearInterval(animationInterval);

            reels.forEach(reel => {
                if (reel) {
                    reel.classList.remove("spinning");
                }
            });
        }
    };
}


// ---------------------------------------------------------
// SPIN RESULT
// ---------------------------------------------------------

function showSlotResult(data) {

    const reel1 = document.getElementById("slotReel1");
    const reel2 = document.getElementById("slotReel2");
    const reel3 = document.getElementById("slotReel3");

    if (reel1) reel1.textContent = data.symbols[0];
    if (reel2) reel2.textContent = data.symbols[1];
    if (reel3) reel3.textContent = data.symbols[2];

    const resultText =
        document.getElementById("slotResultText");

    if (!resultText) return;

    if (data.win_amount > 0) {

        resultText.textContent =
            `🎉 YOU WON ${Number(data.win_amount).toFixed(2)} ETB — ${data.multiplier}x!`;

        resultText.style.color = "#2ed573";

        if (window.Telegram?.WebApp?.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.notificationOccurred(
                "success"
            );
        }

    } else {

        resultText.textContent =
            "😔 No win this time. Try again!";

        resultText.style.color = "#ff6b6b";
    }
}


// ---------------------------------------------------------
// MAIN SPIN
// ---------------------------------------------------------

async function spinLuckySlots() {

    if (slotSpinning) return;

    if (!userData.telegram_id) {
        showMessage(
            "Telegram Error",
            "Please open the game from Telegram.",
            "⚠️"
        );
        return;
    }

    const balance =
        parseFloat(userData.balance || 0);

    if (balance < selectedSlotBet) {

        showMessage(
            "Insufficient Balance",
            `Your balance is ${balance.toFixed(2)} ETB. You need ${selectedSlotBet.toFixed(2)} ETB to spin.`,
            "💰"
        );

        return;
    }

    const spinBtn =
        document.getElementById("slotSpinBtn");

    const resultText =
        document.getElementById("slotResultText");

    slotSpinning = true;

    if (spinBtn) {
        spinBtn.disabled = true;
        spinBtn.textContent = "🎰 SPINNING...";
    }

    if (resultText) {
        resultText.textContent =
            "🎰 Good luck...";
        resultText.style.color = "";
    }

    const animation =
        startSlotAnimation();

    try {

        const response = await fetch(
            "/api/slots/spin",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    telegram_id: String(userData.telegram_id),
                    bet_amount: selectedSlotBet
                })
            }
        );

        let data = {};

        try {
            data = await response.json();
        } catch (e) {
            data = {};
        }

        if (!response.ok) {

            animation.stop();

            const errorMessage =
                data.detail ||
                data.message ||
                "Spin failed. Please try again.";

            showMessage(
                "Spin Error",
                errorMessage,
                "⚠️"
            );

            return;
        }

        // Give the animation a little time
        await new Promise(resolve =>
            setTimeout(resolve, 700)
        );

        animation.stop();

        showSlotResult(data);

        if (data.balance !== undefined) {

            userData.balance =
                Number(data.balance).toFixed(2);

            updateBalanceUI(userData.balance);
            updateSlotsBalance();

        } else {

            await syncAndFetchUser();
            updateSlotsBalance();
        }

    } catch (error) {

        console.error(
            "Lucky Slots Error:",
            error
        );

        animation.stop();

        showMessage(
            "Connection Error",
            "The spin could not be completed. Please try again.",
            "⚠️"
        );

    } finally {

        slotSpinning = false;

        if (spinBtn) {
            spinBtn.disabled = false;
            spinBtn.textContent = "🎰 SPIN";
        }
    }
}


// ---------------------------------------------------------
// SPIN BUTTON
// ---------------------------------------------------------

document.getElementById("slotSpinBtn")?.addEventListener(
    "click",
    spinLuckySlots
);


// ---------------------------------------------------------
// BACK BUTTON
// ---------------------------------------------------------

document.getElementById("slotsBackBtn")?.addEventListener(
    "click",
    () => {

        if (slotSpinning) return;

        showPage("home");

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });
    }
);

/* =========================================================
   QUICK_BIRR GAMES - PLINKO ENGINE
   Backend-connected Plinko Game Logic
   ========================================================= */

// Plinko DOM Elements Selection
const plinkoBalanceEl = document.getElementById("plinkoBalance");
const plinkoBoard = document.getElementById("plinkoBoard");
const plinkoBall = document.getElementById("plinkoBall");
const plinkoDropBtn = document.getElementById("plinkoDropBtn");
const plinkoResultText = document.getElementById("plinkoResultText");
const plinkoMultiplierElements = document.querySelectorAll(".plinko-multiplier-slot");

/* =========================================================
   UPDATE PLINKO BALANCE
========================================================= */
function updatePlinkoBalance() {
    const el = plinkoBalanceEl || document.getElementById("plinkoBalance");
    if (!el) return;

    const balance = parseFloat(userData?.balance || 0);
    el.textContent = `${balance.toFixed(2)} ETB`;

    if (balance <= 0) {
        el.classList.add("low");
    } else {
        el.classList.remove("low");
    }
}

/* =========================================================
   OPEN PLINKO
========================================================= */
function openPlinkoGame() {
    if (typeof showPage === "function") {
        showPage("plinko");
    }
    updatePlinkoBalance();
    resetPlinkoBoard();

    if (plinkoResultText) {
        plinkoResultText.textContent = "Choose your bet and drop the ball";
        plinkoResultText.classList.remove("win", "jackpot");
    }
}

/* =========================================================
   RESET BOARD
========================================================= */
function resetPlinkoBoard() {
    if (plinkoBall) {
        plinkoBall.classList.remove("active", "drop-animation");
        plinkoBall.style.left = "50%";
        plinkoBall.style.transform = "translateX(-50%)";
    }

    plinkoMultiplierElements.forEach(element => {
        element.classList.remove("win");
    });
}

/* =========================================================
   BET BUTTONS
========================================================= */
document.querySelectorAll(".plinko-bet-btn").forEach(button => {
    button.addEventListener("click", () => {
        if (plinkoPlaying) return;

        const bet = parseFloat(button.dataset.plinkoBet);
        if (!bet) return;

        selectedPlinkoBet = bet;

        document.querySelectorAll(".plinko-bet-btn").forEach(btn => {
            btn.classList.remove("active");
        });

        button.classList.add("active");

        if (plinkoResultText) {
            plinkoResultText.textContent = `${bet} ETB selected — Ready to drop 🎯`;
            plinkoResultText.classList.remove("win", "jackpot");
        }

        if (window.Telegram?.WebApp?.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.selectionChanged();
        }
    });
});

/* =========================================================
   BALL ANIMATION
========================================================= */
function animatePlinkoBall(resultIndex) {
    return new Promise(resolve => {
        if (!plinkoBall) {
            resolve();
            return;
        }

        resetPlinkoBoard();

        /*
         * Horizontal positions for slots:
         * 0 = far left, 5 = center, 10 = far right
         */
        const horizontalPositions = [8, 16, 25, 34, 42, 50, 58, 66, 75, 84, 92];

        const targetPercent = horizontalPositions[
            Math.max(0, Math.min(resultIndex, horizontalPositions.length - 1))
        ];

        plinkoBall.style.left = "50%";
        plinkoBall.style.top = "18px";
        plinkoBall.classList.add("active");

        requestAnimationFrame(() => {
            setTimeout(() => {
                plinkoBall.classList.add("drop-animation");

                const startTime = performance.now();
                const duration = 1450;

                function moveBall(now) {
                    const elapsed = now - startTime;
                    const progress = Math.min(elapsed / duration, 1);
                    const eased = 1 - Math.pow(1 - progress, 2);

                    const currentPercent = 50 + (targetPercent - 50) * eased;
                    plinkoBall.style.left = `${currentPercent}%`;

                    if (progress < 1) {
                        requestAnimationFrame(moveBall);
                    } else {
                        plinkoBall.style.left = `${targetPercent}%`;
                        setTimeout(resolve, 120);
                    }
                }

                requestAnimationFrame(moveBall);
            }, 80);
        });
    });
}

/* =========================================================
   HIGHLIGHT RESULT
========================================================= */
function highlightPlinkoResult(resultIndex, multiplier, winAmount) {
    plinkoMultiplierElements.forEach(element => {
        element.classList.remove("win");
    });

    const resultElement = plinkoMultiplierElements[resultIndex];
    if (resultElement) {
        resultElement.classList.add("win");
    }

    if (!plinkoResultText) return;

    if (multiplier >= 10) {
        plinkoResultText.textContent = `🎉 JACKPOT! +${Number(winAmount).toFixed(2)} ETB — 10x!`;
        plinkoResultText.classList.add("jackpot");

        if (window.Telegram?.WebApp?.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.notificationOccurred("success");
        }
    } else if (multiplier >= 1) {
        plinkoResultText.textContent = `🎉 YOU WON ${Number(winAmount).toFixed(2)} ETB — ${multiplier}x!`;
        plinkoResultText.classList.add("win");

        if (window.Telegram?.WebApp?.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.notificationOccurred("success");
        }
    } else if (multiplier > 0) {
        plinkoResultText.textContent = `💰 ${Number(winAmount).toFixed(2)} ETB returned — ${multiplier}x`;
        plinkoResultText.classList.add("win");
    } else {
        plinkoResultText.textContent = "😢 No prize this time. Try again!";
        plinkoResultText.classList.remove("win", "jackpot");
    }
}

/* =========================================================
   DROP BALL
========================================================= */
async function dropPlinkoBall() {
    if (plinkoPlaying) return;

    // Telegram Validation Check
    const telegramId = userData?.telegram_id || window.Telegram?.WebApp?.initDataUnsafe?.user?.id;

    if (!telegramId) {
        if (typeof showMessage === "function") {
            showMessage("Telegram Error", "Please open the game from Telegram.", "⚠️");
        } else {
            alert("Please open the game from Telegram.");
        }
        return;
    }

    // Current Balance Check
    const balance = parseFloat(userData?.balance || 0);

    if (balance < selectedPlinkoBet) {
        if (typeof showMessage === "function") {
            showMessage("Insufficient Balance", `Your balance is ${balance.toFixed(2)} ETB. You need ${selectedPlinkoBet.toFixed(2)} ETB to play.`, "💰");
        } else {
            alert(`Your balance is ${balance.toFixed(2)} ETB. You need ${selectedPlinkoBet.toFixed(2)} ETB to play.`);
        }
        return;
    }

    // Start Game
    plinkoPlaying = true;
    const btn = plinkoDropBtn || document.getElementById("plinkoDropBtn");

    if (btn) {
        btn.disabled = true;
        btn.textContent = "🎯 DROPPING...";
    }

    if (plinkoResultText) {
        plinkoResultText.textContent = "🎯 Ball is dropping...";
        plinkoResultText.classList.remove("win", "jackpot");
    }

    try {
        // Backend API Call
        const response = await fetch("/api/plinko/drop", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                telegram_id: String(telegramId),
                bet_amount: selectedPlinkoBet
            })
        });

        let data = {};
        try {
            data = await response.json();
        } catch (e) {
            data = {};
        }

        if (!response.ok || !data.success) {
            if (typeof showMessage === "function") {
                showMessage("Plinko Error", data.detail || data.message || "Plinko game could not be completed.", "⚠️");
            } else {
                alert(data.detail || data.message || "Plinko game could not be completed.");
            }
            return;
        }

        const resultIndex = Number(data.result_index);
        const multiplier = Number(data.multiplier);
        const winAmount = Number(data.win_amount);

        // Animate Ball
        await animatePlinkoBall(resultIndex);

        // Highlight Result Slot
        highlightPlinkoResult(resultIndex, multiplier, winAmount);

        // Update User Balance
        if (data.balance !== undefined && data.balance !== null) {
            userData.balance = Number(data.balance);

            if (typeof updateBalanceUI === "function") {
                updateBalanceUI(userData.balance);
            }
            updatePlinkoBalance();
        } else if (typeof syncAndFetchUser === "function") {
            await syncAndFetchUser();
            updatePlinkoBalance();
        }

        // Haptic Feedback
        if (window.Telegram?.WebApp?.HapticFeedback) {
            if (multiplier > 0) {
                window.Telegram.WebApp.HapticFeedback.notificationOccurred("success");
            } else {
                window.Telegram.WebApp.HapticFeedback.notificationOccurred("warning");
            }
        }

    } catch (error) {
        console.error("Plinko Error:", error);
        if (typeof showMessage === "function") {
            showMessage("Connection Error", "The Plinko game could not be completed. Please try again.", "⚠️");
        } else {
            alert("The Plinko game could not be completed. Please try again.");
        }
    } finally {
        plinkoPlaying = false;
        if (btn) {
            btn.disabled = false;
            btn.textContent = "🎯 DROP BALL";
        }
    }
}

/* =========================================================
   EVENT LISTENERS
========================================================= */
const dropBtn = plinkoDropBtn || document.getElementById("plinkoDropBtn");
if (dropBtn) {
    dropBtn.addEventListener("click", dropPlinkoBall);
}

document.getElementById("plinkoBackBtn")?.addEventListener("click", () => {
    if (plinkoPlaying) return;
    if (typeof showPage === "function") {
        showPage("home");
    }
});

/* =========================================================
   INITIAL PLINKO STATE
========================================================= */
function initializePlinko() {
    document.querySelectorAll(".plinko-bet-btn").forEach(button => {
        const bet = Number(button.dataset.plinkoBet);
        if (bet === selectedPlinkoBet) {
            button.classList.add("active");
        } else {
            button.classList.remove("active");
        }
    });

    updatePlinkoBalance();
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializePlinko);
} else {
    initializePlinko();
}

// =========================================================
// ROULETTE GAME LOGIC & ENGINE
// =========================================================

// European Roulette Wheel Sequence (Clockwise: 0 - 36)
const ROULETTE_NUMBERS = [
    0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5,
    24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26
];

// Red & Black Numbers Sets
const RED_NUMBERS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36];

// Roulette Active State Management
let rouletteState = {
    selectedBetAmount: 10.0, // Default selected bet amount (10, 20, 50 ETB)
    selectedBetType: null,   // 'red', 'black', 'green', or 'number'
    selectedBetValue: null,  // 0 - 36 if type is 'number'
    isSpinning: false,
    currentRotation: 0       // Accrued wheel rotation degree
};

// ---------------------------------------------------------
// 1. INITIALIZATION & SETUP
// ---------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
    renderRouletteNumberGrid();
    initRouletteEventListeners();
    updateRouletteBalance();
});

// 1-36 የቁጥር Grid በ HTML #rouletteNumberGrid ውስጥ በዳይናሚክ መፍጠሪያ
function renderRouletteNumberGrid() {
    const gridEl = document.getElementById('rouletteNumberGrid');
    if (!gridEl) return;

    gridEl.innerHTML = ''; // Clear existing content

    for (let i = 1; i <= 36; i++) {
        const isRed = RED_NUMBERS.includes(i);
        const numBtn = document.createElement('button');
        numBtn.type = 'button';
        numBtn.className = `roulette-number-btn ${isRed ? 'red' : 'black'}`;
        numBtn.dataset.value = i;
        numBtn.innerText = i;
        gridEl.appendChild(numBtn);
    }
}

// ባላንስ በየጊዜው ማደሻ Helper
function updateRouletteBalance() {
    const rBalance = document.getElementById('rouletteBalance');
    if (rBalance && typeof userData !== 'undefined') {
        rBalance.innerText = `${parseFloat(userData.balance || 0).toFixed(2)} ETB`;
    }
}

// ---------------------------------------------------------
// 2. EVENT LISTENERS
// ---------------------------------------------------------
function initRouletteEventListeners() {
    // A. Back Button - ወደ ዋናው ገፅ መመለሻ
    const backBtn = document.getElementById('rouletteBackBtn');
    if (backBtn) {
        backBtn.addEventListener('click', () => {
            if (rouletteState.isSpinning) return;
            if (typeof showPage === 'function') {
                showPage('home');
            } else {
                const rouletteView = document.getElementById('rouletteView');
                if (rouletteView) rouletteView.hidden = true;
            }
        });
    }

    // B. Bet Amount Selection (10, 20, 50 ETB)
    const betBtns = document.querySelectorAll('.roulette-bet-btn');
    betBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            if (rouletteState.isSpinning) return;
            const amount = parseFloat(e.currentTarget.dataset.rouletteBet);
            if ([10, 20, 50].includes(amount)) {
                rouletteState.selectedBetAmount = amount;
                betBtns.forEach(b => b.classList.remove('active'));
                e.currentTarget.classList.add('active');
            }
        });
    });

    // C. Bet on Color Buttons (RED, BLACK, GREEN)
    const colorBtns = document.querySelectorAll('.roulette-color-btn');
    colorBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            if (rouletteState.isSpinning) return;
            const betType = e.currentTarget.dataset.rouletteType; // 'red', 'black', 'green'
            
            clearBetSelections();
            e.currentTarget.classList.add('selected');

            rouletteState.selectedBetType = betType;
            rouletteState.selectedBetValue = (betType === 'green') ? 0 : null;

            updateResultText(`Selected: ${betType.toUpperCase()} (${rouletteState.selectedBetAmount} ETB)`, '');
        });
    });

    // D. Bet on Single Number (Grid Buttons)
    const gridEl = document.getElementById('rouletteNumberGrid');
    if (gridEl) {
        gridEl.addEventListener('click', (e) => {
            if (rouletteState.isSpinning) return;
            const btn = e.target.closest('.roulette-number-btn');
            if (!btn) return;

            const val = parseInt(btn.dataset.value);
            if (!isNaN(val) && val >= 1 && val <= 36) {
                clearBetSelections();
                btn.classList.add('selected');

                rouletteState.selectedBetType = 'number';
                rouletteState.selectedBetValue = val;

                updateResultText(`Selected Number: ${val} (${rouletteState.selectedBetAmount} ETB)`, '');
            }
        });
    }

    // E. Spin Button Click
    const spinBtn = document.getElementById('rouletteSpinBtn');
    if (spinBtn) {
        spinBtn.addEventListener('click', handleRouletteSpin);
    }
}

function clearBetSelections() {
    document.querySelectorAll('.roulette-color-btn').forEach(b => b.classList.remove('selected'));
    document.querySelectorAll('.roulette-number-btn').forEach(b => b.classList.remove('selected'));
}

function updateResultText(msg, statusClass = '') {
    const resText = document.getElementById('rouletteResultText');
    if (resText) {
        resText.innerText = msg;
        resText.className = `roulette-result-text ${statusClass}`;
    }
}

// ---------------------------------------------------------
// 3. EXECUTE SPIN & API CALL
// ---------------------------------------------------------
async function handleRouletteSpin() {
    if (rouletteState.isSpinning) return;

    // 1. Validate Bet Selection
    if (!rouletteState.selectedBetType) {
        if (typeof showMessage === 'function') {
            showMessage("Roulette", "እባክዎን መጀመሪያ ውርርድ (ከለር ወይም ቁጥር) ይምረጡ!", "⚠️");
        } else {
            alert("እባክዎን መጀመሪያ ውርርድ (ከለር ወይም ቁጥር) ይምረጡ!");
        }
        return;
    }

    // 2. Balance Check
    const currentBalance = parseFloat(userData?.balance || 0);

    if (currentBalance < rouletteState.selectedBetAmount) {
        if (typeof showMessage === 'function') {
            showMessage("ባላንስ ማነስ", "የበቂ ባላንስ የለዎትም! እባክዎን ዴፖዚት ያድርጉ።", "💳");
        } else {
            alert("የበቂ ባላንስ የለዎትም! እባክዎን ዴፖዚት ያድርጉ።");
        }
        return;
    }

    rouletteState.isSpinning = true;
    setSpinButtonState(false);
    updateResultText("Spinning... Good luck!", '');

    // Telegram ID ማግኛ
    const telegramId = String(userData?.telegram_id || window.myTelegramId || "12345678");

    try {
        // Backend API (`/api/roulette/spin`) ጥሪ
        const response = await fetch('/api/roulette/spin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_id: telegramId,
                bet_amount: rouletteState.selectedBetAmount,
                bet_type: rouletteState.selectedBetType,
                bet_value: rouletteState.selectedBetValue
            })
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            const errModal = typeof showMessage === 'function' ? showMessage("ስህተት", data.detail || "ስህተት ተፈጥሯል!", "❌") : alert(data.detail || "ስህተት ተፈጥሯል!");
            rouletteState.isSpinning = false;
            setSpinButtonState(true);
            return;
        }

        // 3. Wheel Spinning Animation ማሰራት
        animateWheel(data.winning_number, () => {
            // 4. ውጤቱን ማሳወቅ እና ባላንስ ማደስ
            handleSpinSuccess(data);
            rouletteState.isSpinning = false;
            setSpinButtonState(true);
        });

    } catch (error) {
        console.error("Roulette Spin Error:", error);
        if (typeof showMessage === 'function') {
            showMessage("ኔትወርክ ስህተት", "የኔትወርክ ስህተት ተፈጥሯል! እባክዎ እንደገና ይሞክሩ።", "📡");
        } else {
            alert("የኔትወርክ ስህተት ተፈጥሯል!");
        }
        rouletteState.isSpinning = false;
        setSpinButtonState(true);
    }
}

// ---------------------------------------------------------
// 4. ANIMATION LOGIC
// ---------------------------------------------------------
function animateWheel(winningNumber, onComplete) {
    const wheelEl = document.getElementById('rouletteWheel');
    const resultNumSpan = document.querySelector('#rouletteResultNumber');

    if (!wheelEl) {
        setTimeout(onComplete, 3000);
        return;
    }

    const numberIndex = ROULETTE_NUMBERS.indexOf(winningNumber);
    const degreesPerSpot = 360 / 37;
    
    // ድግሪውን ሁልጊዜ ወደፊት ለመዞር Cumulative ድግሪ እንጠቀማለን
    const extraRounds = 360 * 5; // 5 ሙሉ ዙር
    const targetDegree = extraRounds + (numberIndex * degreesPerSpot);
    
    rouletteState.currentRotation += targetDegree;

    wheelEl.style.transition = 'transform 4s cubic-bezier(0.12, 0.7, 0.15, 1)';
    wheelEl.style.transform = `rotate(${rouletteState.currentRotation}deg)`;

    // Spinning በሚያደርግበት ወቅት ቁጥሮቹ በማዕከሉ ላይ በፍጥነት እንዲቀያየሩ የማድረጊያ Effect
    let counter = 0;
    const interval = setInterval(() => {
        if (resultNumSpan) {
            resultNumSpan.innerText = ROULETTE_NUMBERS[counter % 37];
        }
        counter++;
    }, 70);

    setTimeout(() => {
        clearInterval(interval);
        if (resultNumSpan) {
            resultNumSpan.innerText = winningNumber;
        }
        onComplete();
    }, 4200);
}

// ---------------------------------------------------------
// 5. RESULT & BALANCE DISPLAY
// ---------------------------------------------------------
function handleSpinSuccess(data) {
    const { winning_number, winning_color, payout, balance, message } = data;

    // A. User Balance UI አዘምን
    if (balance !== undefined) {
        if (typeof userData !== 'undefined') userData.balance = balance;
        
        const formattedBalance = `${parseFloat(balance).toFixed(2)} ETB`;
        const rBalance = document.getElementById('rouletteBalance');
        const mainBalance = document.getElementById('balance');
        const dashBalance = document.getElementById('dashBalance');
        
        if (rBalance) rBalance.innerText = formattedBalance;
        if (mainBalance) mainBalance.innerText = formattedBalance;
        if (dashBalance) dashBalance.innerText = formattedBalance;
    }

    // B. Result Text Message Update (.win / .lose classes)
    const isWin = payout > 0;
    updateResultText(message, isWin ? 'win' : 'lose');

    // C. Center Number Color Update
    const resultNumSpan = document.querySelector('#rouletteResultNumber');
    if (resultNumSpan) {
        resultNumSpan.style.color = winning_color === 'red' ? '#ff4757' : (winning_color === 'black' ? '#ffffff' : '#2ed573');
    }

    // Spin ከተጠናቀቀ በኋላ ምርጫዎችን Reset ማድረግ
    clearBetSelections();
    rouletteState.selectedBetType = null;
    rouletteState.selectedBetValue = null;
}

function setSpinButtonState(enabled) {
    const spinBtn = document.getElementById('rouletteSpinBtn');
    if (spinBtn) {
        spinBtn.disabled = !enabled;
    }
}

// =========================================================
// BLACKJACK GAME LOGIC & ENGINE
// =========================================================

// 🃏 Blackjack Active State Management
let blackjackState = {
    selectedBetAmount: 10.0,
    isPlaying: false
};

// ---------------------------------------------------------
// 1. INITIALIZATION & SETUP
// ---------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
    initBlackjackEventListeners();
    updateBlackjackBalance();
});

// ባላንስ ማደሻ Helper
function updateBlackjackBalance() {
    const bBalance = document.getElementById("blackjackBalance");

    if (bBalance && typeof userData !== "undefined") {
        bBalance.innerText =
            `${parseFloat(userData.balance || 0).toFixed(2)} ETB`;
    }
}

// ---------------------------------------------------------
// 2. EVENT LISTENERS
// ---------------------------------------------------------

function initBlackjackEventListeners() {

    // A. Back Button
    const backBtn = document.getElementById("blackjackBackBtn");

    if (backBtn) {
        backBtn.addEventListener("click", () => {

            if (blackjackState.isPlaying) return;

            if (typeof showPage === "function") {
                showPage("home");
            } else {
                const blackjackView =
                    document.getElementById("blackjackView");

                if (blackjackView) {
                    blackjackView.hidden = true;
                }
            }
        });
    }

    // B. Bet Amount Selection (10, 20, 50 ETB)
    const betBtns =
        document.querySelectorAll(".blackjack-bet-btn");

    betBtns.forEach(btn => {

        btn.addEventListener("click", (e) => {

            if (blackjackState.isPlaying) return;

            const amount = parseFloat(
                e.currentTarget.dataset.blackjackBet
            );

            if ([10, 20, 50].includes(amount)) {

                blackjackState.selectedBetAmount = amount;

                betBtns.forEach(b =>
                    b.classList.remove("active")
                );

                e.currentTarget.classList.add("active");
            }
        });
    });

    // C. START GAME
    const startBtn =
        document.getElementById("blackjackStartBtn");

    if (startBtn) {
        startBtn.addEventListener(
            "click",
            startBlackjackGame
        );
    }

    // D. HIT
    const hitBtn =
        document.getElementById("blackjackHitBtn");

    if (hitBtn) {
        hitBtn.addEventListener(
            "click",
            hitBlackjack
        );
    }

    // E. STAND
    const standBtn =
        document.getElementById("blackjackStandBtn");

    if (standBtn) {
        standBtn.addEventListener(
            "click",
            standBlackjack
        );
    }

    // F. NEW GAME
    const newBtn =
        document.getElementById("blackjackNewBtn");

    if (newBtn) {
        newBtn.addEventListener("click", () => {

            resetBlackjackUI();

            blackjackState.isPlaying = false;

            setBlackjackButtonsState({
                start: true,
                hit: false,
                stand: false,
                newGame: false
            });

            updateBlackjackBalance();
        });
    }
}

// ---------------------------------------------------------
// 3. START BLACKJACK
// ---------------------------------------------------------

async function startBlackjackGame() {

    if (blackjackState.isPlaying) return;

    const currentBalance =
        parseFloat(userData?.balance || 0);

    // Balance Check
    if (
        currentBalance <
        blackjackState.selectedBetAmount
    ) {

        if (typeof showMessage === "function") {

            showMessage(
                "ባላንስ ማነስ",
                "የበቂ ባላንስ የለዎትም! እባክዎን ዴፖዚት ያድርጉ።",
                "💳"
            );

        } else {

            alert(
                "የበቂ ባላንስ የለዎትም!"
            );
        }

        return;
    }

    blackjackState.isPlaying = true;

    setBlackjackButtonsState({
        start: false,
        hit: false,
        stand: false,
        newGame: false
    });

    updateBlackjackResult(
        "Dealing cards...",
        ""
    );

    const telegramId = String(
        userData?.telegram_id ||
        window.myTelegramId ||
        "12345678"
    );

    try {

        const response = await fetch(
            "/api/blackjack/start",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    telegram_id: telegramId,
                    bet_amount:
                        blackjackState.selectedBetAmount
                })
            }
        );

        const data = await response.json();

        if (!response.ok || !data.success) {

            showBlackjackError(
                data.detail ||
                "Blackjack game could not start."
            );

            blackjackState.isPlaying = false;

            setBlackjackButtonsState({
                start: true,
                hit: false,
                stand: false,
                newGame: false
            });

            return;
        }

        // Save game
        currentBlackjackGameId = data.game_id;

        // Update balance
        updateBlackjackBalanceFromResponse(data);

        // Render cards
        renderBlackjackCards(data);

        // Handle finished natural Blackjack
        if (data.status === "finished") {

            handleBlackjackResult(data);

            return;
        }

        // Game continues
        setBlackjackButtonsState({
            start: false,
            hit: true,
            stand: true,
            newGame: false
        });

        updateBlackjackResult(
            data.message || "Hit or Stand?",
            ""
        );

    } catch (error) {

        console.error(
            "Blackjack Start Error:",
            error
        );

        showBlackjackError(
            "የኔትወርክ ስህተት ተፈጥሯል!"
        );

        blackjackState.isPlaying = false;

        setBlackjackButtonsState({
            start: true,
            hit: false,
            stand: false,
            newGame: false
        });
    }
}

// ---------------------------------------------------------
// 4. HIT
// ---------------------------------------------------------

async function hitBlackjack() {

    if (!blackjackState.isPlaying) return;

    const telegramId = String(
        userData?.telegram_id ||
        window.myTelegramId ||
        "12345678"
    );

    setBlackjackButtonsState({
        start: false,
        hit: false,
        stand: false,
        newGame: false
    });

    updateBlackjackResult(
        "Drawing card...",
        ""
    );

    try {

        const response = await fetch(
            "/api/blackjack/hit",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    telegram_id: telegramId
                })
            }
        );

        const data = await response.json();

        if (!response.ok || !data.success) {

            showBlackjackError(
                data.detail ||
                "Could not draw card."
            );

            setBlackjackButtonsState({
                start: false,
                hit: true,
                stand: true,
                newGame: false
            });

            return;
        }

        renderBlackjackCards(data);

        updateBlackjackBalanceFromResponse(data);

        // Finished = Bust / 21 / resolved
        if (data.status === "finished") {

            handleBlackjackResult(data);

            return;
        }

        // Continue playing
        setBlackjackButtonsState({
            start: false,
            hit: true,
            stand: true,
            newGame: false
        });

        updateBlackjackResult(
            data.message || "Hit or Stand?",
            ""
        );

    } catch (error) {

        console.error(
            "Blackjack Hit Error:",
            error
        );

        showBlackjackError(
            "የኔትወርክ ስህተት ተፈጥሯል!"
        );

        setBlackjackButtonsState({
            start: false,
            hit: true,
            stand: true,
            newGame: false
        });
    }
}

// ---------------------------------------------------------
// 5. STAND
// ---------------------------------------------------------

async function standBlackjack() {

    if (!blackjackState.isPlaying) return;

    const telegramId = String(
        userData?.telegram_id ||
        window.myTelegramId ||
        "12345678"
    );

    setBlackjackButtonsState({
        start: false,
        hit: false,
        stand: false,
        newGame: false
    });

    updateBlackjackResult(
        "Dealer is playing...",
        ""
    );

    try {

        const response = await fetch(
            "/api/blackjack/stand",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    telegram_id: telegramId
                })
            }
        );

        const data = await response.json();

        if (!response.ok || !data.success) {

            showBlackjackError(
                data.detail ||
                "Could not stand."
            );

            setBlackjackButtonsState({
                start: false,
                hit: true,
                stand: true,
                newGame: false
            });

            return;
        }

        renderBlackjackCards(data);

        updateBlackjackBalanceFromResponse(data);

        handleBlackjackResult(data);

    } catch (error) {

        console.error(
            "Blackjack Stand Error:",
            error
        );

        showBlackjackError(
            "የኔትወርክ ስህተት ተፈጥሯል!"
        );

        setBlackjackButtonsState({
            start: false,
            hit: true,
            stand: true,
            newGame: false
        });
    }
}

// ---------------------------------------------------------
// 6. RENDER CARDS
// ---------------------------------------------------------

function renderBlackjackCards(data) {

    const playerCardsEl =
        document.getElementById(
            "blackjackPlayerCards"
        );

    const dealerCardsEl =
        document.getElementById(
            "blackjackDealerCards"
        );

    const playerValueEl =
        document.getElementById(
            "blackjackPlayerValue"
        );

    const dealerValueEl =
        document.getElementById(
            "blackjackDealerValue"
        );

    if (!playerCardsEl || !dealerCardsEl) return;

    playerCardsEl.innerHTML = "";
    dealerCardsEl.innerHTML = "";

    // PLAYER CARDS
    (data.player_cards || []).forEach(card => {

        playerCardsEl.appendChild(
            createBlackjackCard(card)
        );
    });

    // DEALER CARDS
    (data.dealer_cards || []).forEach(card => {

        dealerCardsEl.appendChild(
            createBlackjackCard(card)
        );
    });

    if (playerValueEl) {

        playerValueEl.innerText =
            `Value: ${data.player_value ?? "-"}`;
    }

    if (dealerValueEl) {

        dealerValueEl.innerText =
            `Value: ${data.dealer_value ?? "-"}`;
    }
}

// ---------------------------------------------------------
// 7. CREATE CARD UI
// ---------------------------------------------------------

function createBlackjackCard(card) {

    const cardEl =
        document.createElement("div");

    const isRed =
        card.suit === "♥" ||
        card.suit === "♦";

    cardEl.className =
        `blackjack-card ${isRed ? "red" : "black"}`;

    const rankEl =
        document.createElement("div");

    rankEl.className =
        "blackjack-card-rank";

    rankEl.innerText =
        card.rank;

    const suitEl =
        document.createElement("div");

    suitEl.className =
        "blackjack-card-suit";

    suitEl.innerText =
        card.suit;

    cardEl.appendChild(rankEl);
    cardEl.appendChild(suitEl);

    return cardEl;
}

// ---------------------------------------------------------
// 8. RESULT & BALANCE DISPLAY
// ---------------------------------------------------------

function updateBlackjackBalanceFromResponse(data) {

    if (data.balance === undefined) return;

    if (typeof userData !== "undefined") {
        userData.balance = data.balance;
    }

    const formattedBalance =
        `${parseFloat(data.balance).toFixed(2)} ETB`;

    const blackjackBalance =
        document.getElementById(
            "blackjackBalance"
        );

    const mainBalance =
        document.getElementById("balance");

    const dashBalance =
        document.getElementById("dashBalance");

    if (blackjackBalance) {
        blackjackBalance.innerText =
            formattedBalance;
    }

    if (mainBalance) {
        mainBalance.innerText =
            formattedBalance;
    }

    if (dashBalance) {
        dashBalance.innerText =
            formattedBalance;
    }
}

// ---------------------------------------------------------
// 9. RESULT HANDLER
// ---------------------------------------------------------

function handleBlackjackResult(data) {

    blackjackState.isPlaying = false;

    renderBlackjackCards(data);

    updateBlackjackBalanceFromResponse(data);

    const result =
        data.result || "";

    let resultClass = "";

    if (
        result === "win" ||
        result === "blackjack"
    ) {
        resultClass = "win";

    } else if (
        result === "loss" ||
        result === "dealer_blackjack"
    ) {
        resultClass = "lose";
    }

    updateBlackjackResult(
        data.message ||
        getBlackjackResultMessage(data),
        resultClass
    );

    setBlackjackButtonsState({
        start: false,
        hit: false,
        stand: false,
        newGame: true
    });
}

// ---------------------------------------------------------
// 10. RESULT MESSAGE
// ---------------------------------------------------------

function getBlackjackResultMessage(data) {

    const result =
        data.result || "";

    if (result === "blackjack") {
        return "🃏 BLACKJACK! You win!";
    }

    if (result === "win") {
        return "🎉 YOU WIN!";
    }

    if (result === "push") {
        return "🤝 PUSH — Bet returned!";
    }

    if (
        result === "loss" ||
        result === "dealer_blackjack"
    ) {
        return "😔 YOU LOSE!";
    }

    return "Game finished.";
}

// ---------------------------------------------------------
// 11. RESULT TEXT
// ---------------------------------------------------------

function updateBlackjackResult(
    message,
    statusClass = ""
) {

    const resultEl =
        document.getElementById(
            "blackjackResultText"
        );

    if (!resultEl) return;

    resultEl.innerText = message;

    resultEl.className =
        `blackjack-result-text ${statusClass}`;
}

// ---------------------------------------------------------
// 12. BUTTON STATES
// ---------------------------------------------------------

function setBlackjackButtonsState({
    start,
    hit,
    stand,
    newGame
}) {

    const startBtn =
        document.getElementById(
            "blackjackStartBtn"
        );

    const hitBtn =
        document.getElementById(
            "blackjackHitBtn"
        );

    const standBtn =
        document.getElementById(
            "blackjackStandBtn"
        );

    const newBtn =
        document.getElementById(
            "blackjackNewBtn"
        );

    if (startBtn) {
        startBtn.disabled = !start;
    }

    if (hitBtn) {
        hitBtn.disabled = !hit;
    }

    if (standBtn) {
        standBtn.disabled = !stand;
    }

    if (newBtn) {
        newBtn.hidden = !newGame;
    }
}

// ---------------------------------------------------------
// 13. RESET UI
// ---------------------------------------------------------

function resetBlackjackUI() {

    const playerCardsEl =
        document.getElementById(
            "blackjackPlayerCards"
        );

    const dealerCardsEl =
        document.getElementById(
            "blackjackDealerCards"
        );

    const playerValueEl =
        document.getElementById(
            "blackjackPlayerValue"
        );

    const dealerValueEl =
        document.getElementById(
            "blackjackDealerValue"
        );

    if (playerCardsEl) {
        playerCardsEl.innerHTML = "";
    }

    if (dealerCardsEl) {
        dealerCardsEl.innerHTML = "";
    }

    if (playerValueEl) {
        playerValueEl.innerText =
            "Value: -";
    }

    if (dealerValueEl) {
        dealerValueEl.innerText =
            "Value: -";
    }

    updateBlackjackResult(
        "Choose your bet and start the game",
        ""
    );
}

// ---------------------------------------------------------
// 14. ERROR HANDLER
// ---------------------------------------------------------

function showBlackjackError(message) {

    if (typeof showMessage === "function") {

        showMessage(
            "Blackjack",
            message,
            "❌"
        );

    } else {

        alert(message);
    }
}

// Current Blackjack Game ID
let currentBlackjackGameId = null;

// =========================================================
// 💣 MINES GAME LOGIC & ENGINE
// =========================================================

let minesState = {
    selectedBetAmount: 10.0,
    selectedMineCount: 3,
    isPlaying: false,
    gameId: null,
    revealedTiles: []
};

document.addEventListener("DOMContentLoaded", () => {
    initMinesEventListeners();
    renderMinesBoard();
    updateMinesBalance();
});


// =========================================================
// 💰 BALANCE
// =========================================================

function updateMinesBalance() {
    const balanceEl = document.getElementById("minesBalance");

    if (balanceEl && typeof userData !== "undefined") {
        balanceEl.innerText =
            `${parseFloat(userData.balance || 0).toFixed(2)} ETB`;
    }
}


// =========================================================
// 🎮 INITIALIZE
// =========================================================

function initMinesEventListeners() {

    const backBtn = document.getElementById("minesBackBtn");

    if (backBtn) {
        backBtn.addEventListener("click", () => {

            if (minesState.isPlaying) return;

            if (typeof showPage === "function") {
                showPage("home");
            }
        });
    }


    // BET BUTTONS
    const betButtons =
        document.querySelectorAll(".mines-bet-btn");

    betButtons.forEach(btn => {

        btn.addEventListener("click", () => {

            if (minesState.isPlaying) return;

            const amount =
                parseFloat(btn.dataset.minesBet);

            if (![10, 20, 50].includes(amount)) return;

            minesState.selectedBetAmount = amount;

            betButtons.forEach(b =>
                b.classList.remove("active")
            );

            btn.classList.add("active");
        });
    });


    // MINE COUNT BUTTONS
    const countButtons =
        document.querySelectorAll(".mines-count-btn");

    countButtons.forEach(btn => {

        btn.addEventListener("click", () => {

            if (minesState.isPlaying) return;

            const count =
                parseInt(btn.dataset.minesCount);

            if (![3, 5, 10].includes(count)) return;

            minesState.selectedMineCount = count;

            countButtons.forEach(b =>
                b.classList.remove("active")
            );

            btn.classList.add("active");
        });
    });


    // START
    const startBtn =
        document.getElementById("minesStartBtn");

    if (startBtn) {
        startBtn.addEventListener(
            "click",
            startMinesGame
        );
    }


    // CASH OUT
    const cashoutBtn =
        document.getElementById("minesCashoutBtn");

    if (cashoutBtn) {
        cashoutBtn.addEventListener(
            "click",
            cashOutMines
        );
    }


    // NEW GAME
    const newBtn =
        document.getElementById("minesNewBtn");

    if (newBtn) {

        newBtn.addEventListener("click", () => {

            resetMinesUI();

            minesState.isPlaying = false;
            minesState.gameId = null;
            minesState.revealedTiles = [];

            setMinesButtonsState({
                start: true,
                cashout: false,
                newGame: false
            });

            enableMinesSelectors(true);

            updateMinesBalance();
        });
    }
}


// =========================================================
// 🟦 RENDER 25 TILES
// =========================================================

function renderMinesBoard() {

    const board =
        document.getElementById("minesBoard");

    if (!board) return;

    board.innerHTML = "";

    for (let i = 0; i < 25; i++) {

        const tile =
            document.createElement("button");

        tile.type = "button";
        tile.className = "mines-tile";
        tile.dataset.index = i;
        tile.innerText = "💎";

        tile.addEventListener("click", () => {
            revealMineTile(i);
        });

        board.appendChild(tile);
    }
}


// =========================================================
// 🚀 START GAME
// =========================================================

async function startMinesGame() {

    if (minesState.isPlaying) return;

    const balance =
        parseFloat(userData?.balance || 0);

    const bet =
        minesState.selectedBetAmount;

    if (balance < bet) {

        if (typeof showMessage === "function") {

            showMessage(
                "ባላንስ ማነስ",
                "የበቂ ባላንስ የለዎትም! እባክዎን ዴፖዚት ያድርጉ።",
                "💳"
            );

        } else {

            alert("የበቂ ባላንስ የለዎትም!");

        }

        return;
    }


    minesState.isPlaying = true;

    minesState.revealedTiles = [];

    setMinesButtonsState({
        start: false,
        cashout: false,
        newGame: false
    });

    enableMinesSelectors(false);

    resetMinesBoard();

    updateMinesResult(
        "💣 Preparing Mines game...",
        ""
    );


    const telegramId =
        String(
            userData?.telegram_id ||
            window.myTelegramId ||
            "12345678"
        );


    try {

        const response =
            await fetch(
                "/api/mines/start",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        telegram_id: telegramId,
                        bet_amount: bet,
                        mine_count:
                            minesState.selectedMineCount
                    })
                }
            );


        const data =
            await response.json();


        if (!response.ok || !data.success) {

            showMinesError(
                data.detail ||
                "Mines game could not start."
            );

            minesState.isPlaying = false;

            enableMinesSelectors(true);

            setMinesButtonsState({
                start: true,
                cashout: false,
                newGame: false
            });

            return;
        }


        minesState.gameId =
            data.game_id;


        updateMinesBalanceFromResponse(data);


        updateMinesMultiplier(
            data.multiplier || 1
        );


        updateMinesResult(
            data.message ||
            "💎 Choose a tile!",
            ""
        );


        setMinesButtonsState({
            start: false,
            cashout: false,
            newGame: false
        });

    } catch (error) {

        console.error(
            "Mines Start Error:",
            error
        );

        showMinesError(
            "የኔትወርክ ስህተት ተፈጥሯል!"
        );

        minesState.isPlaying = false;

        enableMinesSelectors(true);

        setMinesButtonsState({
            start: true,
            cashout: false,
            newGame: false
        });
    }
}


// =========================================================
// 💎 REVEAL TILE
// =========================================================

async function revealMineTile(index) {

    if (!minesState.isPlaying) return;

    if (
        minesState.revealedTiles.includes(index)
    ) {
        return;
    }


    const telegramId =
        String(
            userData?.telegram_id ||
            window.myTelegramId ||
            "12345678"
        );


    const tiles =
        document.querySelectorAll(
            ".mines-tile"
        );

    const tile = tiles[index];

    if (tile) {
        tile.disabled = true;
    }


    try {

        const response =
            await fetch(
                "/api/mines/reveal",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        telegram_id:
                            telegramId,

                        game_id:
                            minesState.gameId,

                        tile_index:
                            index
                    })
                }
            );


        const data =
            await response.json();


        if (!response.ok || !data.success) {

            if (tile) {
                tile.disabled = false;
            }

            showMinesError(
                data.detail ||
                "Could not reveal tile."
            );

            return;
        }


        minesState.revealedTiles.push(index);

        updateMinesBalanceFromResponse(data);


        // SAFE TILE
        if (!data.is_mine) {

            if (tile) {

                tile.classList.add(
                    "safe",
                    "revealed-safe"
                );

                tile.innerText = "💎";
            }


            updateMinesMultiplier(
                data.multiplier || 1
            );


            updateMinesResult(
                data.message ||
                "💎 SAFE! Choose another tile.",
                "win"
            );


            setMinesButtonsState({
                start: false,
                cashout: true,
                newGame: false
            });

            return;
        }


        // MINE
        if (tile) {

            tile.classList.add(
                "mine",
                "revealed-mine"
            );

            tile.innerText = "💣";
        }


        revealAllMines(data);

        handleMinesLoss(data);

    } catch (error) {

        console.error(
            "Mines Reveal Error:",
            error
        );

        if (tile) {
            tile.disabled = false;
        }

        showMinesError(
            "የኔትወርክ ስህተት ተፈጥሯል!"
        );
    }
}


// =========================================================
// 💰 CASH OUT
// =========================================================

async function cashOutMines() {

    if (!minesState.isPlaying) return;

    if (
        minesState.revealedTiles.length === 0
    ) {

        updateMinesResult(
            "💎 First reveal at least one safe tile.",
            ""
        );

        return;
    }


    const telegramId =
        String(
            userData?.telegram_id ||
            window.myTelegramId ||
            "12345678"
        );


    setMinesButtonsState({
        start: false,
        cashout: false,
        newGame: false
    });


    updateMinesResult(
        "💰 Collecting your winnings...",
        ""
    );


    try {

        const response =
            await fetch(
                "/api/mines/cashout",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        telegram_id:
                            telegramId,

                        game_id:
                            minesState.gameId
                    })
                }
            );


        const data =
            await response.json();


        if (!response.ok || !data.success) {

            showMinesError(
                data.detail ||
                "Cash out failed."
            );

            setMinesButtonsState({
                start: false,
                cashout: true,
                newGame: false
            });

            return;
        }


        updateMinesBalanceFromResponse(data);

        updateMinesMultiplier(
            data.multiplier || 1
        );


        minesState.isPlaying = false;


        updateMinesResult(
            data.message ||
            `💰 CASH OUT: ${(data.payout || 0).toFixed(2)} ETB`,
            "win"
        );


        setMinesButtonsState({
            start: false,
            cashout: false,
            newGame: true
        });


        enableMinesSelectors(true);

    } catch (error) {

        console.error(
            "Mines Cashout Error:",
            error
        );

        showMinesError(
            "የኔትወርክ ስህተት ተፈጥሯል!"
        );

        setMinesButtonsState({
            start: false,
            cashout: true,
            newGame: false
        });
    }
}


// =========================================================
// 💣 LOSS
// =========================================================

function handleMinesLoss(data) {

    minesState.isPlaying = false;


    updateMinesMultiplier(0);


    updateMinesResult(
        data.message ||
        "💣 BOOM! You hit a mine!",
        "lose"
    );


    setMinesButtonsState({
        start: false,
        cashout: false,
        newGame: true
    });


    enableMinesSelectors(true);
}


// =========================================================
// 💣 REVEAL ALL MINES
// =========================================================

function revealAllMines(data) {

    const minePositions =
        data.mine_positions || [];


    const tiles =
        document.querySelectorAll(
            ".mines-tile"
        );


    minePositions.forEach(index => {

        const tile = tiles[index];

        if (!tile) return;

        tile.classList.add("mine");

        tile.innerText = "💣";

        tile.disabled = true;
    });


    tiles.forEach(tile => {
        tile.disabled = true;
    });
}


// =========================================================
// 🔄 RESET BOARD
// =========================================================

function resetMinesBoard() {

    const tiles =
        document.querySelectorAll(
            ".mines-tile"
        );


    tiles.forEach((tile, index) => {

        tile.className = "mines-tile";

        tile.innerText = "💎";

        tile.disabled = false;

        tile.dataset.index = index;
    });


    updateMinesMultiplier(1);
}


// =========================================================
// 🔄 RESET UI
// =========================================================

function resetMinesUI() {

    resetMinesBoard();

    updateMinesResult(
        "Choose your bet and start the game",
        ""
    );

    updateMinesMultiplier(1);
}


// =========================================================
// 🎛️ BUTTON STATES
// =========================================================

function setMinesButtonsState({
    start,
    cashout,
    newGame
}) {

    const startBtn =
        document.getElementById(
            "minesStartBtn"
        );

    const cashoutBtn =
        document.getElementById(
            "minesCashoutBtn"
        );

    const newBtn =
        document.getElementById(
            "minesNewBtn"
        );


    if (startBtn) {
        startBtn.disabled = !start;
    }

    if (cashoutBtn) {
        cashoutBtn.disabled = !cashout;
    }

    if (newBtn) {
        newBtn.hidden = !newGame;
    }
}


// =========================================================
// 🔒 ENABLE / DISABLE SELECTORS
// =========================================================

function enableMinesSelectors(enabled) {

    document
        .querySelectorAll(
            ".mines-bet-btn, .mines-count-btn"
        )
        .forEach(btn => {

            btn.disabled = !enabled;

        });
}


// =========================================================
// 📈 MULTIPLIER
// =========================================================

function updateMinesMultiplier(multiplier) {

    const multiplierEl =
        document.getElementById(
            "minesMultiplier"
        );

    if (!multiplierEl) return;

    const value =
        parseFloat(multiplier || 1);

    multiplierEl.innerText =
        `${value.toFixed(2)}x`;
}


// =========================================================
// 📝 RESULT TEXT
// =========================================================

function updateMinesResult(
    message,
    statusClass = ""
) {

    const resultEl =
        document.getElementById(
            "minesResultText"
        );

    if (!resultEl) return;

    resultEl.innerText = message;

    resultEl.className =
        `mines-result-text ${statusClass}`;
}


// =========================================================
// 💰 UPDATE BALANCE FROM SERVER
// =========================================================

function updateMinesBalanceFromResponse(data) {

    if (data.balance === undefined) return;


    if (typeof userData !== "undefined") {
        userData.balance = data.balance;
    }


    const formattedBalance =
        `${parseFloat(data.balance).toFixed(2)} ETB`;


    const minesBalance =
        document.getElementById(
            "minesBalance"
        );

    const mainBalance =
        document.getElementById(
            "balance"
        );

    const dashBalance =
        document.getElementById(
            "dashBalance"
        );


    if (minesBalance) {
        minesBalance.innerText =
            formattedBalance;
    }

    if (mainBalance) {
        mainBalance.innerText =
            formattedBalance;
    }

    if (dashBalance) {
        dashBalance.innerText =
            formattedBalance;
    }
}


// =========================================================
// ❌ ERROR
// =========================================================

function showMinesError(message) {

    if (typeof showMessage === "function") {

        showMessage(
            "Mines",
            message,
            "❌"
        );

    } else {

        alert(message);

    }
}
