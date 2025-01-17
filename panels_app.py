import json

import yaml
import param
import panel
from panel.custom import AnyWidgetComponent
from pydantic import BaseModel, HttpUrl,PrivateAttr
from typing import List, Optional
from datetime import datetime
from pydantic.types import date
from core import (
    FramadatePoll, LinkTarget, PolledDay, Status, Styling, Task,
    fetch_polls_data, PollType, RED, YELLOW, BLUE
)

DEFAULT_DATA = {
    "entries": [],
    "card_title": "Aktuelle Aktionen",
    "legend_title": "Statuslegende",
    "understaffed": int(YELLOW*100),
    "half_staffed": int(BLUE*100),
    "full_staffed": int(BLUE*100),
}


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
    # todo: way / address description
    status: Status
    """Staffing and completion status indicator """
    sub_tasks: Optional[List[Task]] = None
    signal_group_link: Optional[HttpUrl] = None
    """Link to the signal group of the activity"""
    signal_group_link_text: str = "Zur Signal-Gruppe"
    """Display text of the signal group link"""
    google_maps_link: Optional[str] = None
    """Coordinates of the location of the activity, to be used to create a google 
    maps link."""  # todo: create google maps link (or map provider agnostic link)
    google_maps_link_text: Optional[str] = "Zum Treffpunkt"
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
        extra = "allow"

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
        # print("link_list:", link_list)
        self._links = " | ".join(link_list)
        # print("self._links:", self._links)
        self._html = f"""<div class="vertical-timeline-item vertical-timeline-element">
                    <div>
                        <span class="vertical-timeline-element-icon bounce-in">
                            <i class="{self.status.value}"> </i>
                        </span>
                        <div class="vertical-timeline-element-content bounce-in">
                            {self.header_tag.value.opener} {self.title} {self.header_tag.value.closer}
                            {self.body_tag.value.opener} {self.description} {self.body_tag.value.closer}
                            {self.body_tag.value.opener} {self._links} {self.body_tag.value.closer}
                            <span class="vertical-timeline-element-date">{self.date.strftime("%d.%m.%y")}</span>
                        </div>
                    </div>
                </div>"""

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


class Timeline(AnyWidgetComponent):
    index = param.Integer(default=0)
    data = param.Dict(
        default=DEFAULT_DATA
    )

    _importmap = {
        "imports": {
            "handlebars": "https://esm.sh/handlebars@latest",
        }
    }
    _stylesheets = [
        "https://cdn.jsdelivr.net/npm/bootstrap@4/dist/css/bootstrap.min.css",
        """
.badge-dot-xl {
    width: 18px;
    height: 18px;
    position: relative;
}

.badge-dot-xl-inline {
    display: inline-block;
    vertical-align: middle;
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

body {
    background-color: #fff; /* Set the background color to white */
    margin: 0; /* Remove default margin */
    padding: 0; /* Remove default padding */
}

.card {
    box-shadow: none; /* Remove the shadow */
    border: none; /* Remove the border */
    transition: all .2s;
    margin-left: 0; /* Ensure the card is aligned to the left */
}

.card {
    position: relative;
    display: flex;
    flex-direction: column;
    min-width: 0;
    word-wrap: break-word;
    background-color: #fff;
    background-clip: border-box;
    border-radius: .25rem;
}

.card-body {
    padding-top: 10px; /* Reduce the top padding */
    padding-bottom: 1.25rem;
    padding-left: 1.25rem;
    padding-right: 1.25rem;
}

.dot {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    margin-right: 8px;
}

.dot-danger {
    background-color: #d13c47;
}

.dot-warning {
    background-color: #ffc107;
}

.dot-primary {
    background-color: #367df8;
}

.dot-success {
    background-color: #45a550;
}

.legend {
    margin-top: 20px;
    margin-bottom: 5px; /* Reduce the bottom margin */
}

.legend ul {
    list-style: none;
    padding: 0;
}

.legend li {
    display: flex;
    align-items: center;
    margin-bottom: 5px;
}

.mt-20 {
    margin-top: 20px;
}

.mb-10 {
    margin-bottom: 10px;
}

.row {
    margin-top: 20px;
    margin-bottom: 10px;
}

.status-item {
    display: flex;
    align-items: center;
    margin-bottom: 5px;
}

.status-item p {
    margin: 0 0 0 5px;
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

    _esm = """
    import Handlebars from "handlebars"
    const timeline_area_template = `
<head>
    <meta charset="UTF-8">
</head>
<div class="row mt-20 mb-10">
    <div>
        <div class="main-card mb-3 card">
            <div class="card-body">
                <h4 class="card-title">{{card_title}}</h4>
                <div class="vertical-timeline vertical-timeline--animate 
                vertical-timeline--one-column">               
                    {{#each entries}}
                        {{{html}}}
                    {{/each}}
                </div>
            </div>
        </div>        
    </div> 
</div>
    `

    function render({ model, el }) {
      var template = Handlebars.compile(timeline_area_template);
      model.on('change:data', () => {
          el.innerHTML = template(model.get("data"));
          console.log(model.get("data"))
      })
      el.innerHTML = template(model.get("data"));
    }
    export default { render };
    """


panel.extension()

with open("data/polls.yaml", "r", encoding="utf-8") as f:
    content = yaml.safe_load(f)

polls_from_yaml = [FramadatePoll(**poll) for poll in content]


async def update(event, polls: List[FramadatePoll] = polls_from_yaml):
    timeline.index += 1
    data = json.loads(json.dumps(timeline.data))
    # await async_fetch_polls
    poll_data = fetch_polls_data(polls)
    # print("poll_data:", poll_data)
    for poll, datum in zip(polls, poll_data):
        poll.set_poll_data(datum)
    days: List[PolledDay] = []
    for poll in polls:
        days.extend(poll.days)
    today = datetime.now().date()
    # past_days = [day for day in days if day.date < today]
    future_days = [day for day in days if day.date >= today]
    future_days_sorted = sorted(future_days, key=lambda x: x.date)
    # entries_ = Entries(
    #     items=[Entry(**day.model_dump()) for day in future_days_sorted]
    # )
    gen_entries = [Entry(**day.model_dump()) for day in future_days_sorted]
    entries: list = data["entries"]
    entries.extend([{"html": entry.html} for entry in gen_entries])

    data["entries"] = entries
    timeline.data = data


title_and_description = panel.pane.HTML("""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Grüne Würzburg-Stadt</title>
    <h1>Grüne Würzburg-Stadt</h1>
</head>
<p>Willkommen auf der Übersichtsseite zu Gemeinschaftsaktionen der Grünen Würzburg-Stadt.</p>"""
)
refresh_button = panel.widgets.Button(name="Aktualisieren", width=100)
refresh_button.on_click(update)
legend = panel.pane.HTML(
    """<style>
.dot {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    margin-right: 8px;
}

.dot-danger {
    background-color: #d13c47;
}

.dot-warning {
    background-color: #ffc107;
}

.dot-primary {
    background-color: #367df8;
}

.dot-success {
    background-color: #45a550;
}

.legend {
    margin-top: 20px;
    margin-bottom: 5px; /* Reduce the bottom margin */
}

.legend ul {
    list-style: none;
    padding: 0;
}

.legend li {
    display: flex;
    align-items: center;
    margin-bottom: 5px;
}
</style>
<head>
    <meta charset="UTF-8">
</head>
<div class="legend">
    <p>Statuslegende</p>
    <ul>
        <li><span class="dot dot-danger"></span>Unterbesetzt (&lt; 50 
        %)</li>
        <li><span class="dot dot-warning"></span>Halb besetzt (&lt; 80 
        %)</li>
        <li><span class="dot dot-primary"></span>Gut besetzt (&gt; 80 
        %)</li>
        <li><span class="dot dot-success"></span>Abgeschlossen</li>
    </ul>
</div>
    """
)
timeline = Timeline(width=1000, data=DEFAULT_DATA)

app = panel.Column(
    title_and_description,
    refresh_button,
    legend,
    timeline,
)
app
# simulating a click

