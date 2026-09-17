import tkinter as tk
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


VALID_CATEGORIES = ["Classroom", "Equipment", "Internet", "Cleanliness", "Facility"]
VALID_PRIORITIES = ["Low", "Medium", "High"]
VALID_STATUSES = ["Pending", "In Progress", "Resolved", "Rejected"]

USERS = {
    "student": {"password": "student123", "role": "student", "name": "Student User"},
    "teacher": {"password": "teacher123", "role": "teacher", "name": "Teacher User"},
    "admin": {"password": "admin123", "role": "admin", "name": "Administrator"},
    "maintenance": {"password": "maint123", "role": "maintenance", "name": "Maintenance Staff"},
    "it": {"password": "it123", "role": "it", "name": "IT Support"},
}

SUBMITTER_ROLES = {"student", "teacher"}


@dataclass
class Concern:
    report_number: str
    student_name: str
    category: str
    location: str
    description: str
    priority: str
    status: str = "Pending"
    assigned_to: str = "Unassigned"
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HelpDeskSystem:
    def __init__(self, data_file: str | Path = "data/concerns.json"):
        self.data_file = Path(data_file)
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        self.concerns: list[dict[str, Any]] = self._load_concerns()
        self.current_user = None

    def _load_concerns(self) -> list[dict[str, Any]]:
        if not self.data_file.exists():
            self.data_file.write_text("[]", encoding="utf-8")
            return []

        try:
            raw_data = json.loads(self.data_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            self.data_file.write_text("[]", encoding="utf-8")
            return []

        return raw_data if isinstance(raw_data, list) else []

    def _save_concerns(self) -> None:
        self.data_file.write_text(json.dumps(self.concerns, indent=2), encoding="utf-8")

    def _next_report_number(self) -> str:
        numbers = []
        for concern in self.concerns:
            try:
                report_number = concern.get("report_number", "")
                if report_number.startswith("PHD-"):
                    numbers.append(int(report_number.split("-")[-1]))
            except ValueError:
                continue

        next_number = max(numbers, default=1000) + 1
        return f"PHD-{next_number}"

    def login(self, username: str, password: str) -> dict[str, str] | None:
        user = USERS.get(username)
        if user and user["password"] == password:
            self.current_user = {"username": username, **user}
            return self.current_user
        return None

    def submit_concern(
        self,
        category: str,
        location: str,
        description: str,
        priority: str = "",
    ) -> dict[str, Any]:
        if self.current_user is None:
            raise PermissionError("Please log in first before submitting a concern.")

        if self.current_user["role"] not in SUBMITTER_ROLES:
            raise PermissionError("Only students and teachers can submit concerns.")

        category = category.strip().title()
        location = location.strip()
        description = description.strip()
        priority = priority.strip()
        student_name = self.current_user["name"].strip()

        if category not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category. Choose from: {', '.join(VALID_CATEGORIES)}")
        if not priority:
            raise ValueError(f"Priority is required. Choose from: {', '.join(VALID_PRIORITIES)}")
        if priority not in VALID_PRIORITIES:
            raise ValueError(f"Invalid priority. Choose from: {', '.join(VALID_PRIORITIES)}")
        if not student_name or not location or not description:
            raise ValueError("Student name, location, and description are required.")

        concern = Concern(
            report_number=self._next_report_number(),
            student_name=student_name,
            category=category,
            location=location,
            description=description,
            priority=priority,
        )
        self.concerns.append(concern.to_dict())
        self._save_concerns()
        return concern.to_dict()

    def search_concerns(self, query: str) -> list[dict[str, Any]]:
        query = query.strip().lower()
        if not query:
            return self.concerns

        matches = []
        for concern in self.concerns:
            if query in concern.get("report_number", "").lower() or query in concern.get("category", "").lower():
                matches.append(concern)
        return matches

    def update_concern_status(self, report_number: str, new_status: str, actor_role: str) -> dict[str, Any]:
        if actor_role == "student":
            raise PermissionError("Students cannot update concern status.")
        if new_status not in VALID_STATUSES:
            raise ValueError(f"Invalid status. Choose from: {', '.join(VALID_STATUSES)}")

        for concern in self.concerns:
            if concern["report_number"] == report_number:
                concern["status"] = new_status
                self._save_concerns()
                return concern

        raise LookupError(f"Concern {report_number} was not found.")

    def delete_concern(self, report_number: str, actor_role: str) -> dict[str, Any]:
        if actor_role not in {"admin", "maintenance", "it"}:
            raise PermissionError("Only authorized staff can delete concerns.")

        for index, concern in enumerate(self.concerns):
            if concern["report_number"] == report_number:
                deleted = self.concerns.pop(index)
                self._save_concerns()
                return deleted

        raise LookupError(f"Concern {report_number} was not found.")

    def view_all_concerns(self) -> list[dict[str, Any]]:
        return self.concerns

    def view_report_history(self) -> list[dict[str, Any]]:
        return sorted(self.concerns, key=lambda item: item.get("created_at", ""), reverse=True)


def format_concern(concern: dict[str, Any]) -> str:
    return (
        f"Report #: {concern['report_number']}\n"
        f"Student: {concern['student_name']}\n"
        f"Category: {concern['category']}\n"
        f"Location: {concern['location']}\n"
        f"Priority: {concern['priority']}\n"
        f"Status: {concern['status']}\n"
        f"Description: {concern['description']}\n"
        f"Created: {concern['created_at']}\n"
    )


# ------------------------------
# Tkinter GUI
# ------------------------------

system = HelpDeskSystem()


def refresh_feed(query: str = "") -> None:
    output_text.delete("1.0", tk.END)

    if query.strip():
        concerns = system.search_concerns(query)
        if not concerns:
            output_text.insert(tk.END, "No matching concerns found.")
            return
    else:
        concerns = system.view_report_history()
        if not concerns:
            output_text.insert(tk.END, "No concerns yet. Start by submitting one.")
            return

    result = ""
    for concern in concerns:
        result += format_concern(concern) + "\n"
    output_text.insert(tk.END, result)


def clear_submit_form() -> None:
    category_entry.delete(0, tk.END)
    location_entry.delete(0, tk.END)
    description_entry.delete(0, tk.END)
    priority_entry.delete(0, tk.END)


def show_login_screen() -> None:
    main_frame.pack_forget()
    login_frame.pack(fill="both", expand=True, padx=20, pady=20)
    login_status_var.set("Please log in first.")


def show_main_screen() -> None:
    login_frame.pack_forget()
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)

    role = system.current_user["role"]
    dashboard_status_var.set(f"Logged in as {system.current_user['name']} ({role})")

    if role in SUBMITTER_ROLES:
        submit_frame.pack(fill="x", padx=20, pady=10)
        search_frame.pack(fill="x", padx=20, pady=10)
    else:
        submit_frame.pack_forget()
        search_frame.pack_forget()

    refresh_feed()


def login_user() -> None:
    username = username_entry.get().strip()
    password = password_entry.get().strip()

    user = system.login(username, password)
    if user is None:
        login_status_var.set("Invalid username or password.")
        return

    show_main_screen()


def logout_user() -> None:
    system.current_user = None
    username_entry.delete(0, tk.END)
    password_entry.delete(0, tk.END)
    show_login_screen()


def submit_concern_from_gui() -> None:
    if system.current_user is None:
        dashboard_status_var.set("Please log in first before submitting a concern.")
        return

    if system.current_user["role"] not in SUBMITTER_ROLES:
        dashboard_status_var.set("Only students and teachers can submit concerns.")
        return

    try:
        category = category_entry.get().strip()
        location = location_entry.get().strip()
        description = description_entry.get().strip()
        priority = priority_entry.get().strip()

        if not priority:
            raise ValueError("Priority is required. Choose from: Low, Medium, High.")

        concern = system.submit_concern(category, location, description, priority)
        clear_submit_form()
        dashboard_status_var.set(f"Concern submitted successfully. Report #: {concern['report_number']}")
        refresh_feed()

    except Exception as error:
        dashboard_status_var.set(f"Error: {error}")


def search_concerns_gui() -> None:
    if system.current_user is None:
        dashboard_status_var.set("Please log in first.")
        return

    query = search_entry.get().strip()
    refresh_feed(query)
    dashboard_status_var.set("Showing search results." if query else "Showing all concerns.")


# Build GUI
window = tk.Tk()
window.title("UPANG HelpDesk")
window.geometry("1000x800")
window.resizable(False, False)

login_frame = tk.Frame(window, bg="#f3f3f3")
login_frame.pack(fill="both", expand=True, padx=20, pady=20)

login_card = tk.Frame(login_frame, bg="#ffffff", bd=2, relief="groove")
login_card.pack(expand=True)

tk.Label(login_card, text="UPANG HelpDesk", font=("Arial", 18, "bold"), bg="#ffffff").pack(pady=(20, 5))
tk.Label(login_card, text="Please login to continue", bg="#ffffff").pack(pady=(0, 20))

login_fields = tk.Frame(login_card, bg="#ffffff")
login_fields.pack(padx=40, pady=10)

tk.Label(login_fields, text="Username", bg="#ffffff").grid(row=0, column=0, padx=5, pady=10, sticky="e")
username_entry = tk.Entry(login_fields, width=28)
username_entry.grid(row=0, column=1, padx=5, pady=10)

tk.Label(login_fields, text="Password", bg="#ffffff").grid(row=1, column=0, padx=5, pady=10, sticky="e")
password_entry = tk.Entry(login_fields, width=28, show="*")
password_entry.grid(row=1, column=1, padx=5, pady=10)

login_button = tk.Button(login_card, text="Login", width=20, command=login_user)
login_button.pack(pady=(10, 20))

login_status_var = tk.StringVar()
login_status_label = tk.Label(login_card, textvariable=login_status_var, bg="#ffffff", wraplength=400, justify="center")
login_status_label.pack(pady=(0, 20))

main_frame = tk.Frame(window, bg="#f5f5f5")

header_frame = tk.Frame(main_frame, bg="#f5f5f5")
header_frame.pack(fill="x", padx=20, pady=(20, 10))

tk.Label(header_frame, text="UPANG HelpDesk Dashboard", font=("Arial", 16, "bold"), bg="#f5f5f5").pack(anchor="w")

logout_button = tk.Button(header_frame, text="Logout", command=logout_user)
logout_button.pack(anchor="e", pady=(10, 0))

dashboard_status_var = tk.StringVar()
status_label = tk.Label(main_frame, textvariable=dashboard_status_var, bg="#f5f5f5", wraplength=500, justify="left")
status_label.pack(anchor="w", padx=20, pady=(0, 10))

submit_frame = tk.LabelFrame(main_frame, text="Submit a Concern", padx=10, pady=10)
submit_inner = tk.Frame(submit_frame)
submit_inner.pack(fill="x")

tk.Label(submit_inner, text="Category").grid(row=0, column=0, padx=5, pady=5, sticky="e")
category_entry = tk.Entry(submit_inner, width=18)
category_entry.grid(row=0, column=1, padx=5, pady=5)

tk.Label(submit_inner, text="Location").grid(row=0, column=2, padx=5, pady=5, sticky="e")
location_entry = tk.Entry(submit_inner, width=18)
location_entry.grid(row=0, column=3, padx=5, pady=5)

tk.Label(submit_inner, text="Priority").grid(row=0, column=4, padx=5, pady=5, sticky="e")
priority_entry = tk.Entry(submit_inner, width=15)
priority_entry.grid(row=0, column=5, padx=5, pady=5)

tk.Label(submit_inner, text="Keyword categories: Classroom, Equipment, Internet, Cleanliness, Facility", fg="gray", font=("Arial", 9)).grid(row=1, column=0, columnspan=6, padx=5, pady=(0, 5), sticky="w")

tk.Label(submit_inner, text="Description").grid(row=2, column=0, padx=5, pady=5, sticky="e")
description_entry = tk.Entry(submit_inner, width=70)
description_entry.grid(row=2, column=1, columnspan=5, padx=5, pady=5, sticky="ew")

submit_button = tk.Button(submit_frame, text="Submit Concern", command=submit_concern_from_gui)
submit_button.pack(pady=(10, 0))

search_frame = tk.LabelFrame(main_frame, text="Search Feed", padx=10, pady=10)
search_entry = tk.Entry(search_frame, width=55)
search_entry.pack(side="left", padx=5)
search_button = tk.Button(search_frame, text="Search", command=search_concerns_gui)
search_button.pack(side="left", padx=5)

feed_frame = tk.LabelFrame(main_frame, text="Concern Feed", padx=10, pady=10)
feed_frame.pack(fill="both", expand=True, padx=20, pady=10)

output_text = tk.Text(feed_frame, height=18, width=120)
output_text.pack(fill="both", expand=True)

show_login_screen()
window.mainloop()