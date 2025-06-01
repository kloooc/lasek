const sign_in_btn = document.querySelector("#sign-in-btn");
const sign_up_btn = document.querySelector("#sign-up-btn");
const container = document.querySelector(".container");

sign_up_btn.addEventListener("click", () => {
    container.classList.add("sign-up-mode");
});

sign_in_btn.addEventListener("click", () => {
    container.classList.remove("sign-up-mode");
});
document.getElementById('register-form').addEventListener('submit', function (event) {
    event.preventDefault(); // Zatrzymaj domyślne wysyłanie formularza

    const formData = new FormData(this);

    fetch('{{ url_for("register_page") }}', {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert(data.message);
                if (data.redirect) {
                    window.location.href = data.redirect;
                }
            } else if (data.status === 'error') {
                alert(data.message);
                if (data.errors) {
                    for (let field in data.errors) {
                        data.errors[field].forEach(error => alert(`${field}: ${error}`));
                    }
                }
            }
        })
        .catch(error => {
            alert('Wystąpił błąd podczas wysyłania formularza: ' + error.message);
        });
});
