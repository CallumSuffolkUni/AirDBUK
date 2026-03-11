document.addEventListener('DOMContentLoaded', () => {
    // grab all text inputs marked for autocomplete
    const inputs = document.querySelectorAll('input.autocomplete');
    inputs.forEach(input => {
        input.addEventListener('input', function () {
            const listId = this.getAttribute('list');
            if (!listId) return;
            const datalist = document.getElementById(listId);
            const term = this.value;
            if (term.length < 2) {
                // clear suggestions if too short
                if (datalist) datalist.innerHTML = '';
                return;
            }
            fetch(`/ajax/airport-autocomplete/?term=${encodeURIComponent(term)}`)
                .then(response => response.json())
                .then(data => {
                    if (!datalist) return;
                    datalist.innerHTML = '';
                    data.forEach(item => {
                        const option = document.createElement('option');
                        option.value = item;
                        datalist.appendChild(option);
                    });
                });
        });
    });
});