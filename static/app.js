/* =========================================================
   QUICK_BIRR GAMES - PART 1 / 3
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
let soundEnabled = true;
let isAutoMark = true;
let markedCellsMap = {}; 
let winnerAutoCloseTimer = null;

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

        if ((data.type === "countdown" || data.type === "time_update") && (data.phase === "PICK" || !data.phase)) {
            currentGameId = data.game_id || currentGameId;
            updateCountdownUI(data);
            recentBallsList = [];
        }

        if (data.type === "taken_cards_update") {
            updateTakenCardsUI(data.taken_cards);
        }

        if (data.type === "phase_change" && (data.phase === "DRAW" || data.phase === "GAME_START")) {
            showPage("bingoLive");
            render75BoardSkeleton();
            renderMyBoughtCards();
        }

        if (data.type === "ball") {
            showPage("bingoLive");
            renderDrawnBall(data);
        }

        if (data.type === "game_over") {
            handleGameOver(data);
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
   QUICK_BIRR GAMES - PART 2 / 3
   ========================================================= */

/* =========================
   DRAW PHASE & BOARD LOGIC
========================= */
function render75BoardSkeleton() {
    const ranges = {
        B: [1, 15], I: [16, 30], N: [31, 45], G: [46, 60], O: [61, 75]
    };

    for (const [letter, range] of Object.entries(ranges)) {
        const container = document.getElementById(`row-${letter}`);
        if (!container) continue;

        container.innerHTML = "";
        for (let i = range[0]; i <= range[1]; i++) {
            const cell = document.createElement("span");
            cell.className = "board-cell";
            cell.id = `cell-ball-${i}`;
            cell.textContent = i;
            container.appendChild(cell);
        }
    }
}

function renderDrawnBall(data) {
    if (data.number) {
        calledNumbersSet.add(data.number);
    }

    const letterEl = document.getElementById("currentBallLetter");
    const numberEl = document.getElementById("currentBallNumber");
    const historyList = document.getElementById("recentBallsList");
    const callBadge = document.getElementById("callCountBadge");
    const gameIdBadge = document.getElementById("gameIdBadge");
    const liveDerashText = document.getElementById("liveDerashText");

    const letter = data.label ? data.label.charAt(0) : (data.letter || 'B');
    const color = getBingoColor(letter);

    if (letterEl) {
        letterEl.textContent = letter;
        letterEl.style.color = color;
    }
    if (numberEl) {
        numberEl.textContent = data.number || "--";
    }
    
    if (callBadge && data.call_count) callBadge.textContent = `Call ${data.call_count}`;
    
    const activeGameId = data.game_id || currentGameId || 0;
    if (gameIdBadge) gameIdBadge.textContent = `Game #${activeGameId}`;

    if (data.derash_amount) {
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

    if (soundEnabled && data.number) {
        try {
            let audio = new Audio(`/static/sounds/${data.number}.mp3.mp3`);
            audio.play().catch(e => console.log("Sound playback prevented:", e));
        } catch (err) {
            console.error("Audio error:", err);
        }
    }

    if (data.number) {
        recentBallsList.unshift({ label: `${letter}${data.number}`, letter: letter, num: data.number });
        if (recentBallsList.length > 10) recentBallsList.pop();
    }

    if (historyList) {
        historyList.innerHTML = "";
        recentBallsList.forEach((b, idx) => {
            const ballItem = document.createElement("div");
            ballItem.className = idx === 0 ? "recent-ball-pill active" : "recent-ball-pill";
            ballItem.style.backgroundColor = getBingoColor(b.letter);
            ballItem.textContent = `${b.letter}${b.num}`;
            historyList.appendChild(ballItem);
        });
    }

    if (isAutoMark && data.number) {
        const matchingCells = document.querySelectorAll(`.cell-${data.number}`);
        matchingCells.forEach(cell => {
            cell.classList.add("marked-auto");
            cell.style.background = color;
            cell.style.color = "#fff";
        });
    }

    autoMarkAllBoughtCards();
    renderMyBoughtCards();
}

function render1000BingoCards() {
    const gridContainer = document.getElementById("cardsGrid");
    if (!gridContainer) return;

    gridContainer.innerHTML = "";
    selectedBingoCards = [];
    temporarilySelectedCards = [];
    updateSelectedCardsUI();

    const fragment = document.createDocumentFragment();
    for (let i = 1; i <= 1000; i++) {
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

/* =========================================================
   QUICK_BIRR GAMES - PART 3 / 3 (MATCHED WITH HTML FORMAT)
   ========================================================= */

function autoMarkAllBoughtCards() {
    if (!selectedBingoCards || selectedBingoCards.length === 0) return;

    selectedBingoCards.forEach(cardNum => {
        if (!markedCellsMap[cardNum]) markedCellsMap[cardNum] = new Set();
        if (isAutoMark) {
            calledNumbersSet.forEach(num => markedCellsMap[cardNum].add(num));
        }
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

    for (let index = 0; index < selectedBingoCards.length; index++) {
        const activeCardNum = selectedBingoCards[index];

        if (!markedCellsMap[activeCardNum]) markedCellsMap[activeCardNum] = new Set();
        if (isAutoMark) {
            calledNumbersSet.forEach(num => markedCellsMap[activeCardNum].add(num));
        }

        try {
            const res = await fetch(`/api/cards/get_matrix?card_number=${activeCardNum}`);
            const data = await res.json();
            const matrix = data.matrix;

            const cardBox = document.createElement("div");
            cardBox.className = "single-card-block";
            cardBox.style.cssText = "background:#181c26; border:1px solid #ff9f43; border-radius:12px; padding:10px; margin-bottom:12px;";

            let html = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div class="card-title-label" style="color: #ffd700; font-weight: bold; font-size: 14px;">
                        ካርቴላ #${activeCardNum}
                    </div>
                    <button onclick="toggleMarkingMode()" style="background: ${isAutoMark ? '#2ed573' : '#718093'}; color: white; border: none; padding: 4px 8px; font-size: 11px; font-weight: bold; border-radius: 4px; cursor:pointer;">
                        ${isAutoMark ? "🤖 Auto: ON" : "🖐 Manual"}
                    </button>
                </div>
                <div class="bingo-header-letters" style="display:grid; grid-template-columns: repeat(5, 1fr); gap: 4px; text-align:center; font-weight:bold; margin-bottom: 5px;">
                    <span style="background:${getBingoColor('B')}; border-radius:4px;">B</span>
                    <span style="background:${getBingoColor('I')}; border-radius:4px;">I</span>
                    <span style="background:${getBingoColor('N')}; border-radius:4px;">N</span>
                    <span style="background:${getBingoColor('G')}; border-radius:4px;">G</span>
                    <span style="background:${getBingoColor('O')}; border-radius:4px;">O</span>
                </div>
                <div class="bingo-card-grid-5x5" style="display:grid; grid-template-columns: repeat(5, 1fr); gap:6px;">
            `;

            matrix.forEach(row => {
                row.forEach(cell => {
                    if (cell === "FREE" || cell === 0) {
                        html += `<div class="bingo-cell free-star" style="background:#ffbc00; color:#000; display:flex; justify-content:center; align-items:center; aspect-ratio:1; border-radius:6px; font-weight:bold;">★</div>`;
                    } else {
                        const isMarkedInState = markedCellsMap[activeCardNum].has(cell);
                        const isCalled = calledNumbersSet.has(cell);

                        if (isCalled && (isAutoMark || isMarkedInState)) {
                            let letterPrefix = cell <= 15 ? 'B' : cell <= 30 ? 'I' : cell <= 45 ? 'N' : cell <= 60 ? 'G' : 'O';
                            const savedColor = getBingoColor(letterPrefix);
                            markedCellsMap[activeCardNum].add(cell);

                            html += `<div class="bingo-cell cell-${cell} marked-auto" style="background:${savedColor} !important; color:#fff; display:flex; justify-content:center; align-items:center; aspect-ratio:1; border-radius:6px; font-weight:bold; cursor:pointer;" onclick="handleManualCellClick(this, ${cell}, ${activeCardNum})">${cell}</div>`;
                        } else {
                            html += `<div class="bingo-cell cell-${cell}" style="background:#252634; color:#fff; display:flex; justify-content:center; align-items:center; aspect-ratio:1; border-radius:6px; font-weight:bold; cursor:pointer;" onclick="handleManualCellClick(this, ${cell}, ${activeCardNum})">${cell}</div>`;
                        }
                    }
                });
            });

            html += `</div>`;
            cardBox.innerHTML = html;
            container.appendChild(cardBox);
        } catch (e) {
            console.error("Matrix load error", e);
        }
    }
}

function toggleMarkingMode() {
    isAutoMark = !isAutoMark;
    if (isAutoMark) autoMarkAllBoughtCards();
    renderMyBoughtCards(); 
}

function handleManualCellClick(cellElement, cellNumber, activeCardNum) {
    if (!markedCellsMap[activeCardNum]) markedCellsMap[activeCardNum] = new Set();

    const isBallDrawn = calledNumbersSet.has(cellNumber);

    if (isBallDrawn) {
        markedCellsMap[activeCardNum].add(cellNumber);
        let letterPrefix = cellNumber <= 15 ? 'B' : cellNumber <= 30 ? 'I' : cellNumber <= 45 ? 'N' : cellNumber <= 60 ? 'G' : 'O';
        const ballColor = getBingoColor(letterPrefix);
        cellElement.style.background = ballColor;
        cellElement.style.color = "#fff";
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

/* =========================================================
   GAME OVER & WINNERS LOGIC
========================================================= */
function handleGameOver(data) {
    const winnerModalEl = document.getElementById('winnerModal');
    const winnersList = data.winners || [];
    
    if (winnerModalEl && winnersList.length > 0) {
        let modalContentContainer = winnerModalEl.querySelector('.modal-card') || winnerModalEl;
        
        let winnersHTML = `
            <div style="text-align:center; padding:10px; color:#fff;">
                <h2 style="color:#ff9f43; margin:0 0 10px 0; font-size:24px;">🎉 BINGO! 🎉</h2>
                <div style="font-size:13px; color:#2ed573; margin-bottom:12px;">በዚህ ዙር አጠቃላይ ${winnersList.length} አሸናፊ(ዎች) ወጥተዋል!</div>
                <div style="max-height: 350px; overflow-y: auto; text-align: left; padding-right:5px;">
        `;

        winnersList.forEach((winner, index) => {
            const wName = winner.telegram_name || `User_${winner.winner_id || winner.telegram_id}`;
            const phoneNum = winner.phone_number || "አልተመዘገበም";
            const cNum = winner.card_number || "N/A";
            const pAmt = winner.prize || 0;
            const cardMatrixNumbers = winner.card_numbers || [];
            const winningNumbers = winner.winning_numbers || [];

            winnersHTML += `
                <div style="background:#222736; border:1px solid #ff9f43; border-radius:10px; padding:10px; margin-bottom:12px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <span style="font-weight:bold; color:#ff9f43; font-size:13px;">አሸናፊ #${index + 1}: ${wName}</span>
                        <span style="background:#ffbc00; color:#000; font-size:11px; padding:2px 6px; border-radius:4px; font-weight:bold;">#${cNum}</span>
                    </div>
                    <div style="font-size:12px; color:#a0a0a0; margin-bottom:2px;">📞 ስልክ: ${phoneNum}</div>
                    
                    <div style="display:grid; grid-template-columns: repeat(5, 1fr); gap:3px; margin: 8px 0;">
            `;

            if (cardMatrixNumbers.length === 25) {
                cardMatrixNumbers.forEach((num) => {
                    const isWinningNum = winningNumbers.includes(num);
                    const isFreeSpace = num === 0 || num === "★" || num === "FREE";
                    const cellDisplay = isFreeSpace ? "★" : num;

                    if (isWinningNum || isFreeSpace) {
                        winnersHTML += `<div style="aspect-ratio:1; display:flex; justify-content:center; align-items:center; background:#ffbc00; color:#000; font-weight:bold; font-size:10px; border-radius:3px;">${cellDisplay}</div>`;
                    } else {
                        winnersHTML += `<div style="aspect-ratio:1; display:flex; justify-content:center; align-items:center; background:#181c26; color:#555; font-weight:bold; font-size:10px; border-radius:3px;">${cellDisplay}</div>`;
                    }
                });
            }

            winnersHTML += `
                    </div>
                    <div style="background:#00b894; color:#fff; font-weight:bold; text-align:center; padding:6px; border-radius:6px; margin-top:6px; font-size:14px;">
                        +${pAmt} ETB
                    </div>
                </div>
            `;
        });

        winnersHTML += `
                </div>
                <button onclick="closeWinnerModalAndReset()" style="width:100%; background:#ff7675; color:#fff; border:none; padding:12px; font-size:15px; font-weight:bold; border-radius:8px; cursor:pointer; margin-top:10px;">
                    እሺ (ቀጥል)
                </button>
            </div>
        `;

        modalContentContainer.innerHTML = winnersHTML;
        winnerModalEl.hidden = false;
    }

    if (winnerAutoCloseTimer) clearTimeout(winnerAutoCloseTimer);
    winnerAutoCloseTimer = setTimeout(() => {
        closeWinnerModalAndReset();
    }, 6000);

    selectedBingoCards = [];
    temporarilySelectedCards = [];
    syncAndFetchUser();
}

function closeWinnerModalAndReset() {
    if (winnerAutoCloseTimer) clearTimeout(winnerAutoCloseTimer);
    const winnerModalEl = document.getElementById('winnerModal');
    if (winnerModalEl) winnerModalEl.hidden = true;
    showPage('bingoSelection');
    render1000BingoCards();
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

function hideAllViews() {
    if (homeView) homeView.hidden = true;
    if (profileView) profileView.hidden = true;
    if (bingoSelectionView) bingoSelectionView.hidden = true;
    if (bingoGameView) bingoGameView.hidden = true;
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
});
