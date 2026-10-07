document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("productSearch");
    const productCards = document.querySelectorAll(".product-card");
    const categoryButtons = document.querySelectorAll(".category");

    function filterProducts() {
        const searchValue = searchInput ? searchInput.value.toLowerCase().trim() : "";
        const activeCategory = document.querySelector(".category.active");
        const categoryValue = activeCategory ? activeCategory.dataset.category : "all";
        productCards.forEach(function (card) {
            const productName = card.dataset.name || "";
            const productCategory = card.dataset.category || "";
            const matchesSearch = productName.includes(searchValue);
            const matchesCategory = categoryValue === "all" || productCategory === categoryValue || (categoryValue === "Trending" && card.dataset.index !== "none");
            card.style.display = matchesSearch && matchesCategory ? "" : "none";
        });
    }

    if (searchInput) searchInput.addEventListener("input", filterProducts);
    categoryButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            categoryButtons.forEach(item => item.classList.remove("active"));
            this.classList.add("active");
            filterProducts();
        });
    });

    document.querySelectorAll(".js-wishlist-toggle").forEach(function (button) {
        button.addEventListener("click", async function () {
            const productId = this.dataset.productId;
            const response = await fetch(`/wishlist/toggle/${productId}`, { method: "POST" });
            if (response.status === 401) { window.location.href = "/login"; return; }
            const data = await response.json();
            if (!data.ok) return;
            this.dataset.wishlisted = String(data.wishlisted);
            this.classList.toggle("wishlisted", data.wishlisted);
            this.textContent = data.wishlisted ? "♥" : "♡";
            if (this.closest('.wishlist-card') && !data.wishlisted) {
                this.closest('.wishlist-card').remove();
                const pill = document.querySelector('.wishlist-count-pill');
                if (pill) pill.textContent = `${data.count} saved`;
                if (data.count === 0) window.location.reload();
            }
            const headerBadge = document.querySelector('.header-wishlist b');
            if (data.count > 0) {
                if (headerBadge) headerBadge.textContent = data.count;
            } else if (headerBadge) {
                headerBadge.remove();
            }
        }).catch(() => {});
    });

    setTimeout(function () {
        document.querySelectorAll(".flash-message").forEach(function (message) {
            message.style.opacity = "0";
            setTimeout(function () { message.remove(); }, 400);
        });
    }, 3500);
});
