from app.extensions import login_manager
from app.models.student import Student


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login calls this on every request to reload the logged-in
    user from the ID stored in their session cookie."""
    return Student.query.get(int(user_id))