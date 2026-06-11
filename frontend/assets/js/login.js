const form = document.getElementById("loginForm");
const errorBox = document.getElementById("errorBox");

if (getToken()) {
    window.location.href = "index.html";
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.textContent = "";

    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;

    try {
        const data = await apiFetch("/login/", {
            method: "POST",
            body: JSON.stringify({ username, password })
        });

        setToken(data.token);
        setUser(data.user);
        window.location.href = "index.html";
    } catch (error) {
        errorBox.textContent = error.message || "Login failed.";
    }
});
