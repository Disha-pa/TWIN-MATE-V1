function usePrompt(text) {
    const input = document.getElementById("chat-input");
    if (input) {
        input.value = text;
        document.getElementById("chat-form")?.submit();
    }
}

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".prompt-chip[data-prompt]").forEach((btn) => {
        btn.addEventListener("click", () => usePrompt(btn.dataset.prompt));
    });
});

function startVoice() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        alert("Voice input is not supported in this browser.");
        return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.onresult = (event) => {
        const input = document.getElementById("chat-input");
        if (input) input.value = event.results[0][0].transcript;
    };
    recognition.start();
}
