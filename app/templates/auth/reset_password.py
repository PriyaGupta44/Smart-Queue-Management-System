<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset Password — Queue Management System</title>

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">

    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/navbar.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/login.css') }}">
</head>
<body>

    <header class="navbar">
        <div class="container nav-container">
            <a href="/" class="logo">Queue<span>Flow</span></a>
            <nav>
                <ul class="nav-links">
                    <li><a href="{{ url_for('main.home') }}">Home</a></li>
                    <li><a href="{{ url_for('main.about') }}">About</a></li>
                    <li><a href="{{ url_for('main.services') }}">Services</a></li>
                    <li><a href="{{ url_for('main.contact') }}">Contact</a></li>
                </ul>
            </nav>
            <div class="nav-buttons">
                <a href="{{ url_for('auth.login') }}" class="btn btn-primary">Login</a>
                <a href="{{ url_for('auth.register') }}" class="btn btn-outline">Register</a>
            </div>
        </div>
    </header>

    <section class="login-page">
        <div class="login-wrapper" style="justify-content:center;">
            <div class="login-card">
                <h2>Reset Your Password</h2>
                <p class="subtitle">Choose a new password below.</p>

                <form method="POST" action="{{ url_for('auth.reset_password', token=request.view_args['token']) }}">
                    {{ form.hidden_tag() }}

                    {% with messages = get_flashed_messages(with_categories=true) %}
                        {% if messages %}
                            {% for category, message in messages %}
                                <p class="flash flash-{{ category }}">{{ message }}</p>
                            {% endfor %}
                        {% endif %}
                    {% endwith %}

                    <div class="input-box">
                        <i class="fa-solid fa-lock"></i>
                        {{ form.password(placeholder="New Password") }}
                    </div>
                    {% for error in form.password.errors %}<p class="flash flash-danger">{{ error }}</p>{% endfor %}

                    <div class="input-box">
                        <i class="fa-solid fa-lock"></i>
                        {{ form.confirm_password(placeholder="Confirm New Password") }}
                    </div>
                    {% for error in form.confirm_password.errors %}<p class="flash flash-danger">{{ error }}</p>{% endfor %}

                    {{ form.submit(class="btn") }}
                </form>
            </div>
        </div>
    </section>

</body>
</html>