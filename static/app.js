/* =========================================================
   QUICK_BIRR GAMES - APP.JS (PART 1 OF 2)
   ========================================================= */

let userData = {
    telegram_id: null,
    first_name: "",
    last_name: "",
    username: "",
    db_user_id: null,
    balance: "0.00"
};

let selectedBingoCards = [];
let temporarilySelectedCards = [];
let markedCellsMap = {}; 
let recentBallsList = [];
let isAutoMark = true;
let currentCardIndex = 0;
let currentGameId = null;
let bingoSocket = null;
let isSoundOn = true;

// Page Navigation Manager
function showPage(pageName) {
    const pages = {
        'home': document.getElementById('homeView'),
        'bingoSelection': document.getElementById('bingoSelectionView'),
        'bingoLive': document.getElementById('bingoGameView'),
        'profile': document.getElementById('profileView')
    };

    Object.keys(pages).forEach(key => {
        if (pages[key]) pages[key].hidden = true;
    });

    if (pages[pageName]) pages[pageName].hidden = false;
    window.scrollTo({ top: 0, behavior: "smooth" });
}

// Notifications
function showToastMessage(msg, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast-msg toast-${type}`;
    toast.textContent = msg;
    toast.style.cssText = `
        position: fixed; bottom: 80px; left: 50%; transform: translateX(-50%);
        background: ${type === 'error' ? '#ff4757' : type === 'success' ? '#2ed573' : '#ffbc00'};
        color: #fff; padding: 10px 20px; border-radius: 20px; font-weight: bold;
        z-index: 99999; box-shadow: 0 4px 10px rgba(0,0,0,0.3); font-size: 13px;
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function showMessage(title, text, icon = "ℹ️") {
    const oldModal = document.getElementById("customAlertModal");
    if (oldModal) oldModal.remove();

    const modalHtml = `
        <div id="customAlertModal" style="position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.8); display:flex; justify-content:center; align-items:center; z-index:99999; color:white;">
            <div style="background:#1e1e2e; padding:20px; border-radius:16px; text-align:center; width:280px; border:1px solid #ffbc00;">
                <div style="font-size:35px; margin-bottom:10px;">${icon}</div>
                <h3 style="color:#ffbc00; margin:0 0 10px 0;">${title}</h3>
                <p style="font-size:13px; color:#ccc; margin-bottom:20px;">${text}</p>
                <button onclick="document.getElementById('customAlertModal').remove()" style="background:#ffbc00; color:#000; border:none; padding:10px 20px; font-weight:bold; border-radius:8px; cursor:pointer; width:100%;">እሺ</button>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML("beforeend", modalHtml);
}

function getBingoColor(letter) {
    switch (letter) {
        case 'B': return '#ff4757';
        case 'I': return '#ffa502';
        case 'N': return '#2ed573';
        case 'G': return '#1e90ff';
        case 'O': return '#3742fa';
        default: return '#ffbc00';
    }
}

function render1000BingoCards() {
    const gridContainer = document.getElementById("cardsGrid");
    if (!gridContainer) return;
    
    gridContainer.innerHTML = "";
    const fragment = document.createDocumentFragment();

    for (let i = 1; i <= 1000; i++) {
        const cardBtn = document.createElement("button");
        cardBtn.type = "button";
        cardBtn.className = "card-select-btn";
        cardBtn.id = `card-btn-${i}`;
        cardBtn.textContent = `#${i}`;
        
        if (temporarilySelectedCards.includes(i) || selectedBingoCards.includes(i)) {
            cardBtn.classList.add("selected");
        }

        cardBtn.onclick = () => toggleCardSelection(i, cardBtn);
        fragment.appendChild(cardBtn);
    }
    
    gridContainer.appendChild(fragment);
    updateSelectedCountUI();
}

function toggleCardSelection(cardNum, element) {
    const index = temporarilySelectedCards.indexOf(cardNum);
    if (index > -1) {
        temporarilySelectedCards.splice(index, 1);
        element.classList.remove("selected");
    } else {
        if (temporarilySelectedCards.length >= 10) {
            showToastMessage("በአንድ ዙር ከ10 ካርቴላ በላይ መግዛት አይችሉም!", "error");
            return;
        }
        temporarilySelectedCards.push(cardNum);
        element.classList.add("selected");
    }
    updateSelectedCountUI();
}

function updateSelectedCountUI() {
    const countEl = document.getElementById("mySelectedCount");
    if (countEl) countEl.textContent = temporarilySelectedCards.length;
}

// Purchase & WebSocket Engine
async function confirmCardPurchase() {
    if (temporarilySelectedCards.length === 0) {
        showToastMessage("እባክዎን ቢያንስ አንድ ካርቴላ ይምረጡ!", "error");
        return;
    }

    const tgUser = window.Telegram?.WebApp?.initDataUnsafe?.user;
    const finalTgId = tgUser?.id ? String(tgUser.id) : String(userData.telegram_id || "");

    if (!finalTgId) {
        showToastMessage("እባክዎን አፑን በቴሌግራም ቦት በኩል ይክፈቱት!", "error");
        return;
    }

    try {
        const response = await fetch("/api/cards/buy", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                telegram_id: finalTgId,
                cards: temporarilySelectedCards,
                game_id: currentGameId
            })
        });

        const resData = await response.json();

        if (resData.success) {
            selectedBingoCards = [...selectedBingoCards, ...temporarilySelectedCards];
            temporarilySelectedCards = [];
            showToastMessage("ካርቴላ በትክክል ተገዝቷል!", "success");
            showPage('bingoLive');
            renderMyBoughtCards();
        } else {
            showToastMessage(`ስህተት፦ ${resData.message || "መግዛት አልተቻለም"}`, "error");
        }
    } catch (err) {
        showToastMessage("የካርቴላ ግዢ ላይ ስህተት ተፈጥሯል!", "error");
    }
}

function initBingoWebSocket() {
    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/bingo`;

    bingoSocket = new WebSocket(wsUrl);
    bingoSocket.onopen = () => console.log("Bingo WS Connected.");
    bingoSocket.onmessage = (event) => {
        try {
            handleWebSocketMessage(JSON.parse(event.data));
        } catch (e) {
            console.error("WS Parse Error:", e);
        }
    };
    bingoSocket.onclose = () => setTimeout(initBingoWebSocket, 3000);
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case "game_state":
            currentGameId = data.game_id;
            const phase1Id = document.getElementById("phase1GameId");
            const gameIdBadge = document.getElementById("gameIdBadge");
            if (phase1Id) phase1Id.textContent = `#${data.game_id}`;
            if (gameIdBadge) gameIdBadge.textContent = `Game #${data.game_id}`;
            const timerEl = document.getElementById("selectionTimer");
            if (timerEl) timerEl.textContent = data.time_remaining;
            break;

        case "ball_drawn":
            if (data.ball) {
                recentBallsList.unshift(data.ball);
                updateCurrentBallUI(data.ball);
                renderRecentBallsUI();
                if (isAutoMark) autoMarkAllBoughtCards();
                renderMyBoughtCards();
            }
            break;

        case "game_over":
            handleGameOver(data);
            break;
    }
}

function updateCurrentBallUI(ball) {
    const letterEl = document.getElementById("currentBallLetter");
    const numberEl = document.getElementById("currentBallNumber");
    let letter = ball.num <= 15 ? 'B' : ball.num <= 30 ? 'I' : ball.num <= 45 ? 'N' : ball.num <= 60 ? 'G' : 'O';

    if (letterEl) letterEl.textContent = letter;
    if (numberEl) numberEl.textContent = ball.num;
}

function renderRecentBallsUI() {
    const container = document.getElementById("recentBallsList");
    if (!container) return;
    container.innerHTML = "";

    recentBallsList.slice(0, 5).forEach((ball) => {
        const ballItem = document.createElement("div");
        ballItem.className = "recent-ball-item";
        let letter = ball.num <= 15 ? 'B' : ball.num <= 30 ? 'I' : ball.num <= 45 ? 'N' : ball.num <= 60 ? 'G' : 'O';
        ballItem.style.backgroundColor = getBingoColor(letter);
        ballItem.style.color = "#fff";
        ballItem.style.padding = "4px 8px";
        ballItem.style.borderRadius = "4px";
        ballItem.style.fontWeight = "bold";
        ballItem.textContent = `${letter}-${ball.num}`;
        container.appendChild(ballItem);
    });
}

/* =========================================================
   QUICK_BIRR GAMES - APP.JS (PART 2 OF 2)
   ========================================================= */

function autoMarkAllBoughtCards() {
    if (!selectedBingoCards || selectedBingoCards.length === 0) return;
    const drawnNumbers = recentBallsList.map(b => b.num);

    selectedBingoCards.forEach(cardNum => {
        if (!markedCellsMap[cardNum]) markedCellsMap[cardNum] = new Set();
        drawnNumbers.forEach(num => markedCellsMap[cardNum].add(num));
    });
}

async function renderMyBoughtCards() {
    const container = document.getElementById("playerBingoCard");
    if (!container) return;
    container.innerHTML = "";

    if (selectedBingoCards.length === 0) {
        container.innerHTML = "<div style='color:#a0a0a0; text-align:center; padding:20px; font-weight:bold;'>በዚህ ዙር ምንም ካርቴላ አልገዙም!</div>";
        return;
    }
    
    const activeCardNum = selectedBingoCards[currentCardIndex];
    if (!markedCellsMap[activeCardNum]) markedCellsMap[activeCardNum] = new Set();

    if (isAutoMark) {
        recentBallsList.forEach(b => markedCellsMap[activeCardNum].add(b.num));
    }

    try {
        const res = await fetch(`/api/cards/get_matrix?card_number=${activeCardNum}`);
        const data = await res.json();
        const matrix = data.matrix;

        const mainSliderLayout = document.createElement("div");
        mainSliderLayout.className = "main-slider-layout";
        mainSliderLayout.style.cssText = "display: flex; align-items: center; justify-content: space-between; width: 100%; gap: 10px;";

        let html = `
            <button class="side-nav-btn" type="button" onclick="moveSlider(-1)" style="background:#1e272e; color:#00ffcc; border:1px solid #00ffcc; padding:10px; border-radius:8px; font-weight:bold; cursor:pointer;">◀</button>
            <div class="card-display-center" style="flex-grow:1;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div class="card-title-label" style="color: #ffd700; font-weight: bold; font-size: 14px;">
                        ካርድ #${activeCardNum} (${currentCardIndex + 1}/${selectedBingoCards.length})
                    </div>
                    <button id="toggleMarkBtn" type="button" onclick="toggleMarkingMode()" style="background: ${isAutoMark ? '#2ed573' : '#718093'}; color: white; border: none; padding: 4px 8px; font-size: 11px; font-weight: bold; border-radius: 4px; cursor:pointer;">
                        ${isAutoMark ? "🤖 Auto: ON" : "🖐 Manual"}
                    </button>
                </div>
                <div class="bingo-header-letters" style="display:grid; grid-template-columns: repeat(5, 1fr); gap: 4px; text-align:center; font-weight:bold; margin-bottom: 5px;">
                    <span style="background:${getBingoColor('B')}; border-radius:4px; color:#fff;">B</span>
                    <span style="background:${getBingoColor('I')}; border-radius:4px; color:#fff;">I</span>
                    <span style="background:${getBingoColor('N')}; border-radius:4px; color:#fff;">N</span>
                    <span style="background:${getBingoColor('G')}; border-radius:4px; color:#fff;">G</span>
                    <span style="background:${getBingoColor('O')}; border-radius:4px; color:#fff;">O</span>
                </div>
                <div class="bingo-card-grid-5x5" style="display:grid; grid-template-columns: repeat(5, 1fr); gap:6px;">
        `;

        matrix.forEach(row => {
            row.forEach(cell => {
                if (cell === "FREE" || cell === 0) {
                    html += `<div class="bingo-cell free-star" style="background:#ffbc00; color:#000; display:flex; justify-content:center; align-items:center; aspect-ratio:1; border-radius:6px; font-weight:bold;">★</div>`;
                } else {
                    const isMarkedInState = markedCellsMap[activeCardNum].has(cell);
                    const isAlreadyDrawn = recentBallsList.some(b => b.num === cell);

                    if (isMarkedInState || (isAlreadyDrawn && isAutoMark)) {
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
        
        html += `</div></div><button class="side-nav-btn" type="button" onclick="moveSlider(1)" style="background:#1e272e; color:#00ffcc; border:1px solid #00ffcc; padding:10px; border-radius:8px; font-weight:bold; cursor:pointer;">▶</button>`;
        mainSliderLayout.innerHTML = html;
        container.appendChild(mainSliderLayout);
    } catch (e) {
        console.error("Matrix load error:", e);
    }
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
    if (isAutoMark) autoMarkAllBoughtCards();
    renderMyBoughtCards(); 
}

function handleManualCellClick(cellElement, cellNumber, activeCardNum) {
    if (!activeCardNum) activeCardNum = selectedBingoCards[currentCardIndex];
    if (!markedCellsMap[activeCardNum]) markedCellsMap[activeCardNum] = new Set();

    const isBallDrawn = recentBallsList.some(b => b.num === cellNumber);

    if (isBallDrawn) {
        markedCellsMap[activeCardNum].add(cellNumber);
        let letterPrefix = cellNumber <= 15 ? 'B' : cellNumber <= 30 ? 'I' : cellNumber <= 45 ? 'N' : cellNumber <= 60 ? 'G' : 'O';
        cellElement.style.background = getBingoColor(letterPrefix);
        cellElement.style.color = "#fff";
    } else {
        const oldBg = cellElement.style.background;
        cellElement.style.background = "#ff4757";
        setTimeout(() => { cellElement.style.background = oldBg; }, 250);
    }
}

function handleGameOver(data) {
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

            allWinnersHtml += `
                <div style="background:#161622; padding:15px; border-radius:15px; margin-bottom: 15px; border: 1px solid #2a2b3d; text-align: left;">
                    <div style="font-size:14px;">
                        <p style="margin:4px 0;">👤 <b>ስም፦</b> <span style="color:#00ffcc; float:right;">${wName}</span></p>
                        <p style="margin:4px 0;">📞 <b>ስልክ፦</b> <span style="color:#3aafaa; float:right;">${phoneNum}</span></p>
                        <p style="margin:4px 0;">🎫 <b>ካርድ፦</b> <span style="color:#ffbc00; float:right;">#${cNum}</span></p>
                    </div>
                    <div style="background: rgba(0,255,0,0.1); border: 1px dashed #00ff00; padding: 8px; border-radius: 8px; text-align: center; margin-top: 10px;">
                        <span style="font-size:20px; color:#00ff00; font-weight:bold;">+${pAmt} ETB</span>
                    </div>
                </div>
            `;
        });
    }

    const oldModal = document.getElementById('winnerModal');
    if (oldModal) oldModal.remove();

    const modalHtml = `
        <div id="winnerModal" style="position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); display:flex; justify-content:center; align-items:center; z-index:9999; color:white;">
            <div style="background:#1e1e2e; padding:20px; border-radius:16px; text-align:center; width:320px; border:2px solid #ffbc00;">
                <h2 style="color:#ffbc00; margin-top:0;">${titleText}</h2>
                <p style="font-size:13px; color:#aaa;">${messageText}</p>
                <div>${allWinnersHtml}</div>
                <button onclick="document.getElementById('winnerModal').remove(); showPage('bingoSelection'); render1000BingoCards();" style="background:#ffbc00; color:black; border:none; padding:12px; font-weight:bold; border-radius:8px; width:100%; cursor:pointer;">እሺ (ቀጥል)</button>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    selectedBingoCards = [];
    temporarilySelectedCards = [];
    syncAndFetchUser();
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
    const formatted = `${amount} ETB`;
    const topBalanceEl = document.getElementById("balance");
    const dashBalanceEl = document.getElementById("dashBalance");

    if (topBalanceEl) topBalanceEl.textContent = formatted;
    if (dashBalanceEl) dashBalanceEl.textContent = formatted;
}

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

            try {
                const res = await fetch("/api/users/deposit", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        telegram_id: finalTgId,
                        telegram_name: finalTgName,
                        amount: amount,
                        bank_name: bankName,
                        sms_data: smsData
                    })
                });
                const data = await res.json();

                if (data.success) {
                    if (typeof closeModals === "function") closeModals();
                    depositForm.reset();
                    showMessage("ተልኳል!", data.message || "የዲፖዚት ጥያቄዎ ለአድሚን ደርሷል!", "✅");
                } else {
                    showMessage("ስህተት", data.message || "ጥያቄውን ማስተናገድ አልተቻለም", "❌");
                }
            } catch (err) {
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

            try {
                const res = await fetch("/api/users/withdraw", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        telegram_id: finalTgId,
                        amount: amount,
                        bank_name: bankName,
                        account_number: accountNumber
                    })
                });
                const data = await res.json();

                if (data.success) {
                    if (typeof closeModals === "function") closeModals();
                    withdrawForm.reset();
                    showMessage("ተመዝግቧል!", data.message || "የማውጫ ጥያቄዎ ተመዝግቧል!", "✅");
                    syncAndFetchUser();
                } else {
                    showMessage("ስህተት", data.message || "ጥያቄውን ማስተናገድ አልተቻለም", "❌");
                }
            } catch (err) {
                showMessage("ስህተት", "የማውጫ ጥያቄ መላክ አልተቻለም!", "❌");
            }
        });
    }
}

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

        const profileNameEl = document.getElementById("profileName");
        const profilePhoneEl = document.getElementById("profilePhone");

        if (profileNameEl) profileNameEl.textContent = fullName;
        if (profilePhoneEl) profilePhoneEl.textContent = userData.username || `ID: ${userData.telegram_id}`;

        syncAndFetchUser();
    }
}

document.addEventListener("DOMContentLoaded", () => {
    loadTelegramUser();
    setupFormSubmitListeners();
    initBingoWebSocket();
    updateBalanceUI("0.00");

    const confirmBtn = document.getElementById("confirmCardsBtn");
    if (confirmBtn) {
        confirmBtn.addEventListener("click", confirmCardPurchase);
    }

    const claimBtn = document.getElementById("claimBingoBtn");
    if (claimBtn) {
        claimBtn.addEventListener("click", () => {
            if (!bingoSocket || bingoSocket.readyState !== WebSocket.OPEN) {
                showToastMessage("WebSocket አልተገናኘም!", "error");
                return;
            }

            if (selectedBingoCards.length === 0) {
                showToastMessage("ምንም የተገዛ ካርቴላ የለም!", "error");
                return;
            }

            const currentCard = selectedBingoCards[currentCardIndex];
            bingoSocket.send(JSON.stringify({
                type: "claim_bingo",
                telegram_id: String(userData.telegram_id),
                card_number: currentCard,
                game_id: currentGameId
            }));

            showToastMessage("🔥 የ BINGO ጥያቄ ተልኳል! በመፈተሽ ላይ...", "success");
        });
    }

    const balanceBtn = document.getElementById("balanceButton");
    if (balanceBtn) {
        balanceBtn.addEventListener("click", syncAndFetchUser);
    }

    document.querySelectorAll(".bottom-nav .nav-item").forEach(item => {
        item.addEventListener("click", () => {
            const page = item.dataset.page;
            
            document.querySelectorAll(".bottom-nav .nav-item").forEach(n => n.classList.remove("active"));
            item.classList.add("active");

            if (page === "home") {
                showPage("home");
            } else if (page === "games") {
                showPage("home");
                document.querySelector(".games-section")?.scrollIntoView({ behavior: "smooth" });
            } else if (page === "profile") {
                showPage("profile");
            }
        });
    });
});
