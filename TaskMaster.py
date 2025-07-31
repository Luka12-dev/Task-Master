import sys
import json
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem,
    QLabel, QLineEdit, QTextEdit, QSpinBox, QMessageBox,
    QDialog, QCheckBox, QFormLayout, QDialogButtonBox, QComboBox
)
from PyQt6.QtCore import Qt
from plyer import notification
from PyQt6.QtGui import QIcon

DATA_FILE = "tasks.json"
SETTINGS_FILE = "settings.json"


class Task:
    def __init__(self, title, description, hours, day=None, month=None, hour=None, minute=None, done=False):
        self.title = title
        self.description = description
        self.hours = hours
        self.day = day
        self.month = month
        self.hour = hour
        self.minute = minute
        self.done = done

    def to_dict(self):
        return {
            "title": self.title,
            "description": self.description,
            "hours": self.hours,
            "day": self.day,
            "month": self.month,
            "hour": self.hour,
            "minute": self.minute,
            "done": self.done
        }

    @staticmethod
    def from_dict(d):
        return Task(
            d["title"],
            d["description"],
            d["hours"],
            d.get("day"),
            d.get("month"),
            d.get("hour"),
            d.get("minute"),
            d["done"]
        )

class AddTaskDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Add Task")
        self.setFixedSize(320, 500)
        self.layout = QVBoxLayout()

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Title")

        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Description")

        self.hours_input = QSpinBox()
        self.hours_input.setRange(1, 1000)
        self.hours_input.setSuffix(" hours")

        self.month_input = QComboBox()
        self.months_with_days = {
            "01": 31, "02": 28, "03": 31, "04": 30,
            "05": 31, "06": 30, "07": 31, "08": 31,
            "09": 30, "10": 31, "11": 30, "12": 31
        }
        for m in self.months_with_days.keys():
            self.month_input.addItem(m)
        self.month_input.currentIndexChanged.connect(self.update_days)

        self.day_input = QComboBox()

        self.update_days(0)

        self.hour_input = QComboBox()
        for h in range(24):
            self.hour_input.addItem(f"{h:02d}:00")

        self.minute_input = QComboBox()
        for mm in range(60):
            self.minute_input.addItem(f"{mm:02d}")

        self.add_button = QPushButton("Add Task")
        self.add_button.clicked.connect(self.accept)

        self.layout.addWidget(QLabel("Title:"))
        self.layout.addWidget(self.title_input)

        self.layout.addWidget(QLabel("Description:"))
        self.layout.addWidget(self.desc_input)

        self.layout.addWidget(QLabel("Estimated Hours:"))
        self.layout.addWidget(self.hours_input)

        self.layout.addWidget(QLabel("Month:"))
        self.layout.addWidget(self.month_input)

        self.layout.addWidget(QLabel("Day:"))
        self.layout.addWidget(self.day_input)

        self.layout.addWidget(QLabel("Start Hour:"))
        self.layout.addWidget(self.hour_input)

        self.layout.addWidget(QLabel("Start Minute:"))
        self.layout.addWidget(self.minute_input)

        self.layout.addWidget(self.add_button)

        self.setLayout(self.layout)

    def update_days(self, index):
        month_str = self.month_input.currentText()
        days_in_month = self.months_with_days.get(month_str, 31)
        current_day = self.day_input.currentText()
        self.day_input.clear()
        for d in range(1, days_in_month + 1):
            self.day_input.addItem(f"{d:02d}")
        if current_day and int(current_day) <= days_in_month:
            self.day_input.setCurrentText(current_day)
        else:
            self.day_input.setCurrentIndex(0)

    def get_task_data(self):
        title = self.title_input.text()
        desc = self.desc_input.toPlainText()
        hours = self.hours_input.value()
        day = int(self.day_input.currentText())
        month = int(self.month_input.currentText())
        hour = int(self.hour_input.currentText().split(":")[0])
        minute = int(self.minute_input.currentText())
        return title, desc, hours, day, month, hour, minute

class SettingsDialog(QDialog):
    def __init__(self, parent, settings):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(300, 160)

        self.settings = settings  # dict

        layout = QFormLayout()

        self.notifications_checkbox = QCheckBox()
        self.notifications_checkbox.setChecked(self.settings.get("notifications", True))

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        current_theme = self.settings.get("theme", "Dark")
        self.theme_combo.setCurrentText(current_theme)

        layout.addRow("Enable Notifications:", self.notifications_checkbox)
        layout.addRow("Theme:", self.theme_combo)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addWidget(btn_box)

        self.setLayout(main_layout)

    def get_settings(self):
        return {
            "notifications": self.notifications_checkbox.isChecked(),
            "theme": self.theme_combo.currentText()
        }


class TaskMaster(QWidget):
    def __init__(self):
        super().__init__()

        self.settings = {
            "notifications": True,
            "theme": "Dark"
        }
        self.load_settings()
        self.apply_theme(self.settings.get("theme", "Dark"))

        self.setWindowTitle("TaskMaster")
        self.setGeometry(300, 300, 650, 470)

        self.setWindowIcon(QIcon("To-do-list.ico"))

        self.tasks = []
        self.load_tasks()

        self.layout = QVBoxLayout()

        top_bar = QHBoxLayout()
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedWidth(40)
        self.settings_btn.clicked.connect(self.open_settings_dialog)
        top_bar.addStretch()
        top_bar.addWidget(self.settings_btn)
        self.layout.addLayout(top_bar)

        self.task_list = QListWidget()
        self.task_list.itemClicked.connect(self.show_task_detail)
        self.layout.addWidget(self.task_list)

        self.add_task_btn = QPushButton("Add New Task")
        self.add_task_btn.clicked.connect(self.open_add_task_dialog)
        self.layout.addWidget(self.add_task_btn)

        self.total_hours_label = QLabel()
        self.layout.addWidget(self.total_hours_label)

        self.setLayout(self.layout)

        self.refresh_task_list()

    def load_tasks(self):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                self.tasks = [Task.from_dict(d) for d in data]
        except Exception:
            self.tasks = []

    def save_tasks(self):
        with open(DATA_FILE, "w") as f:
            json.dump([t.to_dict() for t in self.tasks], f, indent=4)

    def load_settings(self):
        try:
            with open(SETTINGS_FILE, "r") as f:
                self.settings = json.load(f)
        except Exception:
            self.settings = {"notifications": True, "theme": "Dark"}

    def save_settings(self):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self.settings, f, indent=4)

    def apply_theme(self, theme):
        if theme == "Dark":
            dark_style = """
            QWidget {
                background-color: #121212;
                color: #e0e0e0;
                font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
                font-size: 14px;
            }
            QPushButton {
                background-color: #333333;
                border: none;
                padding: 8px;
                border-radius: 6px;
                color: #e0e0e0;
            }
            QPushButton:hover {
                background-color: #444444;
            }
            QListWidget {
                background-color: #1e1e1e;
                border: 1px solid #333;
            }
            QListWidget::item:selected {
                background-color: #555555;
            }
            QLineEdit, QTextEdit, QSpinBox, QComboBox {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 2px;
            }
            QCheckBox {
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
            }
            QMessageBox {
                background-color: #222222;
                color: #e0e0e0;
            }
            """
            self.setStyleSheet(dark_style)
        else:
            light_style = """
            QWidget {
                background-color: #fafafa;
                color: #222222;
                font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
                font-size: 14px;
            }
            QPushButton {
                background-color: #e0e0e0;
                border: none;
                padding: 8px;
                border-radius: 6px;
                color: #222222;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QListWidget {
                background-color: #ffffff;
                border: 1px solid #ccc;
            }
            QListWidget::item:selected {
                background-color: #a0c8ff;
            }
            QLineEdit, QTextEdit, QSpinBox, QComboBox {
                background-color: #ffffff;
                color: #222222;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 2px;
            }
            QCheckBox {
                color: #222222;
            }
            QLabel {
                color: #222222;
            }
            QMessageBox {
                background-color: #ffffff;
                color: #222222;
            }
            """
            self.setStyleSheet(light_style)

    def refresh_task_list(self):
        self.task_list.clear()
        total_hours = 0
        for task in self.tasks:
            if task.day and task.month and task.hour is not None and task.minute is not None:
                date_str = f"{task.day}/{task.month} {task.hour:02d}:{task.minute:02d}"
            else:
                date_str = "No date"
            item_text = f"{'[Done] ' if task.done else ''}{task.title} - {task.hours}h - {date_str}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, task)
            self.task_list.addItem(item)
            if not task.done:
                total_hours += task.hours

        self.total_hours_label.setText(f"Total pending hours: {total_hours}")

    def open_add_task_dialog(self):
        dialog = AddTaskDialog()
        if dialog.exec():
            title, desc, hours, day, month, hour, minute = dialog.get_task_data()
            if not title.strip():
                QMessageBox.warning(self, "Warning", "Title cannot be empty!")
                return
            new_task = Task(title, desc, hours, day, month, hour, minute)
            self.tasks.append(new_task)
            self.save_tasks()
            self.refresh_task_list()
            if self.settings.get("notifications", False):
                notification.notify(
                    title="TaskMaster: New Task Added",
                    message=f"{new_task.title} scheduled for {new_task.day}/{new_task.month} at {new_task.hour:02d}:{new_task.minute:02d}",
                    timeout=5
                )

    def show_task_detail(self, item):
        task = item.data(Qt.ItemDataRole.UserRole)
        if task.day and task.month and task.hour is not None and task.minute is not None:
            date_str = f"{task.day}/{task.month} at {task.hour:02d}:{task.minute:02d}"
        else:
            date_str = "No date"
        detail = (
            f"Title: {task.title}\n"
            f"Description: {task.description}\n"
            f"Estimated Hours: {task.hours}\n"
            f"Date: {date_str}\n"
            f"Status: {'Done' if task.done else 'Pending'}"
        )
        msg = QMessageBox(self)
        msg.setWindowTitle("Task Details")
        msg.setText(detail)

        done_btn = msg.addButton("Mark as Done" if not task.done else "Mark as Pending", QMessageBox.ButtonRole.ActionRole)
        delete_btn = msg.addButton("Delete Task", QMessageBox.ButtonRole.DestructiveRole)
        msg.addButton(QMessageBox.StandardButton.Close)

        msg.exec()

        clicked = msg.clickedButton()
        if clicked == done_btn:
            task.done = not task.done
            self.save_tasks()
            self.refresh_task_list()
        elif clicked == delete_btn:
            confirm = QMessageBox.question(self, "Confirm Delete",
                                           f"Are you sure you want to delete '{task.title}'?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                self.tasks.remove(task)
                self.save_tasks()
                self.refresh_task_list()

    def open_settings_dialog(self):
        dialog = SettingsDialog(self, self.settings)
        if dialog.exec():
            self.settings = dialog.get_settings()
            self.save_settings()
            self.apply_theme(self.settings.get("theme", "Dark"))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TaskMaster()
    window.show()
    sys.exit(app.exec())