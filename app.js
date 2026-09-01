/* =========================================================
   QUICK_BIRR GAMES
   Frontend Controller
   ========================================================= */

const tg = window.Telegram?.WebApp;


/* =========================
   TELEGRAM INIT
========================= */

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


/* =========================
   MODAL
========================= */

function showMessage(title, message, icon = "🎮") {

    modalTitle.textContent = title;
    modalMessage.textContent = message;
    modalIcon.textContent = icon;

    modal.hidden = false;
}

function closeMessage() {
    modal.hidden = true;
}

document
    .getElementById("modalClose")
    .addEventListener("click", closeMessage);

document
    .getElementById("modalButton")
    .addEventListener("click", closeMessage);

document
    .querySelector(".modal-overlay")
    .addEventListener("click", closeMessage);


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
   PLAY NOW
========================= */

document
    .getElementById("playNowButton")
    .addEventListener("click", () => {

        document
            .querySelector(".games-section")
            .scrollIntoView({
                behavior: "smooth"
            });

    });


/* =========================
   DEPOSIT
========================= */

document
    .getElementById("depositButton")
    .addEventListener("click", () => {

        showMessage(
            "Deposit",
            "Deposit system will be connected to the backend soon.",
            "💰"
        );

    });


/* =========================
   WITHDRAW
========================= */

document
    .getElementById("withdrawButton")
    .addEventListener("click", () => {

        showMessage(
            "Withdraw",
            "Withdrawal system will be connected to the backend soon.",
            "💸"
        );

    });


/* =========================
   BALANCE
========================= */

document
    .getElementById("balanceButton")
    .addEventListener("click", () => {

        showMessage(
            "Wallet",
            "Your wallet will be connected to the new QUICK_BIRR backend.",
            "💰"
        );

    });


/* =========================
   BOTTOM NAV
========================= */

document.querySelectorAll(".nav-item").forEach(item => {

    item.addEventListener("click", () => {

        document
            .querySelectorAll(".nav-item")
            .forEach(nav => {
                nav.classList.remove("active");
            });

        item.classList.add("active");

        const page = item.dataset.page;

        if (page === "home") {

            window.scrollTo({
                top: 0,
                behavior: "smooth"
            });

        }

        if (page === "games") {

            document
                .querySelector(".games-section")
                .scrollIntoView({
                    behavior: "smooth"
                });

        }

        if (page === "promo") {

            document
                .querySelector(".promo-card")
                .scrollIntoView({
                    behavior: "smooth"
                });

        }

        if (page === "profile") {

            showMessage(
                "Profile",
                "Your Telegram profile and account settings will appear here.",
                "👤"
            );

        }

    });

});


/* =========================
   INITIAL USER
========================= */

function loadTelegramUser() {

    if (!tg?.initDataUnsafe?.user) {
        return;
    }

    const user = tg.initDataUnsafe.user;

    console.log("Telegram user:", user);

    /*
       Backend authentication will be added later.

       IMPORTANT:
       Do not trust initDataUnsafe alone for wallet
       or balance operations.
    */
}

loadTelegramUser();


/* =========================
   INITIAL STATE
========================= */

document.getElementById("balance").textContent =
    "0.00 ETB";

document.getElementById("playerCount").textContent =
    "0";
