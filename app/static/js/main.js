document.addEventListener("DOMContentLoaded", () => {
    /* ==========================================
       MOBILE MENU
    ========================================== */

    const menuButton =
        document.getElementById("mobile-menu-button");

    const mobileMenu =
        document.getElementById("mobile-menu");


    if (menuButton && mobileMenu) {

        menuButton.addEventListener("click", () => {

            mobileMenu.classList.toggle("hidden");

        });


        mobileMenu
            .querySelectorAll("a")
            .forEach((link) => {

                link.addEventListener(
                    "click",
                    () => {
                        mobileMenu.classList.add("hidden");
                    }
                );

            });

    }


    /* ==========================================
       PASSWORD VISIBILITY
    ========================================== */

    const passwordButtons =
        document.querySelectorAll(
            "[data-toggle-password]"
        );


    passwordButtons.forEach((button) => {

        button.addEventListener("click", () => {

            const targetId =
                button.dataset.togglePassword;

            const input =
                document.getElementById(targetId);

            if (!input) {
                return;
            }


            if (input.type === "password") {

                input.type = "text";

                button.textContent = "Hide";

            } else {

                input.type = "password";

                button.textContent = "Show";

            }

        });

    });


    /* ==========================================
       REGISTER PASSWORD CHECK
    ========================================== */

    const registerForm =
        document.querySelector(
            'form[action="/api/auth/register"]'
        );


    if (registerForm) {

        registerForm.addEventListener(
            "submit",
            (event) => {

                const password =
                    document.getElementById(
                        "register-password"
                    );

                const confirmPassword =
                    document.getElementById(
                        "confirm-password"
                    );


                if (
                    password &&
                    confirmPassword &&
                    password.value !==
                    confirmPassword.value
                ) {

                    event.preventDefault();

                    alert(
                        "Passwords do not match."
                    );

                    confirmPassword.focus();

                }

            }
        );

    }

});