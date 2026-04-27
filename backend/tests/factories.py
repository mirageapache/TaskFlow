# Phase 1 骨架 — 各 Factory 隨對應 Model 實作後逐步啟用
# 完整規格見 .doc/taskflow-testing.md §1.4
from faker import Faker

fake = Faker('zh_TW')

# TODO: Phase 1 TDD — 實作 User Model 後取消以下註解
# import factory
# from factory.django import DjangoModelFactory
# from apps.users.models import User, UserSocialAccount
# from apps.workspaces.models import Workspace, WorkspaceMember
# from apps.projects.models import Project, ProjectStatus, ProjectMember
# from apps.tasks.models import Task, Tag
#
# class UserFactory(DjangoModelFactory):
#     class Meta:
#         model = User
#     email    = factory.Sequence(lambda n: f'user{n}@example.com')
#     username = factory.Sequence(lambda n: f'user{n}')
#     password = factory.PostGenerationMethodCall('set_password', 'testpass123')
#
# class WorkspaceFactory(DjangoModelFactory):
#     class Meta:
#         model = Workspace
#     name  = factory.Faker('company', locale='zh_TW')
#     owner = factory.SubFactory(UserFactory)
#
# class WorkspaceMemberFactory(DjangoModelFactory):
#     class Meta:
#         model = WorkspaceMember
#     workspace = factory.SubFactory(WorkspaceFactory)
#     user      = factory.SubFactory(UserFactory)
#     role      = WorkspaceMember.Role.MEMBER
#
# class ProjectFactory(DjangoModelFactory):
#     class Meta:
#         model = Project
#     workspace = factory.SubFactory(WorkspaceFactory)
#     name      = factory.Faker('bs', locale='zh_TW')
#
# class ProjectStatusFactory(DjangoModelFactory):
#     class Meta:
#         model = ProjectStatus
#     project      = factory.SubFactory(ProjectFactory)
#     name         = '待處理'
#     order        = factory.Sequence(lambda n: n)
#     is_completed = False
#
# class TagFactory(DjangoModelFactory):
#     class Meta:
#         model = Tag
#     workspace = factory.SubFactory(WorkspaceFactory)
#     name      = factory.Sequence(lambda n: f'標籤{n}')
#     color     = '#94a3b8'
#
# class ProjectMemberFactory(DjangoModelFactory):
#     class Meta:
#         model = ProjectMember
#     project = factory.SubFactory(ProjectFactory)
#     user    = factory.SubFactory(UserFactory)
#     role    = ProjectMember.Role.MEMBER
#
# class UserSocialAccountFactory(DjangoModelFactory):
#     class Meta:
#         model = UserSocialAccount
#     user             = factory.SubFactory(UserFactory)
#     provider         = 'google'
#     provider_user_id = factory.Sequence(lambda n: f'google_uid_{n}')
#
# class TaskFactory(DjangoModelFactory):
#     class Meta:
#         model = Task
#     project  = factory.SubFactory(ProjectFactory)
#     status   = factory.SubFactory(ProjectStatusFactory)
#     title    = factory.Faker('sentence', nb_words=4, locale='zh_TW')
#     priority = Task.Priority.MEDIUM
