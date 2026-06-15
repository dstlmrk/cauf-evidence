// Color mode (light / dark / auto) switcher. The initial theme is applied by
// an inline script in <head> to avoid a flash of the wrong theme; this module
// wires up the footer toggle and reacts to OS changes while in "auto" mode.

const STORAGE_KEY = "theme";
const darkQuery = window.matchMedia("(prefers-color-scheme: dark)");

// Click cycles through these in order; the toggle shows the current mode.
const ORDER = ["light", "dark", "auto"];
const ICONS = {
    light: "bi-sun",
    dark: "bi-moon",
    auto: "bi-circle-half",
};
const LABELS = {
    light: "Light mode",
    dark: "Dark mode",
    auto: "Auto mode",
};

const getStoredTheme = () => localStorage.getItem(STORAGE_KEY) || "auto";

const resolveTheme = (theme) => (theme === "auto" ? (darkQuery.matches ? "dark" : "light") : theme);

const applyTheme = (theme) => {
    document.documentElement.setAttribute("data-bs-theme", resolveTheme(theme));
};

const updateSwitcherUI = (theme) => {
    document.querySelectorAll("[data-theme-icon]").forEach((el) => {
        el.className = "bi " + (ICONS[theme] || ICONS.auto);
    });
    document.querySelectorAll("[data-theme-label]").forEach((el) => {
        el.textContent = LABELS[theme] || LABELS.auto;
    });
};

const setTheme = (theme) => {
    localStorage.setItem(STORAGE_KEY, theme);
    applyTheme(theme);
    updateSwitcherUI(theme);
};

// Follow the OS theme only while the user hasn't pinned a specific theme.
darkQuery.addEventListener("change", () => {
    if (getStoredTheme() === "auto") applyTheme("auto");
});

const init = () => {
    updateSwitcherUI(getStoredTheme());
    document.querySelectorAll("[data-theme-toggle]").forEach((el) => {
        el.addEventListener("click", (event) => {
            event.preventDefault();
            const next = ORDER[(ORDER.indexOf(getStoredTheme()) + 1) % ORDER.length];
            setTheme(next);
        });
    });
};

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
} else {
    init();
}
