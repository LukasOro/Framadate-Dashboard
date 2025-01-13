import yaml
import param
import panel
from panel.custom import ReactiveHTML
from pydantic import BaseModel, HttpUrl,PrivateAttr
from typing import List, Optional
from datetime import datetime
from pydantic.types import date
from core import (
    FramadatePoll, LinkTarget, PolledDay, Status, Styling, Task,
    fetch_polls_data,
)


class Entry(BaseModel):
    """Class to represent a single day of an activity in the timeline"""

    title: str
    """Title of the activity entry"""
    date: date
    """Date of the activity entry"""
    poll_url: Optional[HttpUrl] = None
    """URL of the poll"""
    poll_link_text: str = "Zur Umfrage"
    """Display text of the poll link"""
    description: Optional[str] = None
    """Description of the activity"""
    #todo: way / address description
    status: Status
    """Staffing and completion status indicator """
    sub_tasks: Optional[List[Task]] = None
    signal_group_link: Optional[HttpUrl] = None
    """Link to the signal group of the activity"""
    signal_group_link_text: str = "Zur Signal-Gruppe"
    """Display text of the signal group link"""
    google_maps_link: Optional[str] = None
    """Coordinates of the location of the activity, to be used to create a google 
    maps link.""" # todo: create google maps link (or map provider agnostic link)
    google_maps_link_text: Optional[str] = "Zur Karte"
    """Display text of the google maps link"""
    header_tag: Optional[Styling] = Styling.h4
    """Styling of the header, containing the title of the entry"""
    body_tag: Optional[Styling] = Styling.p
    """Styling of the body, containing the description of the entry, links and 
    buttons"""
    link_target: LinkTarget = LinkTarget.NEW
    """Kind of action that should happen when clicking links in the entry"""
    _links: Optional[str] = PrivateAttr(default="")
    _html: Optional[str] = PrivateAttr(default="")
    """HTML representation of the activity as a timeline entry"""

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, *args, **kwargs):
        if len(args) == 1 and isinstance(args[0], FramadatePoll):
            kwargs = args[0].dict()
        data = kwargs
        super().__init__(**data)
        self._gen_html()

    def _gen_html(self):  # todo: move to Poll
        link_list = [
            f'<a href="{self.poll_url}" target="{self.link_target.value}">'
            f'{self.poll_link_text}</a>'
        ]
        if self.signal_group_link:
            link_list.append(
                f'<a href="{self.signal_group_link}" target="{self.link_target.value}">'
                f'{self.signal_group_link_text}</a>'
            )
        if self.google_maps_link:
            link_list.append(
                f'<a href="{self.google_maps_link}" target="{self.link_target.value}">'
                f'{self.signal_group_link_text}</a>'
            )
        self._links = " | ".join(link_list)
        self._html = f"""
                <div class="vertical-timeline-item vertical-timeline-element">
                    <div>
                        <span class="vertical-timeline-element-icon bounce-in">
                            <i class="{self.status.value}"> </i>
                        </span>
                        <div class="vertical-timeline-element-content bounce-in">
                            {self.header_tag.value.opener}{self.title}{self.header_tag.value.closer}
                            {self.body_tag.value.opener}{self.description}{self.body_tag.value.closer}
                            {self.body_tag.value.opener}{self._links}{self.body_tag.value.closer}
                            <span class="vertical-timeline-element-date">
{self.date.strftime("DD.MM.YY")}</span>
                        </div>
                    </div>
                </div>
                """

    @property
    def html(self):
        if not self._html:
            self._gen_html()
        return self._html


class Entries(BaseModel):
    items: list[Entry]
    _html: Optional[str] = PrivateAttr("")

    def _gen_html(self):
        self._html = "\n".join([item.html for item in self.items])

    def __init__(self, **data):
        super().__init__(**data)
        self._gen_html()

    @property
    def html(self):
        self._gen_html()
        return self._html


class TimelineLayout(ReactiveHTML):
    card_title = param.String(default="Aktuelle Aktionen")
    polls = param.List(item_type=FramadatePoll)
    _entries = param.ClassSelector(class_=Entries)
    _entries_html = param.String(default="")

    # todo: make each card collapsible
    _template = """
<div class="row d-flex justify-content-center mt-70 mb-70">
    <div>
        <div class="main-card mb-3 card">
            <div class="card-body">
                <h3 class="card-title">{{card_title}}</h3>
                <div class="vertical-timeline vertical-timeline--animate vertical-timeline--one-column">               
                    {{entries_html}}
                </div>
            </div>
        </div>        
    </div> 
</div>
"""
    _stylesheets = [
        "https://cdn.jsdelivr.net/npm/bootstrap@4/dist/css/bootstrap.min.css",
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

    def update(self):
        # thread = run_async(async_fetch_polls_data, aiohttp.ClientSession(), self.polls)
        # thread.join()
        # poll_data = thread.result
        # poll_data = asyncio.run(async_fetch_polls_data(self.polls))
        poll_data = fetch_polls_data(self.polls)
        for poll, data in zip(self.polls, poll_data):
            poll.set_poll_data(data)
        days: List[PolledDay] = []
        for poll in self.polls:
            days.extend(poll.days)
        today = datetime.now().date()
        # past_days = [day for day in days if day.date < today]
        future_days = [day for day in days if day.date >= today]
        future_days_sorted = sorted(future_days, key=lambda x: x.date)
        self._entries = Entries(
            items=[Entry(**day.model_dump()) for day in future_days_sorted]
        )
        self._entries_html = self._entries.html

    def __init__(self, **params):
        if "polls" in params and params["polls"]:
            self.polls = params["polls"]
        super().__init__(**params)
        self.update()


panel.extension()

with open("data/polls.yaml", "r") as f:
    content = yaml.safe_load(f)

app = TimelineLayout(
    polls=[FramadatePoll(**poll) for poll in content],
    width=500,  # todo: necessary?
    # styles={"border": "2px solid lightgray"},
)

# todo: update button
app.servable()