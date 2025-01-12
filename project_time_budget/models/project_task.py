# © 2018 Numigi (tm) and all its contributors (https://bit.ly/numigiens)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, models

ADDED = "added"
MODIFIED = "modified"
DELETED = "deleted"
REMOVED = "removed"
ARCHIVED = "archived"
RESTORED = "restored"


class ProjectTask(models.Model):
    _inherit = "project.task"

    @api.model
    def create(self, vals):
        res = super().create(vals)
        res._project_budget_log_required()._notify_template_task_added()
        return res

    @api.multi
    def write(self, vals):
        changing_project = "project_id" in vals
        if changing_project:
            added_tasks = self._project_budget_log_required().filtered(
                lambda r: r.project_id.id != vals["project_id"]
            )
            removed_tasks = [(t.project_id, t) for t in added_tasks]

        archiving = "active" in vals and not vals["active"]
        if archiving:
            archived_tasks = self.filtered("active")

        restoring = vals.get("active")
        if restoring:
            restored_tasks = self.filtered(lambda t: not t.active)

        changing_estimates = (
            "min_hours" in vals or "planned_hours" in vals or "max_hours" in vals
        )

        res = super(ProjectTask, self).write(vals)

        if changing_project:
            for project, task in removed_tasks:
                task._notify_template_task_removed_from(project)

            added_tasks._notify_template_task_added()

        elif changing_estimates:
            self._project_budget_log_required()._notify_template_task_modified()

        elif archiving:
            archived_tasks._project_budget_log_required()._notify_template_task_archived()

        elif restoring:
            restored_tasks._project_budget_log_required()._notify_template_task_restored()

        return res

    @api.multi
    def unlink(self):
        deleted_tasks = [(t.project_id, t) for t in self._project_budget_log_required()]
        res = super().unlink()
        for project, task in deleted_tasks:
            task._notify_template_task_deleted(project)
        return res

    def _notify_template_task_added(self):
        for task in self:
            task._notify_template_task_changed_to_project(ADDED, task.project_id)

    def _notify_template_task_modified(self):
        for task in self:
            task._notify_template_task_changed_to_project(MODIFIED, task.project_id)

    def _notify_template_task_deleted(self, project):
        for task in self:
            task._notify_template_task_changed_to_project(DELETED, project)

    def _notify_template_task_removed_from(self, project):
        for task in self:
            task._notify_template_task_changed_to_project(REMOVED, project)

    def _notify_template_task_archived(self):
        for task in self:
            task._notify_template_task_changed_to_project(ARCHIVED, task.project_id)

    def _notify_template_task_restored(self):
        for task in self:
            task._notify_template_task_changed_to_project(RESTORED, task.project_id)

    def _notify_template_task_changed_to_project(self, action, project):
        message_template = _(
            """
            <b>{action}</b>
            <ul>
                <li>Min: {min}</li>
                <li>Ideal: {ideal}</li>
                <li>Max: {max}</li>
            </ul>
        """
        )
        message = message_template.format(
            action=self._format_template_task_action(action),
            min=format_float_time(project.budget_min_hours),
            ideal=format_float_time(project.budget_planned_hours),
            max=format_float_time(project.budget_max_hours),
        )
        project.message_post(body=message)

    def _project_budget_log_required(self):
        return self.filtered(lambda r: r.is_template and r.project_id)

    def _format_template_task_action(self, action):
        if action == ADDED:
            message = _("Task template #{} added")
        elif action == MODIFIED:
            message = _("Task template #{} modified")
        elif action == REMOVED:
            message = _("Task template #{} removed from the project")
        elif action == ARCHIVED:
            message = _("Task template #{} archived")
        elif action == RESTORED:
            message = _("Task template #{} restored")
        else:
            message = _("Task template #{} deleted")
        return message.format(self.id)


def format_float_time(value):
    """Format a float into an hh:mm representation.

    Extracted from odoo/addons/base/models/ir_qweb_fields.py
    """
    hours, minutes = divmod(abs(value) * 60, 60)
    minutes = round(minutes)
    if minutes == 60:
        minutes = 0
        hours += 1
    if value < 0:
        return "-%02d:%02d" % (hours, minutes)
    return "%02d:%02d" % (hours, minutes)
