/* =========================================================
QUICK_BIRR GAMES - PART 3 / 3 (PART A)
========================================================= */

// 1. Auto-mark process for all purchased cards
function autoMarkAllBoughtCards() {
  if (!Array.isArray(selectedBingoCards) || selectedBingoCards.length === 0) return;
  if (!Array.isArray(recentBallsList)) return;

  const drawnNumbers = recentBallsList.map(b => b.num);

  selectedBingoCards.forEach(cardNum => {
    if (!markedCellsMap[cardNum]) {
      markedCellsMap[cardNum] = new Set();
    }
    drawnNumbers.forEach(num => markedCellsMap[cardNum].add(num));
  });
}

// 2. Render active bought card UI
async function renderMyBoughtCards() {
  const container = document.getElementById("playerBingoCard");
  if (!container) return;

  container.innerHTML = "";

  // Check if player has purchased cards
  if (!Array.isArray(selectedBingoCards) || selectedBingoCards.length === 0) {
    container.innerHTML = `
      <div style="color:white; text-align:center; padding:20px;">
        በዚህ ዙር ምንም ካርቴላ አልገዙም!
      </div>`;
    return;
  }

  // Bound index safety
  if (currentCardIndex < 0) currentCardIndex = 0;
  if (currentCardIndex >= selectedBingoCards.length) currentCardIndex = selectedBingoCards.length - 1;

  const activeCardNum = selectedBingoCards[currentCardIndex];
  if (!markedCellsMap[activeCardNum]) {
    markedCellsMap[activeCardNum] = new Set();
  }

  // Auto-mark logic for current card if mode is active
  if (typeof isAutoMark !== "undefined" && isAutoMark && Array.isArray(recentBallsList)) {
    recentBallsList.forEach(b => markedCellsMap[activeCardNum].add(b.num));
  }

  try {
    const res = await fetch(`/api/cards/get_matrix?card_number=${activeCardNum}`);
    if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);

    const data = await res.json();
    const matrix = data.matrix;

    if (!matrix || !Array.isArray(matrix)) {
      throw new Error("Invalid card matrix data received");
    }

    const mainSliderLayout = document.createElement("div");
    mainSliderLayout.className = "main-slider-layout";
    mainSliderLayout.style.cssText = "display: flex; align-items: center; justify-content: space-between; width: 100%; gap: 10px;";

    let html = `
      <button class="side-nav-btn" onclick="moveSlider(-1)" style="background:#1e272e; color:#00ffcc; border:1px solid #00ffcc; padding:10px; border-radius:8px; font-weight:bold; cursor:pointer;">◀</button>
      
      <div class="card-display-center" style="flex-grow:1;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <div class="card-title-label" style="color: #ffd700; font-weight: bold; font-size: 14px;">
            ካርድ #${activeCardNum} (${currentCardIndex + 1}/${selectedBingoCards.length})
          </div>
          <button id="toggleMarkBtn" onclick="toggleMarkingMode()" style="background: ${isAutoMark ? '#2ed573' : '#718093'}; color: white; border: none; padding: 4px 8px; font-size: 11px; font-weight: bold; border-radius: 4px; cursor:pointer;">
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
          html += `
            <div class="bingo-cell free-star" style="background:#ffbc00; color:#000; display:flex; justify-content:center; align-items:center; aspect-ratio:1; border-radius:6px; font-weight:bold;">★</div>`;
        } else {
          const isMarkedInState = markedCellsMap[activeCardNum].has(cell);
          const isAlreadyDrawn = Array.isArray(recentBallsList) && recentBallsList.some(b => b.num === cell);

          if (isMarkedInState || (isAlreadyDrawn && isAutoMark)) {
            const letterPrefix = cell <= 15 ? 'B' : cell <= 30 ? 'I' : cell <= 45 ? 'N' : cell <= 60 ? 'G' : 'O';
            const savedColor = getBingoColor(letterPrefix);
            markedCellsMap[activeCardNum].add(cell);

            html += `
              <div class="bingo-cell cell-${cell} marked-auto" style="background:${savedColor} !important; color:#fff; display:flex; justify-content:center; align-items:center; aspect-ratio:1; border-radius:6px; font-weight:bold; cursor:pointer;" onclick="handleManualCellClick(this, ${cell}, ${activeCardNum})">
                ${cell}
              </div>`;
          } else {
            html += `
              <div class="bingo-cell cell-${cell}" style="background:#252634; color:#fff; display:flex; justify-content:center; align-items:center; aspect-ratio:1; border-radius:6px; font-weight:bold; cursor:pointer;" onclick="handleManualCellClick(this, ${cell}, ${activeCardNum})">
                ${cell}
              </div>`;
          }
        }
      });
    });

    html += `
        </div>
      </div>
      
      <button class="side-nav-btn" onclick="moveSlider(1)" style="background:#1e272e; color:#00ffcc; border:1px solid #00ffcc; padding:10px; border-radius:8px; font-weight:bold; cursor:pointer;">▶</button>
    `;

    mainSliderLayout.innerHTML = html;
    container.appendChild(mainSliderLayout);

  } catch (e) {
    console.error("Matrix load error:", e);
    container.innerHTML = `
      <div style="color:#ff4757; text-align:center; padding:20px; font-weight:bold;">
        ⚠️ ካርቴላውን መጫን አልተቻለም! እባክዎ ገጹን ያድሱ።
      </div>`;
  }
}

// 3. Carousel navigation controls
function moveSlider(direction) {
  if (!Array.isArray(selectedBingoCards) || selectedBingoCards.length <= 1) return;

  currentCardIndex += direction;
  if (currentCardIndex < 0) {
    currentCardIndex = selectedBingoCards.length - 1;
  } else if (currentCardIndex >= selectedBingoCards.length) {
    currentCardIndex = 0;
  }

  renderMyBoughtCards();
}

// 4. Toggle marking mode (Auto vs Manual)
function toggleMarkingMode() {
  isAutoMark = !isAutoMark;
  if (isAutoMark) {
    autoMarkAllBoughtCards();
  }
  renderMyBoughtCards();
}

// 5. Handle manual cell click by player
function handleManualCellClick(cellElement, cellNumber, activeCardNum) {
  if (!activeCardNum && Array.isArray(selectedBingoCards)) {
    activeCardNum = selectedBingoCards[currentCardIndex];
  }

  if (!markedCellsMap[activeCardNum]) {
    markedCellsMap[activeCardNum] = new Set();
  }

  const isBallDrawn = Array.isArray(recentBallsList) && recentBallsList.some(b => b.num === cellNumber);

  if (isBallDrawn) {
    markedCellsMap[activeCardNum].add(cellNumber);
    const letterPrefix = cellNumber <= 15 ? 'B' : cellNumber <= 30 ? 'I' : cellNumber <= 45 ? 'N' : cellNumber <= 60 ? 'G' : 'O';
    const ballColor = getBingoColor(letterPrefix);
    
    cellElement.style.background = ballColor;
    cellElement.style.color = "#fff";
  } else {
    // Flash red animation if cell was not drawn
    const originalBg = cellElement.style.background;
    cellElement.style.background = "#ff4757";
    setTimeout(() => {
      cellElement.style.background = originalBg || "#252634";
    }, 250);
  }
}

// 6. Claim Bingo button action handler
document.getElementById("claimBingoBtn")?.addEventListener("click", () => {
  if (typeof bingoSocket === "undefined" || !bingoSocket || bingoSocket.readyState !== WebSocket.OPEN) {
    showToastMessage("⚠️ WebSocket አልተገናኘም!", "error");
    return;
  }

  if (!Array.isArray(selectedBingoCards) || selectedBingoCards.length === 0) {
    showToastMessage("⚠️ ምንም የተገዛ ካርቴላ የለም!", "error");
    return;
  }

  const currentCard = selectedBingoCards[currentCardIndex];
  const telegramId = (typeof userData !== "undefined" && userData?.telegram_id) ? String(userData.telegram_id) : "";

  bingoSocket.send(JSON.stringify({
    type: "claim_bingo",
    telegram_id: telegramId,
    card_number: currentCard,
    game_id: typeof currentGameId !== "undefined" ? currentGameId : null
  }));

  showToastMessage("🔥 የ BINGO ጥያቄ ተልኳል! በመፈተሽ ላይ...", "success");
});

/* =========================================================
   QUICK_BIRR GAMES - PART 3 / 3 (PART B)
   ========================================================= */

let winnerAutoCloseTimer = null;

function handleGameOver(data) {
    if (typeof soundEnabled !== "undefined" && soundEnabled && typeof playWinSound === "function") {
        playWinSound();
    }

    const winnersList = data?.winners || [];
    const titleText = winnersList.length > 1 ? `🎉 ${winnersList.length} አሸናፊዎች! 🎉` : "🎉 BINGO! 🎉";
    const messageText = data?.message || "ጨዋታው ተጠናቋል!";

    let allWinnersHtml = "";

    const renderCardGrid = (cardMatrixNumbers = [], winningNumbers = []) => {
        if (!Array.isArray(cardMatrixNumbers) || cardMatrixNumbers.length !== 25) return "";

        let gridHtml = `<div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; margin: 15px auto; max-width: 250px; background: #111; padding: 10px; border-radius: 10px;">`;
        cardMatrixNumbers.forEach((num) => {
            const isWinningNum = winningNumbers.includes(num);
            const isFreeSpace = num === 0 || num === "★" || num === "FREE";
            const displayNum = isFreeSpace ? "★" : num;

            let cellStyle = `aspect-ratio: 1; display: flex; justify-content: center; align-items: center; font-weight: bold; font-size: 14px; border-radius: 6px; transition: all 0.3s;`;
            if (isWinningNum || isFreeSpace) {
                cellStyle += `background: #ffbc00; color: black; box-shadow: 0 0 12px #ffbc00; border: 1px solid #fff; transform: scale(1.05);`;
            } else {
                cellStyle += `background: #252634; color: #666; border: 1px solid #333;`;
            }
            gridHtml += `<div style="${cellStyle}">${displayNum}</div>`;
        });
        gridHtml += `</div>`;
        return gridHtml;
    };

    if (winnersList.length > 0) {
        winnersList.forEach((winner) => {
            const wName = winner.telegram_name || `User_${winner.winner_id || winner.telegram_id || 'Unknown'}`;
            const phoneNum = winner.phone_number || "ስልክ አልተመዘገበም";
            const cNum = winner.card_number || "N/A";
            const pAmt = winner.prize || 0;
            const gridHtml = renderCardGrid(winner.card_numbers, winner.winning_numbers);

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
        const winnerName = data?.telegram_name || data?.winner_name || "ተጫዋች";
        const phoneNum = data?.phone_number || "ስልክ አልተመዘገበም";
        const cardNum = data?.card_number || "N/A";
        const prize = data?.prize || 0;
        const gridHtml = renderCardGrid(data?.card_numbers, data?.winning_numbers);

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

                <button onclick="closeWinnerModalAndReset()" style="background:#ffbc00; color:black; border:none; padding:14px; font-size:16px; font-weight:bold; border-radius:10px; width:100%; cursor:pointer; flex-shrink: 0;">እሺ (ቀጥል)</button>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    if (winnerAutoCloseTimer) clearTimeout(winnerAutoCloseTimer);
    winnerAutoCloseTimer = setTimeout(() => {
        closeWinnerModalAndReset();
    }, 5000);

    if (typeof selectedBingoCards !== "undefined") selectedBingoCards = [];
    if (typeof temporarilySelectedCards !== "undefined") temporarilySelectedCards = [];
    syncAndFetchUser();
}

function closeWinnerModalAndReset() {
    if (winnerAutoCloseTimer) clearTimeout(winnerAutoCloseTimer);
    const winnerModalEl = document.getElementById('winnerModal');
    if (winnerModalEl) winnerModalEl.remove();
    
    showPage('bingoSelection');
    if (typeof render1000BingoCards === "function") {
        render1000BingoCards();
    }
}

async function syncAndFetchUser() {
    if (typeof userData === "undefined" || !userData.telegram_id || userData.telegram_id === "12345678") return;

    try {
        const userRes = await fetch('/api/users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_id: String(userData.telegram_id),
                telegram_username: userData.username || "",
                first_name: userData.first_name || ""
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
    const balanceEl = document.getElementById("balanceEl");
    const dashBalanceEl = document.getElementById("dashBalanceEl");

    if (balanceEl) balanceEl.textContent = formatted;
    if (dashBalanceEl) dashBalanceEl.textContent = formatted;
}

document.getElementById("balanceButton")?.addEventListener("click", syncAndFetchUser);

function setupFormSubmitListeners() {
    const depositForm = document.getElementById("deposit-form") || document.querySelector("#depositModal form");
    if (depositForm) {
        depositForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            const bankName = document.getElementById("deposit-bank")?.value || "CBE";
            const amount = parseFloat(document.getElementById("deposit-amount")?.value);
            const smsData = document.getElementById("deposit-sms")?.value;

            if (!amount || amount < 50 || !smsData) {
                if (typeof showMessage === "function") showMessage("የተሳሳተ መረጃ", "እባክዎን አነስተኛውን 50 ETB እና የባንክ SMS መረጃውን በትክክል ይሙሉ!", "⚠️");
                return;
            }

            const activeTgUser = window.Telegram?.WebApp?.initDataUnsafe?.user;
            const finalTgId = activeTgUser?.id ? String(activeTgUser.id) : String(userData?.telegram_id || "");
            const finalTgName = activeTgUser?.first_name || userData?.first_name || "ተጫዋች";

            if (!finalTgId || finalTgId === "12345678" || finalTgId === "null" || finalTgId === "undefined") {
                if (typeof showMessage === "function") showMessage("የቴሌግራም ችግር", "እባክዎን አፕሊኬሽኑን በቴሌግራም ቦት በኩል 'Play Now' በማለት እንደገና ይክፈቱት!", "⚠️");
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
                    if (typeof closeModals === "function") closeModals();
                    depositForm.reset();
                    if (typeof showMessage === "function") showMessage("ተልኳል!", data.message || "የዲፖዚት ጥያቄዎ ለአድሚን ደርሷል!", "✅");
                } else {
                    if (typeof showMessage === "function") showMessage("ስህተት", data.message || "ጥያቄውን ማስተናገድ አልተቻለም", "❌");
                }
            } catch (err) {
                console.error("Deposit Error:", err);
                if (typeof showMessage === "function") showMessage("ስህተት", "የዲፖዚት ጥያቄ መላክ አልተቻለም!", "❌");
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

            if (!amount || amount < 100 || !accountNumber) {
                if (typeof showMessage === "function") showMessage("የተሳሳተ መረጃ", "እባክዎን አነስተኛውን 100 ETB እና የባንክ አካውንት ቁጥር በትክክል ይሙሉ!", "⚠️");
                return;
            }

            const activeTgUser = window.Telegram?.WebApp?.initDataUnsafe?.user;
            const finalTgId = activeTgUser?.id ? String(activeTgUser.id) : String(userData?.telegram_id || "");

            if (!finalTgId || finalTgId === "12345678" || finalTgId === "null" || finalTgId === "undefined") {
                if (typeof showMessage === "function") showMessage("የቴሌግራም ችግር", "እባክዎን አፕሊኬሽኑን በቴሌግራም ቦት በኩል እንደገና ይክፈቱት!", "⚠️");
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
                    if (typeof closeModals === "function") closeModals();
                    withdrawForm.reset();
                    if (typeof showMessage === "function") showMessage("ተመዝግቧል!", data.message || "የማውጫ ጥያቄዎ ተመዝግቧል!", "✅");
                    syncAndFetchUser();
                } else {
                    if (typeof showMessage === "function") showMessage("ስህተት", data.message || "ጥያቄውን ማስተናገድ አልተቻለም", "❌");
                }
            } catch (err) {
                console.error("Withdraw Error:", err);
                if (typeof showMessage === "function") showMessage("ስህተት", "የማውጫ ጥያቄ መላክ አልተቻለም!", "❌");
            }
        });
    }
}

function hideAllViews() {
    const homeView = document.getElementById("homeView");
    const profileView = document.getElementById("profileView");
    const bingoSelectionView = document.getElementById("bingoSelectionView");
    const bingoGameView = document.getElementById("bingoGameView");

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

    const homeView = document.getElementById("homeView");
    const profileView = document.getElementById("profileView");
    const bingoSelectionView = document.getElementById("bingoSelectionView");
    const bingoGameView = document.getElementById("bingoGameView");

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

    if (typeof userData === "undefined") window.userData = {};

    if (tgUser && tgUser.id) {
        userData.telegram_id = String(tgUser.id);
        userData.first_name = tgUser.first_name || "User";
        userData.last_name = tgUser.last_name || "";
        userData.username = tgUser.username ? `@${tgUser.username}` : "";

        const fullName = `${userData.first_name} ${userData.last_name}`.trim();

        const profileNameEl = document.getElementById("profileNameEl");
        const profilePhoneEl = document.getElementById("profilePhoneEl");

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
