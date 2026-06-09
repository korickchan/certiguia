(function () {
    const splash = document.getElementById("site-splash");
    if (!splash) return;

    const img = splash.querySelector(".site-splash-img");
    const MIN_MS = 450;
    const MAX_MS = 90000;
    let shownAt = Date.now();
    let hidden = false;

    function hideSplash() {
        if (hidden) return;
        hidden = true;
        const wait = Math.max(0, MIN_MS - (Date.now() - shownAt));
        window.setTimeout(function () {
            splash.classList.add("site-splash--hide");
            window.setTimeout(function () {
                splash.remove();
            }, 320);
        }, wait);
    }

    window.addEventListener("load", hideSplash);
    window.setTimeout(hideSplash, MAX_MS);

    if (img) {
        img.addEventListener("error", hideSplash);
    }

    document.querySelectorAll("form[data-show-loading]").forEach(function (form) {
        form.addEventListener("submit", function () {
            splash.classList.remove("site-splash--hide");
            splash.classList.add("site-splash--form");
            splash.style.display = "flex";
            document.body.classList.add("site-loading");
            hidden = false;
            shownAt = Date.now();
        });
    });
})();
