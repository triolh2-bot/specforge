from ..extensions import db
from ..models import Workspace, WorkspaceSubscription


def create_workspace(name="Personal Workspace"):
    workspace = Workspace(name=name)
    db.session.add(workspace)
    db.session.commit()
    return workspace


def get_workspace(workspace_id):
    return db.session.get(Workspace, workspace_id)


def get_workspace_subscription(workspace_id):
    return WorkspaceSubscription.query.filter_by(workspace_id=workspace_id).first()


def upsert_workspace_subscription(workspace_id, plan, provider=None, provider_subscription_id=None, status="active"):
    sub = get_workspace_subscription(workspace_id)
    if sub is None:
        sub = WorkspaceSubscription(workspace_id=workspace_id)
        db.session.add(sub)
    sub.plan = plan
    sub.provider = provider
    sub.provider_subscription_id = provider_subscription_id
    sub.status = status
    db.session.commit()
    return sub
