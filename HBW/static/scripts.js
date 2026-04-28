
document.addEventListener("DOMContentLoaded", () => {
    const flashes = document.querySelectorAll(".flash");

    flashes.forEach(flash => {
        flash.style.opacity = "0";
        setTimeout(() => {
            flash.style.opacity = "1";
        }, 10);

        setTimeout(() => {
            flash.style.opacity = "0";
            setTimeout(() => {
                flash.classList.add("hidden");
            }, 500);
        }, 3000);

        const closeBtn = flash.querySelector(".close-btn");
        if (closeBtn) {
            closeBtn.addEventListener("click", () => {
                flash.style.opacity = "0";
                setTimeout(() => {
                    flash.classList.add("hidden");
                }, 500);
            });
        }
    });
});
document.addEventListener("DOMContentLoaded", function () {
    let modal = document.createElement("div");
    modal.classList.add("image-modal");

    let modalImg = document.createElement("img");
    modal.appendChild(modalImg);

    let closeBtn = document.createElement("span");
    closeBtn.innerHTML = "&times;";
    closeBtn.classList.add("close-modal");
    modal.appendChild(closeBtn);

    document.body.appendChild(modal);

    document.querySelectorAll("img:not(.profile-img)").forEach(img => {
        img.style.cursor = "pointer";
        img.addEventListener("click", function (event) {
            if (!this.closest("a")) { // Exclude images inside links
                modal.style.display = "flex";
                modalImg.src = this.src;
                modalImg.alt = this.alt;
                event.preventDefault();
            }
        });
    });

    modal.addEventListener("click", function (event) {
        if (event.target === modal || event.target === closeBtn) {
            modal.style.display = "none";
        }
    });
});

