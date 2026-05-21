import datetime

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory
from faker import Faker

from apps.users.models import User, UserSocialAccount

fake = Faker('zh_TW')


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f'user{n}@example.com')
    username = factory.Sequence(lambda n: f'user{n}')

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop('password', 'testpass123')
        user = model_class(*args, **kwargs)
        user.set_password(password)
        user.save()
        return user


class UserSocialAccountFactory(DjangoModelFactory):
    class Meta:
        model = UserSocialAccount

    user = factory.SubFactory(UserFactory)
    provider = 'google'
    provider_user_id = factory.Sequence(lambda n: f'google_uid_{n}')


from apps.workspaces.models import Workspace, WorkspaceMember


class WorkspaceFactory(DjangoModelFactory):
    class Meta:
        model = Workspace

    name = factory.Faker('company', locale='zh_TW')
    owner = factory.SubFactory(UserFactory)


class WorkspaceMemberFactory(DjangoModelFactory):
    class Meta:
        model = WorkspaceMember

    workspace = factory.SubFactory(WorkspaceFactory)
    user = factory.SubFactory(UserFactory)
    role = WorkspaceMember.Role.MEMBER


from apps.projects.models import Project, ProjectMember, ProjectStatus


class ProjectFactory(DjangoModelFactory):
    class Meta:
        model = Project

    workspace = factory.SubFactory(WorkspaceFactory)
    name = factory.Faker('bs', locale='zh_TW')
    description = ''
    color = '#6366f1'


class ProjectStatusFactory(DjangoModelFactory):
    class Meta:
        model = ProjectStatus

    project = factory.SubFactory(ProjectFactory)
    name = factory.Sequence(lambda n: f'Status {n}')
    order = factory.Sequence(lambda n: n)


class ProjectMemberFactory(DjangoModelFactory):
    class Meta:
        model = ProjectMember

    project = factory.SubFactory(ProjectFactory)
    user = factory.SubFactory(UserFactory)
    role = ProjectMember.Role.MEMBER


from apps.tasks.models import Tag, Task


class TagFactory(DjangoModelFactory):
    class Meta:
        model = Tag

    workspace = factory.SubFactory(WorkspaceFactory)
    name = factory.Sequence(lambda n: f'tag-{n}')
    color = '#94a3b8'


class TaskFactory(DjangoModelFactory):
    class Meta:
        model = Task

    project = factory.SubFactory(ProjectFactory)
    status = factory.SubFactory(ProjectStatusFactory, project=factory.SelfAttribute('..project'))
    creator = factory.SubFactory(UserFactory)
    title = factory.Sequence(lambda n: f'Task {n}')


# ────────────────  Calendar Events ────────────────


from apps.calendar_events.models import Event


class EventFactory(DjangoModelFactory):
    class Meta:
        model = Event

    workspace = factory.SubFactory(WorkspaceFactory)
    creator = factory.SubFactory(UserFactory)
    title = factory.Sequence(lambda n: f'Event {n}')
    description = ''
    start_at = factory.LazyFunction(timezone.now)
    end_at = factory.LazyAttribute(
        lambda obj: obj.start_at + datetime.timedelta(hours=1),
    )
    is_all_day = False
    recurrence_rule = ''


# ────────────────  Notifications ────────────────


from apps.notifications.models import Notification


class NotificationFactory(DjangoModelFactory):
    class Meta:
        model = Notification

    recipient = factory.SubFactory(UserFactory)
    notif_type = Notification.NotifType.TASK_ASSIGNED
    title = factory.Sequence(lambda n: f'Notif {n}')
    body = ''
    payload = {}
    is_read = False
