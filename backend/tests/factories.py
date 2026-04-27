import factory
from factory.django import DjangoModelFactory
from faker import Faker

from apps.users.models import User, UserSocialAccount

fake = Faker('zh_TW')


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f'user{n}@example.com')
    username = factory.Sequence(lambda n: f'user{n}')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')


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


from apps.projects.models import Project, ProjectStatus, ProjectMember


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


# TODO: Phase 1 TDD — 實作 Task Model 後啟用
# from apps.tasks.models import Task, Tag
#
# class TagFactory(DjangoModelFactory): ...
# class TaskFactory(DjangoModelFactory): ...
