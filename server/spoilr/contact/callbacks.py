from spoilr.core.api.events import HuntEvent, register


def on_contact_requested(team, contact_request, **kwargs):
    from spoilr.hq.models import Task

    contact_request.tasks.add(Task(), bulk=False)


register(HuntEvent.CONTACT_REQUESTED, on_contact_requested)
