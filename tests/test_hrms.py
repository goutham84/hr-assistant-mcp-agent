from datetime import date, datetime, timedelta

import pytest

from HRMS import *
from utils import seed_services

TOMORROW = date.today() + timedelta(days=1)


@pytest.fixture
def services():
    em, lm, mm, tm = EmployeeManager(), LeaveManager(), MeetingManager(), TicketManager()
    seed_services(em, lm, mm, tm)
    return em, lm, mm, tm


# Employees

def test_search_by_first_name(services):
    em, *_ = services
    assert em.search_employee_by_name("Tony") == ["E004"]


def test_search_tolerates_typos(services):
    em, *_ = services
    assert em.search_employee_by_name("Tony Shrma") == ["E004"]


def test_search_returns_empty_for_unknown_name(services):
    em, *_ = services
    assert em.search_employee_by_name("Zaphod") == []


def test_add_employee_assigns_next_id(services):
    em, *_ = services
    emp_id = em.get_next_emp_id()
    em.add_employee(EmployeeCreate(emp_id=emp_id, name="New Hire", manager_id="E004", email="new@example.com"))
    assert emp_id == "E009"
    assert em.get_manager("E009") == "E004: Tony Sharma"


def test_add_employee_rejects_unknown_manager(services):
    em, *_ = services
    with pytest.raises(ValueError, match="does not exist"):
        em.add_employee(EmployeeCreate(emp_id="E009", name="New Hire", manager_id="E999"))


def test_empty_manager_id_is_stored_as_none(services):
    em, *_ = services
    em.add_employee(EmployeeCreate(emp_id="E009", name="New Hire", manager_id=""))
    assert em.get_employee_details("E009")["manager_id"] is None


def test_invalid_email_is_rejected():
    with pytest.raises(ValueError):
        EmployeeCreate(emp_id="E009", name="New Hire", email="not-an-email")


# Leave

def test_history_still_works_after_applying_leave(services):
    _, lm, *_ = services
    lm.apply_leave(LeaveApplyRequest(emp_id="E004", leave_dates=[TOMORROW]))
    assert TOMORROW.strftime("%B %d, %Y") in lm.get_leave_history("E004")


def test_new_employee_can_apply_leave():
    lm = LeaveManager()
    lm.register_employee("E009")
    assert lm.apply_leave(LeaveApplyRequest(emp_id="E009", leave_dates=[TOMORROW])).endswith("Remaining balance: 19")


def test_leave_rejects_past_and_duplicate_dates():
    lm = LeaveManager()
    lm.register_employee("E009")
    with pytest.raises(ValueError, match="past"):
        lm.apply_leave(LeaveApplyRequest(emp_id="E009", leave_dates=[date.today() - timedelta(days=1)]))
    lm.apply_leave(LeaveApplyRequest(emp_id="E009", leave_dates=[TOMORROW]))
    with pytest.raises(ValueError, match="already applied"):
        lm.apply_leave(LeaveApplyRequest(emp_id="E009", leave_dates=[TOMORROW]))


def test_leave_rejects_insufficient_balance():
    lm = LeaveManager()
    lm.register_employee("E009", balance=1)
    with pytest.raises(ValueError, match="Insufficient"):
        lm.apply_leave(LeaveApplyRequest(emp_id="E009", leave_dates=[TOMORROW, TOMORROW + timedelta(days=1)]))


def test_unknown_employee_leave_raises():
    with pytest.raises(ValueError, match="not found"):
        LeaveManager().get_leave_balance("E999")


# Meetings

def test_seeded_meeting_slot_detects_conflict(services):
    *_, mm, _ = services
    seeded = mm.get_meetings("E001")[0]
    with pytest.raises(ValueError, match="Conflict"):
        mm.schedule_meeting(MeetingCreate(emp_id="E001", meeting_dt=datetime.fromisoformat(seeded["date"]), topic="x"))


def test_cannot_schedule_meeting_in_past():
    with pytest.raises(ValueError, match="past"):
        MeetingManager().schedule_meeting(
            MeetingCreate(emp_id="E001", meeting_dt=datetime.now() - timedelta(hours=1), topic="x"))


def test_cancel_meeting():
    mm = MeetingManager()
    meeting_dt = datetime.combine(TOMORROW, datetime.min.time()).replace(hour=10)
    mm.schedule_meeting(MeetingCreate(emp_id="E001", meeting_dt=meeting_dt, topic="Intro"))
    mm.cancel_meeting(MeetingCancelRequest(emp_id="E001", meeting_dt=meeting_dt))
    assert mm.get_meetings("E001") == []


# Tickets

def test_seeded_tickets_use_standard_ids_and_can_be_updated(services):
    *_, tm = services
    assert tm.tickets[0]["ticket_id"] == "T0001"
    tm.update_ticket_status(TicketStatusUpdate(status="Rejected"), "T0001")
    assert tm.tickets[0]["status"] == "Rejected"


def test_list_tickets_filters(services):
    *_, tm = services
    tm.create_ticket(TicketCreate(emp_id="E004", item="Laptop", reason="New hire setup"))
    assert all(t["emp_id"] == "E004" for t in tm.list_tickets(employee_id="E004"))
    assert all(t["status"] == "Open" for t in tm.list_tickets(status="open"))
