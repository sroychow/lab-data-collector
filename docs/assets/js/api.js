function getToken() {
    return localStorage.getItem("labvault_token");
}

function setToken(token) {
    localStorage.setItem("labvault_token", token);
}

function clearToken() {
    localStorage.removeItem("labvault_token");
    localStorage.removeItem("labvault_user");
}

function setUser(user) {
    localStorage.setItem("labvault_user", JSON.stringify(user));
}

function getUser() {
    const raw = localStorage.getItem("labvault_user");
    if (!raw) return null;

    try {
        return JSON.parse(raw);
    } catch {
        return null;
    }
}

function requireLogin() {
    if (!getToken()) {
        window.location.href = "login.html";
    }
}

async function apiFetch(path, options = {}) {
    const headers = {
        ...(options.headers || {})
    };

    const token = getToken();
    if (token) {
        headers["Authorization"] = `Token ${token}`;
    }

    if (!(options.body instanceof FormData)) {
        headers["Content-Type"] = "application/json";
    }

    const response = await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        headers
    });

    if (response.status === 401 || response.status === 403) {
        clearToken();
        window.location.href = "login.html";
        return;
    }

    if (!response.ok) {
        let message = `Request failed with status ${response.status}`;

        try {
            const data = await response.json();
            message = data.detail || JSON.stringify(data);
        } catch {
            message = await response.text();
        }

        throw new Error(message);
    }

    return response.json();
}

function logout() {
    clearToken();
    window.location.href = "login.html";
}
