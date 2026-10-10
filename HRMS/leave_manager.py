from datetime import date
from typing import Dict, List

from HRMS.schemas import LeaveApplyRequest

DEFAULT_LEAVE_BALANCE = 20


class LeaveManager:
    def __init__(self):
        self.employee_leaves: Dict[str, Dict] = {}
        self._next_request_id: int = 1

    def register_employee(self, employee_id: str, balance: int = DEFAULT_LEAVE_BALANCE) -> None:
        """
        Start tracking leave for an employee. Does nothing if they are already registered.
        """
        self.employee_leaves.setdefault(employee_id, {"balance": balance, "history": []})

    def _get_record(self, employee_id: str) -> Dict:
        if employee_id not in self.employee_leaves:
            raise ValueError(f"Employee ID '{employee_id}' not found.")
        return self.employee_leaves[employee_id]

    def record_leave(self, employee_id: str, leave_dates: List[date]) -> None:
        """
        Append leave dates to an employee's history as a single request (no balance check).
        """
        history = self._get_record(employee_id)["history"]
        for leave_date in leave_dates:
            history.append({
                "history_id": len(history) + 1,
                "emp_id": employee_id,
                "leave_date": leave_date,
                "request_id": self._next_request_id,
            })
        self._next_request_id += 1

    def get_leave_balance(self, employee_id: str) -> str:
        data = self._get_record(employee_id)
        return f"{employee_id} has {data['balance']} leave days remaining."

    def apply_leave(self, req: LeaveApplyRequest) -> str:
        employee_id = req.emp_id
        data = self._get_record(employee_id)
        leave_dates = sorted(set(req.leave_dates))

        past = [d for d in leave_dates if d < date.today()]
        if past:
            raise ValueError(f"Cannot apply for leave on past dates: {', '.join(d.isoformat() for d in past)}.")
        already_taken = {record["leave_date"] for record in data["history"]}
        overlap = [d for d in leave_dates if d in already_taken]
        if overlap:
            raise ValueError(f"Leave already applied for: {', '.join(d.isoformat() for d in overlap)}.")

        requested = len(leave_dates)
        if data["balance"] < requested:
            raise ValueError(f"Insufficient leave balance: requested {requested}, available {data['balance']}.")
        data["balance"] -= requested
        self.record_leave(employee_id, leave_dates)
        return f"Leave applied for {requested} day(s). Remaining balance: {data['balance']}"

    def get_leave_history(self, employee_id: str) -> str:
        history = self._get_record(employee_id)["history"]
        if not history:
            return f"No leave history for {employee_id}."
        dates = [record["leave_date"].strftime("%B %d, %Y")
                 for record in sorted(history, key=lambda r: r["leave_date"])]
        return f"Leave history for {employee_id}: {', '.join(dates)}."


if __name__ == "__main__":
    lm = LeaveManager()
    lm.register_employee("E004")
    print(lm.get_leave_history("E004"))
