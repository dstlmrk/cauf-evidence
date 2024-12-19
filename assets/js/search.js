window.memberSearch = function (tournament_id) {
    return {
        results: [],
        selectedMember: {},
        showResults: false,
        highlightedIndex: -1,
        query: "",
        tournament_id: tournament_id, // for rosters only

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

        onFocus() {
            this.showResults = true;
            if (this.tournament_id) {
                this.search();
            }
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
                await this.fetchForm();
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
                document.querySelector("#id_member_id").value = member.id;
            } else {
                // Transfer page
                await this.fetchForm(member.id);
            }
        },
    };
};
