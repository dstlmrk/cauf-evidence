window.memberSearch = function (tournament_id) {
    return {
        results: [],
        selectedMember: {},
        showResults: false,
        highlightedIndex: -1,
        query: "",
        tournament_id: tournament_id, // for rosters only

        // The hidden member_id input and the error message live next to this
        // component, not inside it, so look them up within the surrounding
        // dialog instead of globally — several dialogs can sit in the DOM.
        scope() {
            return this.$root.closest(".modal-content") ?? document;
        },

        setMemberId(value) {
            const memberIdInput = this.scope().querySelector("#id_member_id");
            if (!memberIdInput) {
                return;
            }
            memberIdInput.value = value;
            memberIdInput.dispatchEvent(new Event("change", { bubbles: true }));
        },

        // Used for transfer form
        async fetchForm(member_id = null) {
            const url = member_id ? `/members/transfer-form?member_id=${member_id}` : `/members/transfer-form`;

            const response = await fetch(url, { headers: { "HX-Request": "true" } });

            if (response.ok) {
                const html = await response.text();
                const container = document.querySelector("#transfer-form-container");
                container.innerHTML = html;
                htmx.process(container);
            }
        },

        // Load member info if member_id input has value (for error states)
        async loadPreselectedMember() {
            const memberIdInput = this.scope().querySelector("#id_member_id");
            if (memberIdInput && memberIdInput.value) {
                try {
                    const response = await fetch(
                        `/members/search?member_id=${memberIdInput.value}&tournament_id=${this.tournament_id}`
                    );
                    if (response.ok) {
                        const data = await response.json();
                        if (data.results && data.results.length > 0) {
                            const member = data.results[0];
                            this.selectedMember = member;
                            this.query = member.full_name + " (" + member.birth_year + ")";
                            memberIdInput.dispatchEvent(new Event("change", { bubbles: true }));
                        }
                    }
                } catch (error) {
                    console.log("Could not load preselected member:", error);
                }
            }
        },

        onFocus() {
            this.showResults = true;
            if (this.tournament_id) {
                this.search();
            }
        },

        onBlur() {
            this.showResults = false;
            this.highlightedIndex = -1;
        },

        onInput(event) {
            if (!event.target.value) {
                this.setMemberId("");
            }
            this.scope().querySelector(".form-error-msg")?.remove();
        },

        moveDown() {
            if (this.highlightedIndex < this.results.length - 1) {
                this.highlightedIndex++;
            }
        },
        moveUp() {
            if (this.highlightedIndex > 0) {
                this.highlightedIndex--;
            }
        },
        selectHighlighted() {
            if (this.highlightedIndex >= 0 && this.highlightedIndex < this.results.length) {
                this.selectMember(this.results[this.highlightedIndex]);
            }
        },

        async search() {
            if (this.query.length > 0 && this.query.length < 3) {
                this.results = [];
                this.showResults = false;
                this.selectedMember = {};
                if (!this.tournament_id) {
                    await this.fetchForm();
                }
                return;
            }

            const response = await fetch(`/members/search?q=${this.query}&tournament_id=${this.tournament_id}`);

            if (response.ok) {
                const data = await response.json();
                this.results = data.results;
                this.showResults = true;
            }
        },

        async selectMember(member) {
            this.selectedMember = member;
            this.query = member.full_name + " (" + member.birth_year + ")";
            this.showResults = false;
            this.highlightedIndex = -1;

            if (this.tournament_id) {
                // Roster page
                this.setMemberId(member.id);
            } else {
                // Transfer page
                await this.fetchForm(member.id);
            }
        },
    };
};

// Keeps a submit button in sync with the current value of the hidden
// member_id input. The value is read on every sync and the listener is
// delegated to the dialog, so an HTMX swap replacing the input cannot leave
// the button stuck in the wrong state.
window.memberSubmitButton = function () {
    return {
        init() {
            this.scope().addEventListener("change", (event) => {
                if (event.target.id === "id_member_id") {
                    this.sync();
                }
            });
            this.sync();
        },

        scope() {
            return this.$el.closest(".modal-content") ?? document;
        },

        sync() {
            this.$el.disabled = !this.scope().querySelector("#id_member_id")?.value;
        },
    };
};
