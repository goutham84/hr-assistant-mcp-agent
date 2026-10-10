from datetime import date, datetime, time, timedelta
import random
from HRMS import *

def seed_services(employee_manager, leave_manager, meeting_manager, ticket_manager):
    """
    Seeds all service classes with coherent dummy data, using the same public
    methods the MCP tools use so seeded and live records share one format.

    Args:
        employee_manager: Instance of EmployeeManager
        leave_manager: Instance of LeaveManager
        meeting_manager: Instance of MeetingManager
        ticket_manager: Instance of TicketManager

    Returns:
        Dict with the number of seeded employees, leave records, meetings and tickets
    """

    # example.com is reserved for documentation, so test emails never reach a real inbox
    employees_data = [
        # Leadership
        {"emp_id": "E001", "name": "Sarah Johnson", "manager_id": None, "email": "sarah.johnson@example.com"},
        {"emp_id": "E002", "name": "Michael Chen", "manager_id": None, "email": "michael.chen@example.com"},

        # Engineering team under Sarah
        {"emp_id": "E003", "name": "David Wilson", "manager_id": "E001", "email": "david.wilson@example.com"},
        {"emp_id": "E004", "name": "Tony Sharma", "manager_id": "E003", "email": "tony.sharma@example.com"},
        {"emp_id": "E005", "name": "James Rodriguez", "manager_id": "E003", "email": "james.rodriguez@example.com"},

        # Product team under Michael
        {"emp_id": "E006", "name": "Emily Kim", "manager_id": "E002", "email": "emily.kim@example.com"},
        {"emp_id": "E007", "name": "Carlos Mendez", "manager_id": "E006", "email": "carlos.mendez@example.com"},
        {"emp_id": "E008", "name": "Lisa Wong", "manager_id": "E006", "email": "lisa.wong@example.com"},
    ]

    # Populate employee manager (managers are listed before their reports)
    for employee in employees_data:
        employee_manager.add_employee(EmployeeCreate(**employee))

    current_date = date.today()

    # Leave data: random balance plus some past leave requests per employee
    for employee in employees_data:
        emp_id = employee["emp_id"]
        leave_manager.register_employee(emp_id, balance=random.randint(5, 20))

        for _ in range(random.randint(1, 5)):
            # A leave request 1-90 days ago; 30% chance it spans 2-5 consecutive days
            start = current_date - timedelta(days=random.randint(1, 90))
            num_days = random.randint(2, 5) if random.random() > 0.7 else 1
            leave_manager.record_leave(emp_id, [start + timedelta(days=j) for j in range(num_days)])

    # Meeting data: 2-6 meetings per employee over the next 10 days, 9 AM to 4 PM
    meeting_types = ["Team Sync", "Project Review", "Client Meeting", "1:1", "Planning"]
    for employee in employees_data:
        emp_id = employee["emp_id"]
        for _ in range(random.randint(2, 6)):
            meeting_dt = datetime.combine(
                current_date + timedelta(days=random.randint(1, 10)),
                time(hour=random.randint(9, 16)),
            )
            try:
                meeting_manager.schedule_meeting(
                    MeetingCreate(emp_id=emp_id, meeting_dt=meeting_dt, topic=random.choice(meeting_types))
                )
            except ValueError:
                pass  # random slot clashed with an existing meeting; skip it

    # Ticket data
    ticket_items = ["Laptop", "Monitor", "Keyboard", "Mouse", "Headset", "Office Chair", "Software License"]
    ticket_reasons = ["New hire setup", "Replacement for broken item", "Upgrade request", "Project requirement",
                      "Ergonomic needs"]

    for _ in range(random.randint(8, 15)):
        employee = random.choice(employees_data)
        ticket_manager.create_ticket(TicketCreate(
            emp_id=employee["emp_id"],
            item=random.choice(ticket_items),
            reason=random.choice(ticket_reasons),
        ))
        status = random.choice(["Open", "In Progress", "Closed"])
        if status != "Open":
            ticket_id = ticket_manager.tickets[-1]["ticket_id"]
            ticket_manager.update_ticket_status(TicketStatusUpdate(status=status), ticket_id)

    return {
        "employees": len(employee_manager.employees),
        "leave_records": sum(len(data["history"]) for data in leave_manager.employee_leaves.values()),
        "meetings": sum(len(meetings) for meetings in meeting_manager.meetings.values()),
        "tickets": len(ticket_manager.tickets)
    }

if __name__ == "__main__":
    # Initialize services
    employee_manager = EmployeeManager()
    leave_manager = LeaveManager()
    meeting_manager = MeetingManager()
    ticket_manager = TicketManager()

    # Seed the services with data
    result = seed_services(employee_manager, leave_manager, meeting_manager, ticket_manager)

    print(f"Seeded {result['employees']} employees")
    print(f"Seeded {result['leave_records']} leave records")
    print(f"Seeded {result['meetings']} meetings")
    print(f"Seeded {result['tickets']} tickets")
