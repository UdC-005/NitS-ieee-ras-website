/* =========================================================
   IEEE RAS NIT SILCHAR — SIMPLE THEME LOADER
   Initial page load + same-origin navigation, with failsafe.
========================================================= */
(() => {
    "use strict";

    const loader = document.getElementById("page-loader");
    if (!loader) return;

    const MIN_VISIBLE_MS = 420;
    const FAILSAFE_MS = 8000;

    const messages = [
        "Preparing your experience",
        "Loading the next page",
        "Bringing ideas to life"
    ];

    const messageNode = loader.querySelector("[data-loader-message]");

    let startedAt = performance.now();
    let isHidden = false;
    let finishTimer = null;
    let failsafeTimer = null;
    let messageTimer = null;
    let messageIndex = 0;

    const clearTimers = () => {
        if (finishTimer) window.clearTimeout(finishTimer);
        if (failsafeTimer) window.clearTimeout(failsafeTimer);
        if (messageTimer) window.clearInterval(messageTimer);

        finishTimer = null;
        failsafeTimer = null;
        messageTimer = null;
    };

    const startMessages = () => {
        if (
            !messageNode ||
            window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ) {
            return;
        }

        if (messageTimer) window.clearInterval(messageTimer);

        messageTimer = window.setInterval(() => {
            if (isHidden) return;

            messageIndex = (messageIndex + 1) % messages.length;

            messageNode.classList.add("is-changing");

            window.setTimeout(() => {
                messageNode.textContent = messages[messageIndex];
                messageNode.classList.remove("is-changing");
            }, 160);
        }, 1900);
    };

    const lockPage = () => {
        document.documentElement.classList.add("loader-active");
    };

    const revealLoader = () => {
        isHidden = false;
        startedAt = performance.now();

        if (finishTimer) window.clearTimeout(finishTimer);
        if (failsafeTimer) window.clearTimeout(failsafeTimer);

        loader.hidden = false;
        loader.classList.remove("is-hidden");

        lockPage();
        startMessages();

        failsafeTimer = window.setTimeout(hideLoader, FAILSAFE_MS);
    };

    function hideLoader() {
        if (isHidden) return;

        isHidden = true;

        const wait = Math.max(
            0,
            MIN_VISIBLE_MS - (performance.now() - startedAt)
        );

        if (finishTimer) window.clearTimeout(finishTimer);

        finishTimer = window.setTimeout(() => {
            loader.classList.add("is-hidden");
            document.documentElement.classList.remove("loader-active");

            if (messageTimer) window.clearInterval(messageTimer);
            messageTimer = null;

            window.setTimeout(() => {
                if (loader.classList.contains("is-hidden")) {
                    loader.hidden = true;
                }
            }, 560);
        }, wait);

        if (failsafeTimer) window.clearTimeout(failsafeTimer);
        failsafeTimer = null;
    }

    // Initial page load.
    lockPage();
    startMessages();

    failsafeTimer = window.setTimeout(hideLoader, FAILSAFE_MS);

    if (document.readyState === "complete") {
        hideLoader();
    } else {
        window.addEventListener("load", hideLoader, { once: true });
    }

    // Show the loader on ordinary same-origin link navigation.
    document.addEventListener("click", (event) => {
        if (
            event.defaultPrevented ||
            event.button !== 0 ||
            event.metaKey ||
            event.ctrlKey ||
            event.shiftKey ||
            event.altKey
        ) {
            return;
        }

        const target = event.target;

        const anchor =
            target instanceof Element
                ? target.closest("a[href]")
                : null;

        if (
            !anchor ||
            anchor.hasAttribute("download") ||
            anchor.hasAttribute("data-no-loader")
        ) {
            return;
        }

        const targetWindow = (
            anchor.getAttribute("target") || ""
        ).toLowerCase();

        if (targetWindow && targetWindow !== "_self") return;

        const rawHref = (anchor.getAttribute("href") || "").trim();

        if (
            !rawHref ||
            rawHref.startsWith("#") ||
            /^(mailto:|tel:|javascript:|data:)/i.test(rawHref)
        ) {
            return;
        }

        let destination;

        try {
            destination = new URL(anchor.href, window.location.href);
        } catch {
            return;
        }

        if (destination.origin !== window.location.origin) return;

        // Do not show the loader for a simple same-page hash change.
        if (
            destination.pathname === window.location.pathname &&
            destination.search === window.location.search &&
            destination.hash &&
            destination.hash !== window.location.hash
        ) {
            return;
        }

        revealLoader();
    });

    // Show the loader on ordinary same-origin form submissions.
    document.addEventListener("submit", (event) => {
        if (event.defaultPrevented) return;

        const form = event.target;

        if (!(form instanceof HTMLFormElement)) return;
        if (form.hasAttribute("data-no-loader")) return;

        const targetWindow = (
            form.getAttribute("target") || ""
        ).toLowerCase();

        if (targetWindow && targetWindow !== "_self") return;

        const rawAction = (form.getAttribute("action") || "").trim();

        if (/^(mailto:|tel:|javascript:|data:)/i.test(rawAction)) {
            return;
        }

        let destination;

        try {
            destination = new URL(
                rawAction || window.location.href,
                window.location.href
            );
        } catch {
            return;
        }

        if (destination.origin !== window.location.origin) return;

        revealLoader();
    });

    // Handle browser back/forward navigation.
    window.addEventListener("pageshow", (event) => {
        if (event.persisted) hideLoader();
    });

    // Stop message rotation when leaving the page.
    window.addEventListener("pagehide", () => {
        if (messageTimer) {
            window.clearInterval(messageTimer);
            messageTimer = null;
        }
    });
})();