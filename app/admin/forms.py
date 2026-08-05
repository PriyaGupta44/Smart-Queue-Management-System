from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length

from app.auth.forms import validate_password_strength


class AddStudentForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email Address", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField(
        "Temporary Password", validators=[DataRequired(), Length(min=8), validate_password_strength]
    )
    submit = SubmitField("Add Student")