// Alpine.js initialization
document.addEventListener("alpine:init", () => {
    Alpine.data("memberSearch", window.memberSearch);
});

// Event listener for roster dialog
document.body.addEventListener("showRosterDialog", (event) => {
    const { teamAtTournamentId } = event.detail;
    const rosterButton = document.getElementById(`rosterButton-${teamAtTournamentId}`);
    rosterButton.click();
});

// Utility functions for birth number processing
class BirthNumberUtils {
    static toDate(birthNumber) {
        let year = parseInt(birthNumber.substring(0, 2), 10);
        let month = parseInt(birthNumber.substring(2, 4), 10);
        let day = parseInt(birthNumber.substring(4, 6), 10);

        // Adjust month for females (50+ indicates female)
        if (month > 50) {
            month -= 50;
        }

        // Determine full year based on birth number length
        let fullYear;
        if (birthNumber.length === 9) {
            fullYear = 1900 + year;
        } else if (birthNumber.length === 10) {
            fullYear = year < 54 ? 2000 + year : 1900 + year;
        } else {
            fullYear = 1900 + year;
        }

        // Format date string
        let yearStr = fullYear.toString();
        let monthStr = month.toString().padStart(2, "0");
        let dayStr = day.toString().padStart(2, "0");

        return `${yearStr}-${monthStr}-${dayStr}`;
    }

    static detectSex(birthNumber) {
        let month = parseInt(birthNumber.substring(2, 4), 10);
        return month > 50 ? 1 : 2; // 1 = female, 2 = male
    }

    static isOlderThan15(birthDateStr) {
        if (!birthDateStr) {
            return true;
        }

        let birthDate = new Date(birthDateStr);
        let today = new Date();

        let age = today.getFullYear() - birthDate.getFullYear();
        let monthDiff = today.getMonth() - birthDate.getMonth();
        let dayDiff = today.getDate() - birthDate.getDate();

        // Adjust age if birthday hasn't occurred this year
        if (monthDiff < 0 || (monthDiff === 0 && dayDiff < 0)) {
            age--;
        }

        return age >= 15;
    }
}

// Main member form component
function memberForm() {
    return {
        // Component state
        initialData: {},
        citizenship: "",
        birthDate: "",
        birthNumber: "",
        sex: "",

        // Initialization
        init() {
            this.setupForm();
            this.loadInitialData();
            this.setupEventListeners();
            this.setupWatchers();
            this.setupMutationObserver();
        },

        // Form setup
        setupForm() {
            // Remove asterisk fields
            this.$refs.form.querySelectorAll("span.asteriskField").forEach((span) => span.remove());

            // Set birth number max length
            const birthNumberInput = this.$refs.form.querySelector("#id_birth_number");
            if (birthNumberInput) {
                birthNumberInput.setAttribute("maxlength", "11");
            }
        },

        // Load initial form data
        loadInitialData() {
            this.initialData = Object.fromEntries(new FormData(this.$refs.form).entries());

            this.citizenship = this.initialData.citizenship;
            this.sex = this.initialData.sex;
            this.birthDate = this.initialData.birth_date;
            this.birthNumber = this.initialData.birth_number;

            // Apply field states after DOM is ready
            this.$nextTick(() => {
                this.applyFieldStates();
            });
        },

        // Setup event listeners
        setupEventListeners() {
            // Birth date blur event
            if (this.$refs.birthDate) {
                this.$refs.birthDate.addEventListener("blur", () => {
                    this.handleBirthDate(this.birthDate);
                });

                // Set empty value if birth date is empty
                if (this.birthDate === "") {
                    this.$refs.birthDate.value = this.birthDate;
                }
            }
        },

        // Setup Alpine.js watchers
        setupWatchers() {
            this.$watch("citizenship", (value) => {
                this.handleCitizenship(value);
            });

            this.$watch("birthNumber", (value) => {
                this.handleBirthNumber(value);
            });
        },

        // Setup mutation observer for form re-renders
        setupMutationObserver() {
            const observer = new MutationObserver((mutations) => {
                let shouldReapply = false;

                mutations.forEach((mutation) => {
                    if (mutation.type === "childList" || mutation.type === "attributes") {
                        shouldReapply = true;
                    }
                });

                if (shouldReapply) {
                    this.$nextTick(() => {
                        this.applyFieldStates();
                    });
                }
            });

            // Observe form for changes
            observer.observe(this.$refs.form, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ["class", "style"],
            });
        },

        // Apply all field states
        applyFieldStates() {
            this.handleCitizenship(this.citizenship);
            this.handleBirthDate(this.birthDate);
        },

        // Handle citizenship changes
        handleCitizenship(value) {
            // Handle Czech-specific fields
            this.$refs.form.querySelectorAll(".disabled-for-cz input, .disabled-for-cz select").forEach((input) => {
                if (value === "CZ") {
                    input.value = "";
                    input.style.pointerEvents = "none";
                    input.style.backgroundColor = "#e9ecef";
                } else {
                    input.style.pointerEvents = "auto";
                    input.style.backgroundColor = "white";
                }
            });
            this.$refs.form
                .querySelectorAll(".disabled-for-foreigners input, .disabled-for-foreigners select")
                .forEach((input) => {
                    if (value !== "CZ") {
                        input.value = "";
                    }
                    input.disabled = value !== "CZ";
                });
        },

        // Handle birth number changes
        handleBirthNumber(value) {
            if (value.length === 10 || value.length === 11) {
                let birthNumber = value.toString().replace("/", "");
                this.birthDate = BirthNumberUtils.toDate(birthNumber);
                this.sex = BirthNumberUtils.detectSex(birthNumber);
                this.handleBirthDate(this.birthDate);
            }
        },

        // Handle birth date changes
        handleBirthDate(value) {
            // Handle legal guardian fields (disabled for people 15+)
            this.$refs.form.querySelectorAll(".legal-guardian-field input").forEach((input) => {
                if (BirthNumberUtils.isOlderThan15(value)) {
                    input.value = "";
                }
                input.disabled = BirthNumberUtils.isOlderThan15(value);
            });

            // Handle regular email fields (disabled for people under 15)
            this.$refs.form.querySelectorAll(".regular-email input").forEach((input) => {
                if (!BirthNumberUtils.isOlderThan15(value)) {
                    input.value = "";
                }
                input.disabled = !BirthNumberUtils.isOlderThan15(value);
            });
        },
    };
}

// Export for global use
window.memberForm = memberForm;
