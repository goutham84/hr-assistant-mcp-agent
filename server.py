import os
from datetime import date, datetime
from typing import List, Dict, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from emails import EmailSender
from HRMS import *
from utils import seed_services  # SEEDING THE DATA OR CREATING THE VIRTUAL DATA ABOUT EMPLOYEES, LEAVES, TICKET INFO , ETC

# load the env
load_dotenv()

employee_manager = EmployeeManager()
meeting_manager = MeetingManager()
leave_manager = LeaveManager()
ticket_manager = TicketManager()

seed_services(employee_manager, leave_manager, meeting_manager, ticket_manager)

emailer = EmailSender(
    smtp_server="smtp.gmail.com",
    port=587,
    username=os.getenv("SENDER_EMAIL"),
    password=os.getenv("SENDER_EMAIL_PWD"),
    use_tls=True
)

mcp = FastMCP("hr-assist")  # CREATING THE MCP


def _require_employee(emp_id: str) -> None:
    """Raise ValueError if the employee ID doesn't exist, so tools fail with a clear message."""
    employee_manager.get_employee_details(emp_id)


@mcp.tool()
def add_employee(emp_name: str, email: str, manager_id: Optional[str] = None) -> str:
    """
    Add a new employee to the HRMS system and set up their leave balance.
    :param emp_name: Full name of the employee
    :param email: Email address of the employee
    :param manager_id: Manager's employee ID, e.g. 'E004' (optional)
    :return: Confirmation message including the new employee ID
    """
    emp_id = employee_manager.get_next_emp_id()
    employee_manager.add_employee(EmployeeCreate(
        emp_id=emp_id,
        name=emp_name,
        manager_id=manager_id,
        email=email
    ))
    leave_manager.register_employee(emp_id)
    return f"Employee {emp_name} added successfully with ID {emp_id}."

@mcp.tool()
def get_employee_details(name: str) -> List[Dict[str, Optional[str]]]:
    """
    Search employees by name. Matches full, first or last name and tolerates small typos.
    :param name: Name of the employee (e.g. 'Tony' or 'Tony Sharma')
    :return: List of matching employee records (ID, name, manager ID, email)
    """
    matches = employee_manager.search_employee_by_name(name)
    if not matches:
        raise ValueError(f"No employees found with name {name}.")
    return [employee_manager.get_employee_details(emp_id) for emp_id in matches]

@mcp.tool()
def get_direct_reports(manager_id: str) -> List[Dict[str, Optional[str]]]:
    """
    List the employees who report directly to a manager.
    :param manager_id: Manager's employee ID
    :return: List of employee records
    """
    return [employee_manager.get_employee_details(eid) for eid in employee_manager.get_direct_reports(manager_id)]

@mcp.tool()
def send_email(to_emails: List[str], subject: str, body: str, html: bool = False) -> str:
    """
    Send an email (e.g. welcome mail to a new hire or a notification to their manager).
    :param to_emails: List of recipient email addresses
    :param subject: Email subject line
    :param body: Email body, plain text or HTML
    :param html: Set to true if the body is HTML
    :return: Confirmation message
    """
    emailer.send_email(subject, body, to_emails, from_email=emailer.username, html=html)
    return f"Email sent successfully to {', '.join(to_emails)}."


@mcp.tool()
def create_ticket(emp_id: str, item: str, reason: str) -> str:
    """
    Create a ticket for buying required items for an employee.
    :param emp_id: Employee ID
    :param item: Item requested (Laptop, ID Card, etc.)
    :param reason: Reason for the request
    :return: Confirmation message
    """
    _require_employee(emp_id)
    ticket_req = TicketCreate(emp_id=emp_id, item=item, reason=reason)
    return ticket_manager.create_ticket(ticket_req)

@mcp.tool()
def update_ticket_status(ticket_id: str, status: TicketStatus) -> str:
    """
    Update the status of a ticket.
    :param ticket_id: Ticket ID, e.g. 'T0001'
    :param status: New status of the ticket
    :return: Confirmation message
    """
    ticket_status_update = TicketStatusUpdate(status=status)
    return ticket_manager.update_ticket_status(ticket_status_update, ticket_id)

@mcp.tool()
def list_tickets(employee_id: Optional[str] = None, status: Optional[TicketStatus] = None) -> List[Dict[str, str]]:
    """
    List tickets, optionally filtered by employee and/or status.
    :param employee_id: Employee ID (optional)
    :param status: Ticket status (optional)
    :return: List of tickets
    """
    return ticket_manager.list_tickets(employee_id=employee_id, status=status)


@mcp.tool()
def schedule_meeting(employee_id: str, meeting_datetime: datetime, topic: str) -> str:
    """
    Schedule a meeting for an employee.
    :param employee_id: Employee ID
    :param meeting_datetime: Date and time of the meeting in ISO format, e.g. 2026-01-15T10:00:00
    :param topic: Topic of the meeting
    :return: Confirmation message
    """
    _require_employee(employee_id)
    meeting_req = MeetingCreate(
        emp_id=employee_id,
        meeting_dt=meeting_datetime,
        topic=topic
    )
    return meeting_manager.schedule_meeting(meeting_req)


@mcp.tool()
def get_meetings(employee_id: str) -> List[Dict[str, str]]:
    """
    Get the list of meetings scheduled for an employee.
    :param employee_id: Employee ID
    :return: List of meetings sorted by date
    """
    return meeting_manager.get_meetings(employee_id)


@mcp.tool()
def cancel_meeting(employee_id: str, meeting_datetime: datetime, topic: Optional[str] = None) -> str:
    """
    Cancel a scheduled meeting for an employee.
    :param employee_id: Employee ID
    :param meeting_datetime: Date and time of the meeting in ISO format, e.g. 2026-01-15T10:00:00
    :param topic: Topic of the meeting, to pick one if several share the same time (optional)
    :return: Confirmation message
    """
    meeting_req = MeetingCancelRequest(
        emp_id=employee_id,
        meeting_dt=meeting_datetime,
        topic=topic
    )
    return meeting_manager.cancel_meeting(meeting_req)


@mcp.tool()
def get_employee_leave_balance(emp_id: str) -> str:
    """
    Get the leave balance of an employee.
    :param emp_id: Employee ID
    :return: Leave balance message
    """
    return leave_manager.get_leave_balance(emp_id)

@mcp.tool()
def apply_leave(emp_id: str, leave_dates: List[date]) -> str:
    """
    Apply for leave for an employee. Dates must be today or later and not already taken.
    :param emp_id: Employee ID
    :param leave_dates: List of leave dates in ISO format, e.g. ["2026-01-20", "2026-01-21"]
    :return: Leave application status message
    """
    req = LeaveApplyRequest(emp_id=emp_id, leave_dates=leave_dates)
    return leave_manager.apply_leave(req)


@mcp.tool()
def get_leave_history(emp_id: str) -> str:
    """
    Get the leave history of an employee.
    :param emp_id: Employee ID
    :return: Leave history message
    """
    return leave_manager.get_leave_history(emp_id)


@mcp.prompt("onboard_new_employee")
def onboard_new_employee(employee_name: str, employee_email: str, manager_name: str):
    return f"""Onboard a new employee with the following details:
    - Name: {employee_name}
    - Email: {employee_email}
    - Manager Name: {manager_name}
    Steps to follow:
    - Look up the manager with get_employee_details to get their employee ID and email.
    - Add the employee to the HRMS system using the manager's ID.
    - Send a welcome email to the employee with their login credentials. (Format: employee_email)
    - Notify the manager about the new employee's onboarding.
    - Raise tickets for a new laptop, id card, and other necessary equipment.
    - Schedule an introductory meeting between the employee and the manager.
    """


if __name__ == "__main__":
    mcp.run(transport="stdio")
