const categoryActions = {
    "Daily": [
        { action: "Wake up on time", target: "Wake up before 7:00 AM", days: 21 },
        { action: "Water Intake", target: "Drink 8 glasses water", days: 30 },
        { action: "Sleep", target: "Sleep 7+ hours", days: 30 }
    ],
    "Fitness": [
        { action: "Workout", target: "Exercise for 30 minutes", days: 30 },
        { action: "Steps", target: "Walk 8000 steps", days: 30 },
        { action: "Stretching", target: "Do 10 min stretching", days: 21 }
    ],
    "Studies": [
        { action: "Deep Study", target: "Study 2 focused hours", days: 30 },
        { action: "Revision", target: "Revise notes daily", days: 21 },
        { action: "Practice", target: "Solve 20 questions", days: 30 }
    ],
    "Finance": [
        { action: "Savings", target: "Save a fixed amount", days: 30 },
        { action: "Expense Tracking", target: "Log all expenses", days: 30 },
        { action: "No-Spend Goal", target: "Avoid impulse purchase", days: 14 }
    ],
    "College": [
        { action: "Assignments", target: "Complete daily assignment target", days: 30 },
        { action: "Attendance", target: "Attend every class", days: 30 },
        { action: "Project Work", target: "Work 45 minutes on project", days: 21 }
    ]
};

function loadActions(category) {
    const container = document.getElementById("actions-container");
    container.innerHTML = "";
    (categoryActions[category] || []).forEach((item) => {
        createActionInput(item.action, item.target, item.days);
    });
}

function createActionInput(actionName, targetValue = "", targetDays = "") {
    const container = document.getElementById("actions-container");
    const div = document.createElement("div");
    div.className = "card";

    const title = document.createElement("h4");
    title.textContent = actionName;

    const hidden = document.createElement("input");
    hidden.type = "hidden";
    hidden.name = "action_name";
    hidden.value = actionName;

    const target = document.createElement("input");
    target.type = "text";
    target.name = "target_value";
    target.value = targetValue;
    target.placeholder = "Goal details (e.g. Drink water)";

    const days = document.createElement("input");
    days.type = "number";
    days.name = "target_days";
    days.min = "1";
    days.value = targetDays;
    days.placeholder = "Number of days (e.g. 21)";
    days.required = true;

    div.append(title, hidden, target, days);
    container.appendChild(div);
}

function addCustomAction() {
    const actionName = prompt("Enter your custom action:");
    if (actionName) {
        createActionInput(actionName.trim(), "", "");
    }
}
