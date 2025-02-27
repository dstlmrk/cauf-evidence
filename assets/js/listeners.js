document.addEventListener("alpine:init", () => {
    Alpine.data("memberSearch", window.memberSearch);
});

document.body.addEventListener("showRosterDialog", (event) => {
    const { teamAtTournamentId } = event.detail;
    const rosterButton = document.getElementById(`rosterButton-${teamAtTournamentId}`);
    rosterButton.click();
});

function birthNumberToDate(birthNumber) {
    let birthNumberStr = birthNumber.toString();
    birthNumberStr = birthNumberStr.replace("/", "");

    let year = parseInt(birthNumberStr.substring(0, 2), 10);
    let month = parseInt(birthNumberStr.substring(2, 4), 10);
    let day = parseInt(birthNumberStr.substring(4, 6), 10);

    if (month > 50) {
        month -= 50;
    }

    let fullYear;
    if (birthNumberStr.length === 9) {
        fullYear = 1900 + year;
    } else if (birthNumberStr.length === 10) {
        fullYear = year < 54 ? 2000 + year : 1900 + year;
    } else {
        fullYear = 1900 + year;
    }

    let yearStr = fullYear.toString();
    let monthStr = month.toString().padStart(2, "0");
    let dayStr = day.toString().padStart(2, "0");

    return `${yearStr}-${monthStr}-${dayStr}`;
}

function isOlderThan15(birthDateStr) {
    if (!birthDateStr) {
        return true;
    }

    let birthDate = new Date(birthDateStr);
    let today = new Date();

    let age = today.getFullYear() - birthDate.getFullYear();
    let monthDiff = today.getMonth() - birthDate.getMonth();
    let dayDiff = today.getDate() - birthDate.getDate();

    if (monthDiff < 0 || (monthDiff === 0 && dayDiff < 0)) {
        age--;
    }

    return age >= 15;
}

function detectSex(birthNumber) {
    let birthNumberStr = birthNumber.toString().replace("/", "");
    let month = parseInt(birthNumberStr.substring(2, 4), 10);
    return month > 50 ? 1 : 2; // 1 = female
}

function memberForm() {
    return {
        initialData: {},
        citizenship: "",
        birthDate: "",
        birthNumber: "",
        sex: "",
        init() {
            this.$refs.form.querySelectorAll("span.asteriskField").forEach((span) => span.remove());
            this.$refs.form.querySelector("#id_birth_number").setAttribute("maxlength", "11");

            this.initialData = Object.fromEntries(new FormData(this.$refs.form).entries());

            this.citizenship = this.initialData.citizenship;
            this.sex = this.initialData.sex;
            this.birthDate = this.initialData.birth_date;
            this.birthNumber = this.initialData.birth_number;

            this.handleCitizenship(this.citizenship);
            this.$watch("citizenship", (value) => {
                this.handleCitizenship(value);
            });

            this.handleBirthNumber(this.birthNumber);
            this.$watch("birthNumber", (value) => {
                this.handleBirthNumber(value);
            });

            this.handleBirthDate(this.birthDate);
            this.$refs.birthDate.addEventListener("blur", () => {
                this.handleBirthDate(this.birthDate);
            });

            if (this.birthDate === "") {
                this.$refs.birthDate.value = this.birthDate;
            }
        },
        handleCitizenship(value) {
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
        handleBirthNumber(value) {
            if (value.length === 10) {
                this.birthDate = birthNumberToDate(value);
                this.sex = detectSex(value);
                this.handleBirthDate(this.birthDate);
            }
        },
        handleBirthDate(value) {
            this.$refs.form.querySelectorAll(".legal-guardian-field input").forEach((input) => {
                if (isOlderThan15(value)) {
                    input.value = "";
                }
                input.disabled = isOlderThan15(value);
            });
            this.$refs.form.querySelectorAll(".regular-email input").forEach((input) => {
                if (!isOlderThan15(value)) {
                    input.value = "";
                }
                input.disabled = !isOlderThan15(value);
            });
        },
    };
}

window.memberForm = memberForm;
