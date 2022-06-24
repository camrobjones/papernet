
function mdcSetup() {
    let cards = document.querySelectorAll('.mdc-card__primary-action');
    cards.forEach(card => mdc.ripple.MDCRipple.attachTo(card));

    // const select = new mdc.select.MDCSelect(document.querySelector('.mdc-select'));

    // select.listen('MDCSelect:change', () => {
    //   alert(`Selected option at index ${select.selectedIndex} with value "${select.value}"`);
    // });

    const chipSetEl = document.querySelector('.mdc-chip-set');
    if (chipSetEl) {
        const chipSet = new mdc.chips.MDCChipSet(chipSetEl);
    }
}


function defaultUser() {
    let user = {
        username: "Guest User",
        is_authenticated: false,
        guest: true,
        image_url: '/static/spyke/images/guest.jpg',
        stats: {}
    };
    return user;
}

function defaultUserMenu() {
    let userMenu = {
            open: false,
            mode: "login",
            login: {
                username: "",
                password: "",
                error: "",
            },
            signup: {
                username: "",
                email: "",
                password: "",
                passwordConfirm: "",
                errors: [],
            }
        };
    return userMenu;
}


Vue.config.delimiters = ["[[", "]]"];

var app = new Vue({
    el: '#app',
    delimiters: ['[[', ']]'],
    data: {

        // General
        modal: "",

        // Projects,
        newProjectTitle: "New Project Title",
        
        // Profile
        profile: {},
        user: defaultUser(),
        userMenu: defaultUserMenu(),

        // Papers
        info: {project: {}},
        papers: [],
        paper: {},
        citations: {},
        citedBy: {},

        // Search
        query: "",
        results: [],
        cr_results: [],
        resultShow: false,
        progress: {state: false,
                   info: {}},
        progressWidth: "1%",
        task_id: "",

    },
    methods: {
        
        // === Auth ====
        toggleAuth: function(mode) {
            if (this.modal == "auth") {
                this.modal = "";
            } else {
                this.modal = "auth";
            }
        },

        getUser: function(response) {
            let user = response.data.user;
            if (user.is_authenticated) {
                    this.user = response.data.user;
                    this.setUserDates();
                  }
        },

        setUserDates: function() {
        // Transform dates
                let created = new Date(this.user.created);
                this.user.created = created.toLocaleDateString();

                let lastActive = new Date(this.user.last_active);
                this.user.last_active = lastActive.toLocaleDateString();
            },

        openUserMenu: function(mode){
            let modes = ["login", "signup", "profile"];
            if (modes.includes(mode)) {
                this.userMenu.mode = mode;
            } else {
                if (this.user.is_authenticated & this.user.guest == false) {
                    this.userMenu.mode = "profile";
                } else {
                    this.userMenu.mode = "login";
                }
            }
            this.userMenu.open = true;
            // document.getElementById('main-container')
            //     .addEventListener('click', function(e) {
            //         app.dismissModals();
            //     }, { once: true });
            },

        loginUser: function() {
            let url = '/papernet/login_user/';
            let csrftoken = Cookies.get('csrftoken');
            let headers = {'X-CSRFToken': csrftoken};
            let data = this.userMenu.login;
            axios.post(url,data,{headers: headers})
              .then(response => {
                  console.log(response.data);
                  if (response.data.success) {
                    window.location.href = "/papernet/";
                    // this.getUser(response);
                    // this.modal = "";
                    // this.userMenu.mode = "profile";
                    // this.userMenu.login.error = "";
                    // this.notify(`Welcome back, ${app.user.username}!`,
                    //              "Okay", "success");
                } else {
                    this.userMenu.login.error = response.data.message;
                    this.$forceUpdate();
                }
                  
            });
        },

        getUserData: function() {
            let url = '/papernet/user_data/';
            axios.get(url)
              .then(response => {
                  console.log(response.data);
                  if (response.data.success) {
                    this.getUser(response);
                    if (this.user.is_authenticated) {
                        this.userMenu.mode = "profile";
                        this.userMenu.login.error = "";
                    }
                } else {
                }
                  
            });
        },

        logout: function() {
            let url = '/papernet/logout/'
            let csrftoken = Cookies.get('csrftoken');
            let headers = {'X-CSRFToken': csrftoken};
            axios.get(url,{headers: headers})
              .then(response => {
                  console.log(response.data);
                  if (response.data.success) {
                    this.user = defaultUser();
                    this.userMenu = defaultUserMenu();
                    this.modal = "";
                    window.location.href = "/papernet/";
                    // this.notify("You have been logged out", "Okay",
                    //     "success.");
                } else {
                    console.log("Logout failed");
                    this.notify("Logout failed: try again in a few seconds.",
                                  "Okay", "error");
                }
                  
            });
        },

        signup: function() {
            let url = '/papernet/signup/';
            let csrftoken = Cookies.get('csrftoken');
            let headers = {'X-CSRFToken': csrftoken};
            let data = this.userMenu.signup;
            axios.post(url,data,{headers: headers})
              .then(response => {
                  console.log(response.data);
                  if (response.data.success) {
                    window.location.href = "/papernet/";
                    // this.getUser(response);
                    // this.modal = "";
                    // this.userMenu.mode = "profile";
                    // this.userMenu.signup.errors = [];
                    // this.notify(`Thanks for signing up, ${app.user.username}!`,
                                 // "Okay", "success");
                } else {
                    this.userMenu.signup.errors = response.data.errors;
                    this.$forceUpdate();
                }
                  
            });
        },

        // Projects
        createProject() {
            let url = '/papernet/create_project/';
            let csrftoken = Cookies.get('csrftoken');
            let headers = {'X-CSRFToken': csrftoken};
            let data = {title: this.newProjectTitle};
            axios.post(url,data,{headers: headers})
              .then(response => {
                  console.log(response.data);
                  if (response.data.success) {
                    let pk = response.data.pk;
                    window.location.href = "/papernet/project/"+pk;
                } else {
                    this.$forceUpdate();
                }
                  
            });

        },

        // Papers
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
        loadPaper: function(pk) {
            window.location.href = '/papernet/update/paper/' + pk + '/';
        },
        focusPaper: function() {
            window.location.href = '/papernet/update/paper/' + this.paper.pk + '/';
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
            t0 = Date.now()
            let url = '/papernet/search';
            axios.get(url, data).then(response => {
                console.log(response);
                this.results = response.data.results;
                this.resultShow = true;
                console.log("Local results in", Date.now() - t0)
                // mdcSetup();
            });
            let cr_url = '/papernet/search_cr';
            axios.get(cr_url, data).then(response => {
                console.log(response);
                this.cr_results = response.data.results;
                this.resultShow = true;
                console.log("Crossref results in", Date.now() - t0)
                // mdcSetup();
            });
        },
        getX: function(id) {
            let el = $('#'+id);
            if (el.length > 0) {
                return el.position().left + el.outerWidth() / 2;
            }
            return 0;
        },
        getY: function(id) {
            let el = $('#'+id);
            if (el.length > 0) {
                return el.position().top + el.outerHeight() / 2;
            }
            return 0;
        },
        paperX: function() {
            let el = $('#paper');
            // console.log(el);
            if (el.length > 0) {
                // console.log('paperY');
                return el.position().left + el.outerWidth() / 2;
            }
            return 0;
        },
        paperY: function() {
            let el = $('#paper');
            // console.log(el);
            if (el.length > 0) {
                // console.log('paperY');
                return el.position().top + el.outerHeight() / 2;
            }
            return 0;
        },
        addToProject: function(paper_id) {
            let project_id = document.getElementById('project-select').value;
            let url = '/papernet/add_to_project/';
            let csrftoken = Cookies.get('csrftoken');
            let headers = {'X-CSRFToken': csrftoken};
            let data = {"paper_id": paper_id, "project_id": project_id}
            axios.post(url,data,{headers: headers})
              .then(response => {
                  console.log(response.data);
              });

        },
        updateJournal: function(journal_id) {
            let url = '/papernet/update/journal/'+journal_id+'/';
            let csrftoken = Cookies.get('csrftoken');
            let headers = {'X-CSRFToken': csrftoken};
            axios.post(url,{},{headers: headers})
              .then(response => {
                  console.log(response.data);
              });
        },
        updateAuthor: function(author_id) {
            let url = '/papernet/update/author/'+author_id+'/';
            let csrftoken = Cookies.get('csrftoken');
            let headers = {'X-CSRFToken': csrftoken};
            axios.post(url,{},{headers: headers})
              .then(response => {
                  console.log(response.data);
              });
        },
        modifyPerusal: function(row, field) {
            // Update a specific value
            let url = '/papernet/modify/perusal/'
            let paper = this.papers[row];
            let perusal_id = paper.meta.pk;
            let value = paper.meta[field]
            let data = {perusal_id: perusal_id,
                        paper_id: paper.pk,
                        project_id: this.info.project.pk,
                        field: field,
                        value: value}
            console.log("modifying perusal: ", data)
            let csrftoken = Cookies.get('csrftoken');
            let headers = {'X-CSRFToken': csrftoken};
            axios.post(url,data,{headers: headers})
              .then(response => {
                  console.log(response.data);
              });
        },
        modifyTags: function(row, content, add) {
            // Update a specific value
            console.log(`modifyTags(${row}, ${content}, ${add}`)
            let url = '/papernet/modify/perusal/tags/'
            let paper = this.papers[row];
            console.log("paper:", paper)
            let perusal_id = paper.meta.pk;
            let data = {perusal_id: perusal_id,
                        paper_id: paper.pk,
                        project_id: this.info.project.pk,
                        content: content,
                        add: add}
            console.log("modifying tags: ", data)
            let csrftoken = Cookies.get('csrftoken');
            let headers = {'X-CSRFToken': csrftoken};
            axios.post(url,data,{headers: headers})
              .then(response => {
                  console.log(response.data);
              });
        },
        toggleTag: function(row, tag) {
            console.log("toggleTag(", row, tag)
            let paper = this.papers[row]
            let tags = paper.meta.tags;
            let add = true;
            if (tags.includes(tag)) {
                tags.splice(tags.indexOf(tag), 1)
                add = false
            } else {
                tags.push(tag)
            }
            this.modifyTags(row, tag, add)
        },
        addNewTag: function(row) {
            let input = document.getElementsByClassName('new-tag-text')[row];
            let tag = input.value;
            this.info.tags.push([tag, 1]);
            this.toggleTag(row, tag);
            this.modifyTags(row, tag, true);
            input.value = "";
        },
        setStatus: function(row, event) {
            console.log('Set Status', row, event)
            let el = event.target;
            let status = el.previousElementSibling.value;
            this.papers[row].meta.status = status;
        },
        uploadCSV: function() {
            // Upload user's image to server
            let url = '/papernet/upload_csv/';
            let csrftoken = Cookies.get('csrftoken');
            let headers = {'X-CSRFToken': csrftoken,
                           'Content-Type': 'multipart/form-data'};
            var formData = new FormData();
            var csvfile = document.querySelector('#csv-upload');
            formData.append("csv", csvfile.files[0]);
            formData.append("project_id", this.info.project.pk);

            axios.post(url,formData,{headers: headers})
              .then(response => {
                  console.log(response.data)
                  this.task_id = response.data.task_id;
                  setTimeout(this.getProgress, 500)

            });
        },
        getProjectData: function() {
            let project_id = this.info.project.pk
            let url = `/papernet/project_data/${project_id}/`;
            axios.get(url)
              .then(response => {
                  console.log(response.data);
                  this.info.project = response.data.project;
                  this.papers = response.data.papers;
              });
        },
        getProgress: function() {
            let url = '/papernet/get_progress/';
            let params = {task_id: this.task_id}
            let data = {params: params}
            axios.get(url,data)
              .then(response => {
                  console.log(response.data)
                  if (response.data.success) {
                    this.progress = response.data.task;
                    this.setProgressWidth();
                  }
                  if (response.data.task.status != "SUCCESS" && this.task_id.length > 1n) {
                    setTimeout(this.getProgress, 500)
                  } else {
                    this.task_id = "";
                    this.getProjectData();
                  }
            });
        },
        setProgressWidth: function() {

            if (this.progress && this.progress.state) {
                let info = this.progress.info || {}
                let current = info.current || 1
                let total = info.total || 100
                this.progressWidth = (current / total) * 100 + "%"
            } else {
                this.progressWidth = "1%"
            }
        }
    },
    computed: {
    },
    mounted: function() {
        console.log("mounted...");
        this.getUserData();
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
