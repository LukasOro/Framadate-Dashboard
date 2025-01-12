import yaml
from enum import Enum, StrEnum
from pydantic import BaseModel, constr

import param
import panel

from panel.custom import ReactiveHTML

panel.extension()

class TimelineLayout(ReactiveHTML):
    card_title = param.String(default="Aktuelle Aktionen")
    entries = param.String(
        default="""
<div class="vertical-timeline-item vertical-timeline-element">
    <div>
        <span class="vertical-timeline-element-icon bounce-in">
            <i class="badge badge-dot badge-dot-xl badge-success"></i>
        </span>
        <div class="vertical-timeline-element-content bounce-in">
            <h4 class="timeline-title">Meeting with client</h4>
            <p>Meeting with USA Client, today at <a href="javascript:void(0);" data-abc="true">12:00 PM</a></p>
            <span class="vertical-timeline-element-date">9:30 AM</span>
        </div>
    </div>
</div>
"""
    )
    # todo: make each card collapsible
    _template = """
<div class="row d-flex justify-content-center mt-70 mb-70">
    <div class="col-md-6">
        <div class="main-card mb-3 card">
            <div class="card-body">
                <h3 class="card-title">{{card_title}}</h3>
                <div class="vertical-timeline vertical-timeline--animate vertical-timeline--one-column">               
                    {{entries}}
                </div>
            </div>
        </div>        
    </div> 
</div>
"""
    _stylesheets = [
        "https://maxcdn.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css",
        """
body{
     background-color: #eee;
}

.mt-70{
     margin-top: 70px;
}

.mb-70{
     margin-bottom: 70px;
}

.card {
    box-shadow: 0 0.46875rem 2.1875rem rgba(4,9,20,0.03), 0 0.9375rem 1.40625rem rgba(4,9,20,0.03), 0 0.25rem 0.53125rem rgba(4,9,20,0.05), 0 0.125rem 0.1875rem rgba(4,9,20,0.03);
    border-width: 0;
    transition: all .2s;
}

.card {
    position: relative;
    display: flex;
    flex-direction: column;
    min-width: 0;
    word-wrap: break-word;
    background-color: #fff;
    background-clip: border-box;
    border: 1px solid rgba(26,54,126,0.125);
    border-radius: .25rem;
}

.card-body {
    flex: 1 1 auto;
    padding: 1.25rem;
}
.vertical-timeline {
    width: 100%;
    position: relative;
    padding: 1.5rem 0 1rem;
}

.vertical-timeline::before {
    content: '';
    position: absolute;
    top: 0;
    left: 67px;
    height: 100%;
    width: 4px;
    background: #e9ecef;
    border-radius: .25rem;
}

.vertical-timeline-element {
    position: relative;
    margin: 0 0 1rem;
}

.vertical-timeline--animate .vertical-timeline-element-icon.bounce-in {
    visibility: visible;
    animation: cd-bounce-1 .8s;
}
.vertical-timeline-element-icon {
    position: absolute;
    top: 0;
    left: 60px;
}

.vertical-timeline-element-icon .badge-dot-xl {
    box-shadow: 0 0 0 5px #fff;
}

.badge-dot-xl {
    width: 18px;
    height: 18px;
    position: relative;
}
.badge:empty {
    display: none;
}


.badge-dot-xl::before {
    content: '';
    width: 10px;
    height: 10px;
    border-radius: .25rem;
    position: absolute;
    left: 50%;
    top: 50%;
    margin: -5px 0 0 -5px;
    background: #fff;
}

.vertical-timeline-element-content {
    position: relative;
    margin-left: 90px;
    font-size: .8rem;
}

.vertical-timeline-element-content .timeline-title {
    font-size: .8rem;
    text-transform: uppercase;
    margin: 0 0 .5rem;
    padding: 2px 0 0;
    font-weight: bold;
}

.vertical-timeline-element-content .vertical-timeline-element-date {
    display: block;
    position: absolute;
    left: -90px;
    top: 0;
    padding-right: 10px;
    text-align: right;
    color: #adb5bd;
    font-size: .7619rem;
    white-space: nowrap;
}

.vertical-timeline-element-content:after {
    content: "";
    display: table;
    clear: both;
}
"""
    ]


class Tag(BaseModel):
    opener: str
    closer: str


class Styling(Enum):
    h4 = Tag(opener='<h4 class="timeline-title">', closer='</h4>')
    p = Tag(opener='<p>', closer='</p>')


class Status(StrEnum):
    UNDERSTAFFED = "badge badge-dot badge-dot-xl badge-danger"  # red
    HALF_STAFFED = "badge badge-dot badge-dot-xl badge-warning"  # yellow
    FULL_STAFFED = "badge badge-dot badge-dot-xl badge-primary"  # blue
    DONE = "badge badge-dot badge-dot-xl badge-success"  # green


class LinkTarget(StrEnum):
    SAME = "_self"
    NEW = "_blank"
    TOP = "_top"
    PARENT = "_parent"

class Entry(BaseModel):
    header_txt: str
    header_tag: Styling = Styling.h4
    body_txt: str
    body_tag: Styling = Styling.p
    link_txt: str = "Zur Umfrage"
    link_url: constr(pattern=r"https?://.*")
    link_target: LinkTarget = LinkTarget.NEW
    date_txt: constr(pattern=r"\d{2}\.\d{2}\.(?:\d{2,4})?")
    status: Status
    _html: str

    def __init__(self, **data):
        super().__init__(**data)
        self._html = f"""
        <div class="vertical-timeline-item vertical-timeline-element">
            <div>
                <span class="vertical-timeline-element-icon bounce-in">
                    <i class="{self.status.value}"></i>
                </span>
                <div class="vertical-timeline-element-content bounce-in">
                    {self.header_tag.value.opener}{self.header_txt}{self.header_tag.value.closer}
                    {self.body_tag.value.opener}{self.body_txt}{self.body_tag.value.closer}
                    {self.body_tag.value.opener}<a href="{self.link_url}" target="{self.link_target.value}">{self.link_txt}</a>{self.body_tag.value.closer}
                    <span class="vertical-timeline-element-date">{self.date_txt}</span>
                </div>
            </div>
        </div>
        """

    def get_html(self):
        return self._html


class Entries(BaseModel):
    items: list[Entry]
    _html: str

    def __init__(self, **data):
        super().__init__(**data)
        self._html = "\n".join([item.get_html() for item in self.items])

    def get_html(self):
        return self._html
#
# with open("data/polls.yaml", "r") as f:
#     content = yaml.safe_load(f)
#     # entries2 = Entries(items=yaml.safe_load(f))

entries = Entries(items=[
        Entry(
            header_txt="Infostand",
            body_txt="Wahlkampf in der Innenstadt",
            date_txt="10.01.",
            status=Status.DONE,
            link_url="https://www.google.com",
        ),
        Entry(
            header_txt="Plakatieren",
            body_txt="Plakate aufhängen in der ganzen Stadt",
            date_txt="11.01.2025",
            status=Status.UNDERSTAFFED,
            link_url="https://www.google.com",
        ),
    ]
).get_html()

app = TimelineLayout(
    entries=entries,
    # styles={"border": "2px solid lightgray"},
)
app.servable()