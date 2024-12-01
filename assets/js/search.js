window.memberSearch = function (club_id) {
    return {
        query: "",
        results: [],
        selectedMember: {},
        showResults: false,
        club_id: club_id,

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

        async search() {
            if (this.query.length < 3) {
                this.results = [];
                this.showResults = false;
                this.selectedMember = {};
                await this.fetchForm();
                return;
            }

            const response = await fetch(`/members/search?q=${this.query}`);
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

            await this.fetchForm(member.id);
        },
    };
};
