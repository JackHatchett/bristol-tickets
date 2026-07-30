"""ui/main_window.py — Test Control desktop window (4-tab workflow).

Mirrors bristol/ui/main_window.py's app.py + ui/ layout for
regularity. Pure UI class — takes an already-provisioned sqlite3.Connection
from app.py and does no path/schema logic of its own.
"""

import sqlite3
from datetime import datetime, timezone
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QLabel, QListWidget, QListWidgetItem, QPushButton, QTextEdit,
    QSplitter, QMessageBox, QGroupBox, QFormLayout, QTabWidget, QLineEdit,
    QScrollArea, QTextBrowser
)

class TestControlWindow(QMainWindow):
    def __init__(self, conn: sqlite3.Connection):
        super().__init__()
        self.conn = conn
        self.current_run_id = None
        self.selected_item_id = None
        self.editor_selected_case_id = None

        self.setWindowTitle("Test Control // Manual Script Execution & Management Suite")
        self.resize(1300, 850)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self._build_execution_tab()
        self._build_session_manager_tab()
        self._build_management_tab()
        self._build_analytics_tab()

        self._refresh_all_contexts()

    def _refresh_all_contexts(self):
        self._populate_run_context()
        self._populate_editor_context()
        self._populate_manager_run_list()
        self._calculate_analytics()

    def _build_execution_tab(self):
        exec_widget = QWidget()
        main_layout = QVBoxLayout(exec_widget)

        context_layout = QHBoxLayout()
        context_layout.addWidget(QLabel("Active Cloned Test Run Session:"))
        self.run_picker = QComboBox()
        self.run_picker.currentIndexChanged.connect(self._handle_run_switch)
        context_layout.addWidget(self.run_picker, 1)
        main_layout.addLayout(context_layout)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter, 1)

        script_group = QGroupBox("Active Test Run Checklist (Script Rows)")
        script_layout = QVBoxLayout(script_group)
        self.list_run_items = QListWidget()
        self.list_run_items.itemClicked.connect(self._handle_item_click)
        script_layout.addWidget(self.list_run_items)
        splitter.addWidget(script_group)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)

        eval_frame = QWidget()
        eval_layout = QVBoxLayout(eval_frame)
        eval_layout.setContentsMargins(0, 0, 0, 0)

        detail_box = QGroupBox("Test Case Execution Detail")
        detail_layout = QVBoxLayout(detail_box)
        self.ui_detail_browser = QTextBrowser()
        self.ui_detail_browser.setMinimumHeight(180)
        self.ui_detail_browser.setHtml("<p style='color: gray;'>Select a test item from the list to view its specification context.</p>")
        detail_layout.addWidget(self.ui_detail_browser)
        eval_layout.addWidget(detail_box)

        step_box = QGroupBox("Action Steps Breakdown (Double-Click Step to Toggle Pass/Fail Status)")
        step_box_layout = QVBoxLayout(step_box)
        self.list_steps = QListWidget()
        self.list_steps.setMinimumHeight(150)
        self.list_steps.itemDoubleClicked.connect(self._toggle_step_status)
        step_box_layout.addWidget(self.list_steps)
        eval_layout.addWidget(step_box)

        notes_box = QGroupBox("Execution Comments / Defect Observations")
        notes_layout = QVBoxLayout(notes_box)
        self.ui_notes = QTextEdit()
        self.ui_notes.setMinimumHeight(100)
        self.ui_notes.setPlaceholderText("Enter logs, console outputs, or edge cases encountered...")
        notes_layout.addWidget(self.ui_notes)
        eval_layout.addWidget(notes_box)

        btn_layout = QHBoxLayout()
        self.btn_mark_pass = QPushButton("Mark Entire Script Row Passed")
        self.btn_mark_pass.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 8px;")
        self.btn_mark_pass.clicked.connect(lambda: self._apply_status_change("passed"))

        self.btn_mark_fail = QPushButton("Mark Entire Script Row Failed")
        self.btn_mark_fail.setStyleSheet("background-color: #c62828; color: white; font-weight: bold; padding: 8px;")
        self.btn_mark_fail.clicked.connect(lambda: self._apply_status_change("failed"))

        btn_layout.addWidget(self.btn_mark_pass)
        btn_layout.addWidget(self.btn_mark_fail)
        eval_layout.addLayout(btn_layout)

        scroll_area.setWidget(eval_frame)
        splitter.addWidget(scroll_area)

        splitter.setSizes([450, 800])
        self.tabs.addTab(exec_widget, "1. Execution Dashboard")

    def _build_session_manager_tab(self):
        mgr_widget = QWidget()
        layout = QHBoxLayout(mgr_widget)

        left_box = QGroupBox("Existing Cloned Test Sessions")
        left_layout = QVBoxLayout(left_box)
        self.mgr_run_list = QListWidget()
        self.mgr_run_list.itemClicked.connect(self._handle_mgr_run_click)
        left_layout.addWidget(self.mgr_run_list)

        self.btn_delete_run = QPushButton("Delete Selected Cloned Session")
        self.btn_delete_run.setStyleSheet("background-color: #d32f2f; color: white; padding: 6px;")
        self.btn_delete_run.clicked.connect(self._delete_cloned_session)
        left_layout.addWidget(self.btn_delete_run)
        layout.addWidget(left_box, 1)

        right_box = QGroupBox("Session Cloning & Modification Actions")
        form_layout = QFormLayout(right_box)

        self.edit_run_name = QLineEdit()
        form_layout.addRow("Rename Selected Session:", self.edit_run_name)

        self.btn_rename_run = QPushButton("Apply Name Update")
        self.btn_rename_run.clicked.connect(self._rename_cloned_session)
        form_layout.addRow(self.btn_rename_run)

        form_layout.addRow(QLabel("<hr/>"))

        form_layout.addRow(QLabel("<b>Clone Master Blueprints into New Session:</b>"))
        self.new_run_name_input = QLineEdit()
        self.new_run_name_input.setPlaceholderText("e.g., July 1st iOS Regression Run")
        form_layout.addRow("New Session Name:", self.new_run_name_input)

        self.btn_create_run = QPushButton("Generate New Cloned Test Session")
        self.btn_create_run.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 6px;")
        self.btn_create_run.clicked.connect(self._generate_new_cloned_session)
        form_layout.addRow(self.btn_create_run)

        layout.addWidget(right_box, 1)
        self.tabs.addTab(mgr_widget, "2. Session Clones Manager")

    def _build_management_tab(self):
        mgmt_widget = QWidget()
        layout = QHBoxLayout(mgmt_widget)

        left_box = QGroupBox("Master Blueprints (Templates Catalog)")
        left_layout = QVBoxLayout(left_box)
        self.editor_case_list = QListWidget()
        self.editor_case_list.itemClicked.connect(self._handle_editor_case_click)
        left_layout.addWidget(self.editor_case_list)

        self.btn_delete_case = QPushButton("Delete Selected Blueprint Template")
        self.btn_delete_case.setStyleSheet("background-color: #d32f2f; color: white;")
        self.btn_delete_case.clicked.connect(self._delete_current_blueprint)
        left_layout.addWidget(self.btn_delete_case)
        layout.addWidget(left_box, 1)

        right_box = QGroupBox("Add / Edit Template Blueprints")
        form_layout = QFormLayout(right_box)

        self.edit_suite_picker = QComboBox()
        form_layout.addRow("Target Application Context (Suite):", self.edit_suite_picker)

        self.edit_section = QLineEdit()
        self.edit_section.setPlaceholderText("e.g., Login View, Inventory Page")
        form_layout.addRow("App Section (Workbook Tab):", self.edit_section)

        self.edit_title = QLineEdit()
        form_layout.addRow("Case Title (Script Row):", self.edit_title)

        self.edit_preconditions = QTextEdit()
        self.edit_preconditions.setMaximumHeight(80)
        form_layout.addRow("Preconditions:", self.edit_preconditions)

        self.edit_step_instruction = QLineEdit()
        form_layout.addRow("Step Action Instruction:", self.edit_step_instruction)

        self.edit_step_expected = QLineEdit()
        form_layout.addRow("Step Expected Outcome:", self.edit_step_expected)

        self.btn_save_case = QPushButton("Commit to Master Templates")
        self.btn_save_case.setStyleSheet("background-color: #1976d2; color: white; font-weight: bold; padding: 6px;")
        self.btn_save_case.clicked.connect(self._save_blueprint_template)
        form_layout.addRow(self.btn_save_case)

        layout.addWidget(right_box, 1)
        self.tabs.addTab(mgmt_widget, "3. Blueprint Template Editor")

    def _build_analytics_tab(self):
        analytics_widget = QWidget()
        layout = QVBoxLayout(analytics_widget)

        box = QGroupBox("Historical Execution Metrics")
        self.analytics_layout = QFormLayout(box)

        self.lbl_total_runs = QLabel("-")
        self.analytics_layout.addRow("Total Logged Clone Sessions:", self.lbl_total_runs)

        self.lbl_total_items = QLabel("-")
        self.analytics_layout.addRow("Total Checklist Script Rows across Sessions:", self.lbl_total_items)

        self.lbl_passed_count = QLabel("-")
        self.analytics_layout.addRow("Total Globally Passed Script Rows:", self.lbl_passed_count)

        self.lbl_failed_count = QLabel("-")
        self.analytics_layout.addRow("Total Globally Failed Defect Rows:", self.lbl_failed_count)

        self.lbl_completion_rate = QLabel("-")
        self.analytics_layout.addRow("Overall Completion Ingestion Velocity:", self.lbl_completion_rate)

        layout.addWidget(box)

        btn_refresh = QPushButton("Refresh Analytics Metrics Engine")
        btn_refresh.clicked.connect(self._calculate_analytics)
        layout.addWidget(btn_refresh)

        self.tabs.addTab(analytics_widget, "4. Analytics Room")

    def _populate_run_context(self):
        self.run_picker.blockSignals(True)
        self.run_picker.clear()
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name FROM control_run ORDER BY id DESC")
        for r_id, r_name in cursor.fetchall():
            self.run_picker.addItem(r_name, r_id)
        self.run_picker.blockSignals(False)
        if self.run_picker.count() > 0:
            self.run_picker.setCurrentIndex(0)
            self.current_run_id = self.run_picker.currentData()
            self._render_matrix_data()

    def _populate_editor_context(self):
        self.edit_suite_picker.clear()
        self.editor_case_list.clear()
        cursor = self.conn.cursor()

        cursor.execute("SELECT id, name FROM control_suite")
        for s_id, s_name in cursor.fetchall():
            self.edit_suite_picker.addItem(s_name, s_id)

        cursor.execute("SELECT id, section, title FROM control_case ORDER BY section, id")
        for c_id, sec, title in cursor.fetchall():
            item = QListWidgetItem(f"[{sec}] {title}")
            item.setData(Qt.UserRole, c_id)
            self.editor_case_list.addItem(item)

    def _populate_manager_run_list(self):
        self.mgr_run_list.clear()
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, created_at FROM control_run ORDER BY id DESC")
        for r_id, name, created_at in cursor.fetchall():
            item = QListWidgetItem(f"{name} (Created: {created_at})")
            item.setData(Qt.UserRole, r_id)
            self.mgr_run_list.addItem(item)

    def _calculate_analytics(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM control_run")
        self.lbl_total_runs.setText(str(cursor.fetchone()[0]))

        cursor.execute("SELECT COUNT(*) FROM control_run_item")
        total_items = cursor.fetchone()[0]
        self.lbl_total_items.setText(str(total_items))

        cursor.execute("SELECT COUNT(*) FROM control_run_item WHERE status = 'passed'")
        passed = cursor.fetchone()[0]
        self.lbl_passed_count.setText(str(passed))

        cursor.execute("SELECT COUNT(*) FROM control_run_item WHERE status = 'failed'")
        failed = cursor.fetchone()[0]
        self.lbl_failed_count.setText(str(failed))

        if total_items > 0:
            pct = ((passed + failed) / total_items) * 100
            self.lbl_completion_rate.setText(f"{pct:.1f}% Processed Status Coverage")
        else:
            self.lbl_completion_rate.setText("0% Base Matrix Load")

    def _handle_run_switch(self):
        self.current_run_id = self.run_picker.currentData()
        self._render_matrix_data()
        self._reset_metadata_form()

    def _render_matrix_data(self):
        self.list_run_items.clear()
        if not self.current_run_id:
            return

        cursor = self.conn.cursor()
        query = """
            SELECT ri.id, tc.section, tc.title, ri.status
            FROM control_run_item ri
            JOIN control_case tc ON ri.case_id = tc.id
            WHERE ri.run_id = ?
            ORDER BY tc.section, tc.id
        """
        cursor.execute(query, (self.current_run_id,))
        for item_id, section, title, status in cursor.fetchall():
            badge = "⚫ UNTESTED"
            if status == "passed": badge = "🟢 PASS"
            elif status == "failed": badge = "❌ FAIL"

            display_text = f"{badge}  |  ({section}) {title}"
            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.UserRole, item_id)
            self.list_run_items.addItem(list_item)

    def _handle_item_click(self, item: QListWidgetItem):
        self.selected_item_id = item.data(Qt.UserRole)
        cursor = self.conn.cursor()
        query = """
            SELECT tc.title, tc.section, tc.preconditions, ri.notes
            FROM control_run_item ri
            JOIN control_case tc ON ri.case_id = tc.id
            WHERE ri.id = ?
        """
        cursor.execute(query, (self.selected_item_id,))
        record = cursor.fetchone()

        if record:
            title, section, preconds, notes = record
            html_content = f"""
            <b style='font-size: 14px;'>Test Case Title:</b><br/>{title}<br/><br/>
            <b>App Section (Workbook Tab):</b> {section}<br/><br/>
            <b>Preconditions Requirements:</b><br/>{preconds if preconds else 'None specified.'}
            """
            self.ui_detail_browser.setHtml(html_content)
            self.ui_notes.setPlainText(notes if notes else "")
            self._refresh_step_list()

    def _refresh_step_list(self):
        self.list_steps.clear()
        if not self.selected_item_id:
            return
        cursor = self.conn.cursor()
        query = """
            SELECT rsi.id, cs.step_number, cs.instruction, cs.expected_result, rsi.status
            FROM control_run_step_item rsi
            JOIN control_case_step cs ON rsi.step_id = cs.id
            WHERE rsi.run_item_id = ?
            ORDER BY cs.step_number ASC
        """
        cursor.execute(query, (self.selected_item_id,))
        for rsi_id, num, inst, expr, status in cursor.fetchall():
            badge = "⚫ UNTESTED"
            if status == 'passed': badge = "🟢 PASS"
            elif status == 'failed': badge = "❌ FAIL"

            lbl = f"Step {num}: {inst}  → Expected: {expr}  [{badge}]"
            step_item = QListWidgetItem(lbl)
            step_item.setData(Qt.UserRole, rsi_id)
            if status == 'passed':
                step_item.setForeground(Qt.darkGreen)
            elif status == 'failed':
                step_item.setForeground(Qt.red)
            self.list_steps.addItem(step_item)

    def _toggle_step_status(self, item: QListWidgetItem):
        rsi_id = item.data(Qt.UserRole)
        cursor = self.conn.cursor()
        cursor.execute("SELECT status FROM control_run_step_item WHERE id = ?", (rsi_id,))
        curr = cursor.fetchone()[0]

        nxt = 'passed' if curr == 'untested' else ('failed' if curr == 'passed' else 'untested')
        cursor.execute("UPDATE control_run_step_item SET status = ? WHERE id = ?", (nxt, rsi_id))
        self.conn.commit()
        self._refresh_step_list()

    def _apply_status_change(self, target_status: str):
        if not self.selected_item_id:
            QMessageBox.warning(self, "Selection Required", "Please select a script row target before updating status.")
            return
        notes_text = self.ui_notes.toPlainText().strip()
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE control_run_item
            SET status = ?, notes = ?, last_updated_at = ?
            WHERE id = ?
        """, (target_status, notes_text, datetime.now(timezone.utc).isoformat(), self.selected_item_id))
        self.conn.commit()
        self._render_matrix_data()
        self._reset_metadata_form()
        self._calculate_analytics()

    def _handle_mgr_run_click(self, item: QListWidgetItem):
        run_id = item.data(Qt.UserRole)
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM control_run WHERE id = ?", (run_id,))
        res = cursor.fetchone()
        if res:
            self.edit_run_name.setText(res[0])

    def _rename_cloned_session(self):
        selected_item = self.mgr_run_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Selection Required", "Select a cloned session from the left list to rename.")
            return
        run_id = selected_item.data(Qt.UserRole)
        new_name = self.edit_run_name.text().strip()
        if not new_name:
            return

        cursor = self.conn.cursor()
        cursor.execute("UPDATE control_run SET name = ? WHERE id = ?", (new_name, run_id))
        self.conn.commit()
        self._refresh_all_contexts()

    def _delete_cloned_session(self):
        selected_item = self.mgr_run_list.currentItem()
        if not selected_item:
            return
        run_id = selected_item.data(Qt.UserRole)

        confirm = QMessageBox.question(self, "Confirm Erasure", "Permanently purge this active execution session run ledger?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM control_run WHERE id = ?", (run_id,))
            self.conn.commit()
            self._refresh_all_contexts()

    def _generate_new_cloned_session(self):
        run_name = self.new_run_name_input.text().strip()
        if not run_name:
            QMessageBox.warning(self, "Input Error", "Please assign an execution session moniker.")
            return

        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM control_case")
        cases = cursor.fetchall()
        if not cases:
            QMessageBox.warning(self, "Empty Database Matrix", "No blueprints exist to copy. Create templates first.")
            return

        cursor.execute("INSERT INTO control_run (name) VALUES (?)", (run_name,))
        new_run_id = cursor.lastrowid

        for (case_id,) in cases:
            cursor.execute("INSERT INTO control_run_item (run_id, case_id, status) VALUES (?, ?, 'untested')", (new_run_id, case_id))
            run_item_id = cursor.lastrowid

            cursor.execute("SELECT id FROM control_case_step WHERE case_id = ?", (case_id,))
            for (step_id,) in cursor.fetchall():
                cursor.execute("INSERT INTO control_run_step_item (run_item_id, step_id, status) VALUES (?, ?, 'untested')", (run_item_id, step_id))

        self.conn.commit()
        self.new_run_name_input.clear()
        self._refresh_all_contexts()
        QMessageBox.information(self, "Session Created", f"Successfully cloned master templates into new session: '{run_name}'")

    def _handle_editor_case_click(self, item: QListWidgetItem):
        self.editor_selected_case_id = item.data(Qt.UserRole)
        cursor = self.conn.cursor()
        cursor.execute("SELECT suite_id, section, title, preconditions FROM control_case WHERE id = ?", (self.editor_selected_case_id,))
        res = cursor.fetchone()
        if res:
            suite_id, section, title, preconds = res
            idx = self.edit_suite_picker.findData(suite_id)
            if idx >= 0: self.edit_suite_picker.setCurrentIndex(idx)
            self.edit_section.setText(section)
            self.edit_title.setText(title)
            self.edit_preconditions.setPlainText(preconds if preconds else "")

    def _save_blueprint_template(self):
        suite_id = self.edit_suite_picker.currentData()
        section = self.edit_section.text().strip() or "General"
        title = self.edit_title.text().strip()
        preconds = self.edit_preconditions.toPlainText().strip()
        step_inst = self.edit_step_instruction.text().strip()
        step_expr = self.edit_step_expected.text().strip()

        if not title:
            QMessageBox.warning(self, "Validation Error", "Blueprint case title is required.")
            return

        cursor = self.conn.cursor()
        if self.editor_selected_case_id:
            cursor.execute("""
                UPDATE control_case SET suite_id = ?, section = ?, title = ?, preconditions = ? WHERE id = ?
            """, (suite_id, section, title, preconds, self.editor_selected_case_id))
            case_id = self.editor_selected_case_id
        else:
            cursor.execute("""
                INSERT INTO control_case (suite_id, section, title, preconditions) VALUES (?, ?, ?, ?)
            """, (suite_id, section, title, preconds))
            case_id = cursor.lastrowid

        if step_inst and step_expr:
            cursor.execute("""
                INSERT INTO control_case_step (case_id, step_number, instruction, expected_result) VALUES (?, 1, ?, ?)
            """, (case_id, step_inst, step_expr))

        self.conn.commit()
        self._refresh_all_contexts()
        QMessageBox.information(self, "Success", "Master blueprint specs updated successfully.")

    def _delete_current_blueprint(self):
        if not self.editor_selected_case_id:
            QMessageBox.warning(self, "Selection Required", "Select a template case file context to delete.")
            return
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM control_case WHERE id = ?", (self.editor_selected_case_id,))
        self.conn.commit()
        self.editor_selected_case_id = None
        self._refresh_all_contexts()

    def _reset_metadata_form(self):
        self.selected_item_id = None
        self.ui_detail_browser.setHtml("<p style='color: gray;'>Select a test item from the list to view its specification context.</p>")
        self.ui_notes.clear()
        self.list_steps.clear()
