(() => {
    const searchInput = document.getElementById("blogs-search");
    const clearButton = document.getElementById("blogs-clear-search");
    const filters = document.getElementById("blogs-category-filters");
    const cards = Array.from(document.querySelectorAll("[data-news-card]"));
    const resultCount = document.getElementById("blogs-result-count");
    const noResults = document.getElementById("blogs-no-results");
    const filterStatus = document.getElementById("blogs-filter-status");
    const resetButton = document.getElementById("blogs-reset-filters");

    if (!searchInput || !filters || cards.length === 0) return;

    let activeCategory = "all";

    function normalize(value) {
        return (value || "").toLocaleLowerCase().trim();
    }

    function applyFilters() {
        const query = normalize(searchInput.value);
        let visible = 0;

        for (const card of cards) {
            const title = normalize(card.dataset.title);
            const description = normalize(card.dataset.description);
            const categoryText = normalize(card.dataset.categories);
            const published = normalize(card.dataset.published);
            const categories = (card.dataset.categories || "")
                .split("|")
                .map(normalize)
                .filter(Boolean);

            const matchesQuery = !query ||
                `${title} ${description} ${categoryText} ${published}`.includes(query);
            const matchesCategory = activeCategory === "all" || categories.includes(activeCategory);
            const matches = matchesQuery && matchesCategory;

            card.hidden = !matches;
            if (matches) visible += 1;
        }

        if (resultCount) {
            resultCount.textContent = `${visible} ${visible === 1 ? "article" : "articles"}`;
        }
        if (noResults) noResults.hidden = visible !== 0;
        if (filterStatus) {
            filterStatus.textContent = query || activeCategory !== "all"
                ? `Showing ${visible} matching ${visible === 1 ? "article" : "articles"}.`
                : "";
        }
        if (clearButton) clearButton.hidden = !searchInput.value;
    }

    filters.addEventListener("click", (event) => {
        const button = event.target.closest("[data-category-filter]");
        if (!button) return;
        activeCategory = normalize(button.dataset.categoryFilter) || "all";

        for (const item of filters.querySelectorAll("[data-category-filter]")) {
            const selected = item === button;
            item.classList.toggle("is-active", selected);
            item.setAttribute("aria-pressed", String(selected));
        }
        applyFilters();
    });

    searchInput.addEventListener("input", applyFilters);

    if (clearButton) {
        clearButton.addEventListener("click", () => {
            searchInput.value = "";
            searchInput.focus();
            applyFilters();
        });
    }

    if (resetButton) {
        resetButton.addEventListener("click", () => {
            searchInput.value = "";
            activeCategory = "all";
            for (const button of filters.querySelectorAll("[data-category-filter]")) {
                const selected = normalize(button.dataset.categoryFilter) === "all";
                button.classList.toggle("is-active", selected);
                button.setAttribute("aria-pressed", String(selected));
            }
            applyFilters();
        });
    }

    applyFilters();
})();
