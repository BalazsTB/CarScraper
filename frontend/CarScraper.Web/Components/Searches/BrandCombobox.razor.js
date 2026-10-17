export function attach(input) {
    // Prevent native form submission and cursor movement only for selection keys.
    input.addEventListener("keydown", event => {
        if (["ArrowDown", "ArrowUp"].includes(event.key) ||
            (input.getAttribute("aria-expanded") === "true" && ["Enter", "Escape"].includes(event.key))) {
            event.preventDefault();
        }
    });
}

export function scrollActive(input) {
    const option = document.getElementById(input.getAttribute("aria-activedescendant"));
    option?.scrollIntoView({ block: "nearest" });
}
