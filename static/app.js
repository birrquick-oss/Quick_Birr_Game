/* =========================================================
   QUICK_BIRR GAMES - PART 1
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
let currentCardIndex = 0;

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
            clear75Board();
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
            clear75Board();
            currentCardIndex = 0;
            renderMyBoughtCards();
            updateRecentBallsUI();
        }

        if (data.type === "ball") {
            showPage("bingoLive");
            handleBallDraw(data);
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
   QUICK_BIRR GAMES - PART 2
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
                        <p style="margin:4px 0;">🎫 <b>ካርድ፦</b> <span style="color:#ffbc00; float:right; font-weight:bold;">#${cNum}</span></p>
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
                    <p style="margin:4px 0;">🎫 <b>ካርድ፦</b> <span style="color:#ffbc00; float:right; font-weight:bold;">#${cardNum}</span></p>
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

/* =========================================================
   QUICK_BIRR GAMES - PART 3
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
    render1000BingoCards();
    connectBingoWebSocket();
});
