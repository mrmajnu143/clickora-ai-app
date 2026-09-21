// CLICKORA AI - Frontend JavaScript

document.addEventListener("DOMContentLoaded", function () {

    // ==========================================
    // THUMBNAIL UPLOAD PREVIEW
    // ==========================================

    const thumbnailInput = document.getElementById("thumbnail");
    const preview = document.getElementById("thumbnail-preview");

    if (thumbnailInput && preview) {

        thumbnailInput.addEventListener("change", function () {

            const file = this.files[0];

            if (!file) {
                preview.style.display = "none";
                return;
            }

            if (!file.type.startsWith("image/")) {

                alert("Please upload an image file.");

                this.value = "";

                preview.style.display = "none";

                return;
            }

            const reader = new FileReader();

            reader.onload = function (event) {

                preview.src = event.target.result;

                preview.style.display = "block";

            };

            reader.readAsDataURL(file);

        });

    }


    // ==========================================
    // ANALYZE FORM
    // ==========================================

    const analyzeForm = document.getElementById("analyze-form");

    const analyzeButton =
        document.getElementById("analyze-button");


    if (analyzeForm && analyzeButton) {

        analyzeForm.addEventListener("submit", async function (event) {

            // Stop normal form submission
            event.preventDefault();


            // Disable button
            analyzeButton.disabled = true;

            analyzeButton.innerHTML = "Analyzing...";


            try {

                // Collect form data
                const formData = new FormData(analyzeForm);


                // Send data to Flask
                const response = await fetch(
                    "/analyze",
                    {
                        method: "POST",
                        body: formData
                    }
                );


                const data = await response.json();


                // Check response
                if (!response.ok || !data.success) {

                    alert(
                        data.message ||
                        "Something went wrong. Please try again."
                    );

                    analyzeButton.disabled = false;

                    analyzeButton.innerHTML =
                        "Analyze My Content";

                    return;
                }


                // ==================================
                // GO TO RESULT PAGE
                // ==================================

                window.location.href =
                    "/result/" + data.analysis_id;

            }

            catch (error) {

                console.error(
                    "Analysis error:",
                    error
                );

                alert(
                    "Unable to analyze your content. Please try again."
                );

                analyzeButton.disabled = false;

                analyzeButton.innerHTML =
                    "Analyze My Content";
            }

        });

    }


    // ==========================================
    // PASSWORD VISIBILITY
    // ==========================================

    const passwordToggle =
        document.getElementById("password-toggle");

    const passwordInput =
        document.getElementById("password");


    if (passwordToggle && passwordInput) {

        passwordToggle.addEventListener(
            "click",
            function () {

                if (passwordInput.type === "password") {

                    passwordInput.type = "text";

                    passwordToggle.textContent =
                        "Hide";

                }

                else {

                    passwordInput.type = "password";

                    passwordToggle.textContent =
                        "Show";

                }

            }
        );

    }


    // ==========================================
    // AUTO-HIDE FLASH MESSAGES
    // ==========================================

    const messages =
        document.querySelectorAll(".flash-message");


    messages.forEach(function (message) {

        setTimeout(function () {

            message.style.opacity = "0";


            setTimeout(function () {

                message.remove();

            }, 500);


        }, 4000);

    });

});