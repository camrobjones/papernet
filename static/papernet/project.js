
function mdcSetup() {
    let cards = document.querySelectorAll('.mdc-card__primary-action');
    cards.forEach(card => mdc.ripple.MDCRipple.attachTo(card));
}

Vue.config.delimiters = ["[[", "]]"];

var app = new Vue({
    el: '#app',
    delimiters: ['[[', ']]'],
    data: {
        project: project,
        papers: papers,
        query: "",
        results: [],
        resultShow: false,
    },
    methods: {
        getByDoi: function(doi) {
            let data = {
                params: {
                    'doi': doi
                }
            };
            let url = '/papernet/doi';
            axios.get(url, data).then(response => {
                console.log(response);
                let data = response.data;
                this.paper = data.paper;
                this.citations = data.citations;
                this.citedBy = data.cited_by;
                this.resultShow = false;

                mdcSetup();

                this.$nextTick(
                    function(){
                        console.log('forcing update...');
                        app.$forceUpdate();
                    }
                );
            });
        },
        refresh: function() {
            let data = {
                params: {
                    'doi': doi
                }
            };
            let url = '/papernet/doi';
            axios.get(url, data).then(response => {
                console.log(response);
                let data = response.data;
                this.paper = data.paper;
            });
        },
        search: function() {
            let data = {
                params: {
                    'query': this.query
                }
            };
            let url = '/papernet/search';
            axios.get(url, data).then(response => {
                console.log(response);
                this.results = response.data.results;
                this.resultShow = true;
                // mdcSetup();
            });
        },
        getX: function(id) {
            let el = $('#'+id);
            if (el.length > 0) {
                return el.position().left + el.width() / 2;
            }
            return 0;
        },
        getY: function(id) {
            let el = $('#'+id);
            if (el.length > 0) {
                return el.position().top + el.height() / 2;
            }
            return 0;
        },
        paperX: function() {
            let el = $('#paper');
            // console.log(el);
            if (el.length > 0) {
                // console.log('paperY');
                return el.position().left + el.width() / 2;
            }
            return 0;
        },
        paperY: function() {
            let el = $('#paper');
            // console.log(el);
            if (el.length > 0) {
                // console.log('paperY');
                return el.position().top + el.height() / 2;
            }
            return 0;
        },
    },
    computed: {
        
    },
    mounted: function() {
        console.log("mounted...");

    }
});

$( document ).ready(function() {
  // Handler for .ready() called.
});

function drawLines() {
    let cards = document.querySelectorAll('.ref.mdc-card');
    for (card of cards) {
        jsPlumb.connect({
        source:"paper",
        target:card.id,
        anchors:[ "Center","Center" ],
        endpoint:[ "Rectangle" ],
        connector:"Straight"
        });
    }
};
