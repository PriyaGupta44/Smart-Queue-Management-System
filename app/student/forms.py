from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo

from app.auth.forms import validate_password_strength


class ProfileForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    submit = SubmitField("Save Changes")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField(
        "New Password", validators=[DataRequired(), Length(min=8), validate_password_strength]
    )
    confirm_new_password = PasswordField(
        "Confirm New Password",
        validators=[DataRequired(), EqualTo("new_password", message="Passwords must match.")],
    )
    submit = SubmitField("Change Password")