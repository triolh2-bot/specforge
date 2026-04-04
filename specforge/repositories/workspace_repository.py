from ..extensions import db
from ..models import Workspace


def create_workspace(name="Personal Workspace"):
    workspace = Workspace(name=name)
    db.session.add(workspace)
    db.session.commit()
    return workspace


def get_workspace(workspace_id):
    return db.session.get(Workspace, workspace_id)
