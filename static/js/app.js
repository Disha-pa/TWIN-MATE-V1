const themeKey = document.body.dataset.themeKey || "theme_guest";

function toggleDarkMode() {
    document.body.classList.toggle("dark");
    localStorage.setItem(themeKey, document.body.classList.contains("dark") ? "dark" : "light");
}

window.addEventListener("DOMContentLoaded", () => {
    if (localStorage.getItem(themeKey) === "dark") {
        document.body.classList.add("dark");
    }

    // Remove old service workers — they were breaking login sessions.
    if ("serviceWorker" in navigator) {
        navigator.serviceWorker.getRegistrations().then((regs) => {
            regs.forEach((reg) => reg.unregister());
        });
    }

    const history = document.getElementById("chat-history");
    if (history) history.scrollTop = history.scrollHeight;
});
