# import asyncio

import pandas as pd
from io import BytesIO

import requests
# import aiohttp
from pydantic import (
    BaseModel, constr, field_validator, HttpUrl, model_validator, PrivateAttr,
)
from typing import List, Optional, Union, Callable, Any
from enum import Enum, StrEnum
from datetime import datetime, timedelta

from pydantic.main import IncEx
from pydantic.types import date
from pydantic_core import PydanticUndefined

DOMAIN = "nuudel.digitalcourage.de"
DEFAULT_DURATION = 1

MAYBE_FACTOR = 0.5
# Threshold for the status of the booth poll
RED = 0.2
YELLOW = 0.5
BLUE = 0.8


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


class Response(StrEnum):
    YES = "Yes"
    NO = "No"
    UNKNOWN = "Unkown"
    UNDERRESERVE = "Under reserve"
    JA = "Ja"
    NEIN = "Nein"
    UNBEKANNT = "Unbekannt"
    UNTERVORBEHALT = "Unter Vorbehalt"


class ResponseFactor(Enum):
    YES = 1
    NO = 0
    UNKNOWN = 0
    UNDERRESERVE = MAYBE_FACTOR
    JA = 1
    NEIN = 0
    UNBEKANNT = 0
    UNTERVORBEHALT = MAYBE_FACTOR


class PolledTimeSlot(BaseModel):
    string: str
    """Column name of the poll data, corresponding to a time slot"""
    polled: int
    """Number of polled persons"""
    positives: int
    """Number of persons who responded with 'Yes'"""
    maybes: int
    """Number of persons who responded with 'Under reserve'"""
    total: float
    """Total number of persons who responded with 'Yes' or 'Under reserve'"""
    status: Optional[Status] = None
    """Status of the time slot, required for booth poll type only to indicate if 
    staff status is under-, half- or full-staffed"""
    date: Optional[date] = None
    """Formatted date of the time slot"""
    start_time: Optional[constr(pattern=r"\d{2}:\d{2}(?::\d{2})?")] = None
    """Formatted start time of the time slot"""
    end_time: Optional[constr(pattern=r"\d{2}:\d{2}(?::\d{2})?")] = None
    """Formatted end time of the time slot"""
    duration: Optional[float] = None
    """Duration of the time slot"""

    class Config:
        arbitrary_types_allowed = True
        # validate_assignment = True

    def calculate_duration(self):
        self.duration = (
                datetime.strptime(self.end_time, "%H:%M") -
                datetime.strptime(self.start_time, "%H:%M")
        ).seconds / 3600

    def set_end_time(self, value: str):
        self.end_time = value
        self.calculate_duration()

    def set_duration(self, value: float):
        self.duration = value
        self.end_time = (
            datetime.strptime(self.start_time, "%H:%M") +
            timedelta(hours=value)
        ).strftime("%H:%M")

    def __init__(self, **data):
        super().__init__(**data)
        self.date = datetime.strptime(self.string.split(" ")[0], "%Y-%m-%d").date()
        times = self.string.split(" ")[1]
        if "-" in times:
            self.start_time, self.end_time = times.split("-")
        else:
            self.start_time = times
        if self.end_time is not None:
            self.calculate_duration()

class PolledDay(BaseModel):
    title: str
    date: date
    time_slots: List[PolledTimeSlot]
    status: Optional[Status] = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data):
        super().__init__(**data)
        for ii, time_slot in enumerate(self.time_slots):
            if ii == len(self.time_slots) - 1:
                time_slot.set_duration(DEFAULT_DURATION)
            else:
                time_slot.set_end_time(self.time_slots[ii + 1].start_time)



class Percentage(BaseModel):
    value: float

    class Config:
        arbitrary_types_allowed = True

    @field_validator("value", mode="before")
    def validate_value(cls, v):
        if v is None:
            raise ValueError("Percentage must not be None!")
        if v < 0 or v > 100:
            raise ValueError("Percentage must be between 0 and 100")
        return v


class Task(BaseModel):
    title: str
    description: str
    status: Percentage

    class Config:
        arbitrary_types_allowed = True


class PollType(StrEnum):
    booth = "Infostand"
    poster = "Plakatieren"


class FramadatePoll(BaseModel):
    poll_uri: Optional[str] = None
    poll_url: Optional[HttpUrl] = None
    title: Optional[str] = None
    description: Optional[str] = None
    poll_type: Optional[PollType] = None
    # todo: description text from the poll
    signal_group_link: Optional[HttpUrl] = None
    sub_tasks: Optional[List[Task]] = None
    poll_data: Optional[str] = None
    """Raw data of the poll"""
    _poll_data_df: Optional[pd.DataFrame] = PrivateAttr(default=None)
    """DataFrame of the poll data"""
    _time_slots: Optional[List[PolledTimeSlot]] = PrivateAttr(default=None)
    _participation_df: Optional[pd.DataFrame] = PrivateAttr(default=None)
    _days: Optional[List[PolledDay]] = PrivateAttr(default=None)
    """List of days with the participation data - to be casted into timeline entries"""
    total_workforce: Optional[float] = None
    """Sum of estimated workforce over all days"""
    person_hours: Optional[float] = None
    """Person hours required to complete the tasks of the poll"""
    person_hours_per_day: Optional[float] = None
    """Person hours required for every day of the poll"""
    # idea: Averaged sum of staff over all time slots of the poll"""
    minimum_staff: Optional[float] = None
    """Persons required for every time slot of the poll"""
    status: Optional[Status] = None
    """Status of the poll"""

    class Config:
        arbitrary_types_allowed = True
        # validate_assignment = True

    @model_validator(mode='before')
    def url_and_uri(cls, values):
        if "poll_uri" in values:
            values["poll_url"] = HttpUrl(f"https://{DOMAIN}/{values['poll_uri']}")
        elif "poll_url" in values:
            values["poll_uri"] = str(values["poll_url"]).split("/")[-1]
        else:
            raise ValueError("Either poll_uri or poll_url must be set")
        return values

    def __init__(self, **data):
        super().__init__(**data)
        if self.poll_data is None:
            self.fetch_poll_data()
        self.process_poll_data()

    def fetch_poll_data(self):
        # Todo: why does ths return a german doc?
        # self.poll_data = asyncio.run(async_fetch_polls_data([self]))[0]
        self.poll_data = requests.get(f"https://{DOMAIN}/exportcsv.php?poll={self.poll_uri}").text

    def get_poll_data(self) -> str:
        if self.poll_data is None:
            self.fetch_poll_data()
        return self.poll_data

    @property
    def days(self) -> List[PolledDay]:
        if self._days is None:
            self.process_poll_data()
        return self._days

    def set_poll_data(self, data: str):
        self.poll_data = data
        self.process_poll_data()

    def update(self):
        self.fetch_poll_data()
        self.process_poll_data()

    def process_poll_data(self) -> None:
        """Process the poll data to generate the participation data"""
        if self.poll_data is None:
            self.fetch_poll_data()

        self._time_slots = []
        # For each cell in the poll data, except the cells of the first column,
        #  which are the names of the participants, try to replace the cells value
        #  with one of the Response enum values. If the cell value is not in the
        #  Response enum, raise an error.
        io_obj = BytesIO(self.poll_data.encode("utf-8"))
        # Process the first two lines of the csv file to generate proper column names
        first_line = io_obj.readline().decode("utf-8")
        second_line = io_obj.readline().decode("utf-8")
        fl_parts = [string.strip('"') for string in  first_line.split(",")]
        sl_parts = [string.strip('"') for string in  second_line.split(",")]
        column_names = [
            f"{fl_part} {sl_part}" for (fl_part, sl_part) in zip(fl_parts, sl_parts)
        ]
        # Read the csv file into a pandas DataFrame
        self._poll_data_df = pd.read_csv(io_obj, skiprows=2, names=column_names)
        # Remove empty columns (with solely NaN values)
        self._poll_data_df.dropna(axis=1, how="all", inplace=True)
        # Replace the values of the cells with the corresponding Response enum value
        for column in self._poll_data_df.columns[1:]:
            self._poll_data_df[column] = self._poll_data_df[column].map(
                lambda x: Response(x)
            )
        # Estimate the participation for each time slot
        for column in self._poll_data_df.columns[1:]:
            positives = (
                self._poll_data_df[column].value_counts().get(Response.JA, 0) +
                self._poll_data_df[column].value_counts().get(Response.YES, 0)
            )
            maybes = (
                self._poll_data_df[column].value_counts().get(
                    Response.UNTERVORBEHALT, 0) +
                self._poll_data_df[column].value_counts().get(
                    Response.UNDERRESERVE, 0)
            )
            total = positives + maybes * MAYBE_FACTOR
            polled = len(self._poll_data_df[column])
            self._time_slots.append(
                PolledTimeSlot(
                    string=column,
                    positives=positives,
                    maybes=maybes,
                    total=total,
                    polled=polled,
                )
            )
        # Group time_slots by day
        days = {}
        for time_slot in self._time_slots:
            if time_slot.date in days:
                days[time_slot.date].append(time_slot)
            else:
                days[time_slot.date] = [time_slot]
        self._days = []
        for date_, time_slots in days.items():
            self._days.append(
                PolledDay(title=self.title, date=date_, time_slots=time_slots)
            )

        def status_decision(target: Union[PolledTimeSlot, PolledDay], nominator: float, denominator: float):
            if any([nominator is None, denominator is None]):
                target.status = Status.UNDERSTAFFED
            else:
                match nominator / denominator:
                    case x if x < YELLOW:  # RED
                        target.status = Status.UNDERSTAFFED
                    case x if x < BLUE:  # YELLOW
                        target.status = Status.HALF_STAFFED
                    case x if x > BLUE:  # BLUE
                        target.status = Status.FULL_STAFFED
                    case _:  # todo: revisit this
                        target.status = Status.UNDERSTAFFED

        def aggregated_status_decision(target: Union[PolledDay, FramadatePoll], list_: list):
            if all(list_ele.status == Status.FULL_STAFFED for list_ele in list_):
                target.status = Status.FULL_STAFFED
            elif all(list_ele.status == Status.HALF_STAFFED for list_ele in list_):
                target.status = Status.HALF_STAFFED
            elif any(list_ele.status == Status.UNDERSTAFFED for list_ele in list_):
                target.status = Status.UNDERSTAFFED
            elif (
                    any(list_ele.status == Status.HALF_STAFFED for list_ele in list_)
                    and not
                    any(list_ele.status == Status.UNDERSTAFFED for list_ele in list_)
            ):
                target.status = Status.HALF_STAFFED
            else:  # todo: revisit this
                target.status = Status.UNDERSTAFFED

        # Determine status
        match self.poll_type:
            case PollType.booth:
                for day in self._days:
                    # Estimate status per day
                    for time_slot in day.time_slots:
                        # Estimate status per time slot
                        if self.minimum_staff is not None and self.total_workforce is not None:
                            status_decision(time_slot, time_slot.total, self.minimum_staff)
                    aggregated_status_decision(day, self._days)
            case PollType.poster:
                self.total_workforce = 0
                for day in self._days:
                    daily_total = sum(
                        time_slot.total for time_slot in day.time_slots
                        if time_slot.total is not None
                    )
                    if self.person_hours_per_day is not None:
                        status_decision(day, daily_total, self.person_hours_per_day)
                    self.total_workforce += daily_total
                # If there is no required workforce per day, estimate the status of the
                #  whole poll, else decide based on the status of the days
                if all(day.status is None for day in self._days):
                    status_decision(self, self.total_workforce, self.person_hours)
                else:
                    aggregated_status_decision(self, self._days)

#
# async def async_fetch_poll_data(session: aiohttp.ClientSession, poll: FramadatePoll) -> str:
#     """Asynchronous function to download the csv file of a poll"""
#     csv_url = f"https://{DOMAIN}/exportcsv.php?poll={poll.poll_uri}"
#     async with session.get(csv_url) as response:
#         return await response.text()
#
#
# async def async_fetch_polls_data(polls: List[FramadatePoll]) -> List[str]:
#     """Asynchronous function to download the csv files of the polls"""
#     async with aiohttp.ClientSession() as session:
#         tasks = [async_fetch_poll_data(session, poll) for poll in polls]
#         return await asyncio.gather(*tasks)


def fetch_poll_data(poll: FramadatePoll) -> str:
    """Synchronous version"""
    # return asyncio.run(async_fetch_poll_data(poll))
    return requests.get(f"https://{DOMAIN}/exportcsv.php?poll={poll.poll_uri}").text

def fetch_polls_data(polls: List[FramadatePoll], use_async: bool = False) -> List[str]:
    """Synchronous version"""
    # if use_async:
    #     return asyncio.run(async_fetch_polls_data(polls))
    # Instead use requests to download the csv file
    return [requests.get(f"https://{DOMAIN}/exportcsv.php?poll={poll.poll_uri}").text for poll in polls]


if __name__ == "__main__":
    infostand = FramadatePoll(poll_uri="JLKKK3hXJ8w3GExz", title="Infostand", poll_type=PollType.booth)
    plakatieren = FramadatePoll(poll_uri="xhLaKnOUkjw7CsXW", title="Plakatieren", poll_type=PollType.poster)
    # infostand.update()
    # plakatieren.update()
    poll_data = fetch_polls_data([infostand, plakatieren])
    # thread = run_async(async_fetch_polls_data, aiohttp.ClientSession(), [infostand,
    #                                                                      plakatieren])
    # thread.join()
    # data = thread.result