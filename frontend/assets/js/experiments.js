requireLogin();

const list = document.getElementById("experimentList");
const userBox = document.getElementById("userBox");
const errorBox = document.getElementById("errorBox");

const user = getUser();
if (user) {
    userBox.textContent = `Logged in as ${user.username}`;
}

document.getElementById("logoutButton").addEventListener("click", logout);

async function loadExperiments() {
    list.innerHTML = "<p>Loading experiments...</p>";

    try {
        const experiments = await apiFetch("/experiments/");

        if (!experiments.length) {
            list.innerHTML = "<p>No active experiments found.</p>";
            return;
        }

        list.innerHTML = "";

        experiments.forEach((experiment) => {
            const card = document.createElement("article");
            card.className = "card";

            const title = document.createElement("h2");
            title.textContent = experiment.title;

            const meta = document.createElement("p");
            meta.className = "muted";
            meta.textContent = [
                experiment.course_or_project || "No course/project",
                `Protocol ${experiment.protocol_version}`,
                experiment.status
            ].join(" · ");

            const objective = document.createElement("p");
            objective.textContent = experiment.objective || "No objective added.";

            const actions = document.createElement("div");
            actions.className = "actions";

            const openLink = document.createElement("a");
            openLink.className = "btn";
            openLink.href = `experiment.html?slug=${encodeURIComponent(experiment.slug)}`;
            openLink.textContent = "Open experiment";

            const submitLink = document.createElement("a");
            submitLink.className = "btn btn-secondary";
            submitLink.href = `submit.html?slug=${encodeURIComponent(experiment.slug)}`;
            submitLink.textContent = "Submit data";

            const submissionsLink = document.createElement("a");
            submissionsLink.className = "btn btn-secondary";
            submissionsLink.href = `submission.html?experiment=${encodeURIComponent(experiment.slug)}`;
            submissionsLink.textContent = "View submissions";

            actions.appendChild(openLink);
            actions.appendChild(submitLink);
            actions.appendChild(submissionsLink);

            card.appendChild(title);
            card.appendChild(meta);
            card.appendChild(objective);
            card.appendChild(actions);

            list.appendChild(card);
        });
    } catch (error) {
        errorBox.textContent = error.message;
        list.innerHTML = "";
    }
}

loadExperiments();
