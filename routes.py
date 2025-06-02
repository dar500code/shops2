from flask import redirect, url_for
from flask_login import login_required, current_user

@app.route('/checkout')
@login_required
def checkout():
    if not current_user.is_authenticated:
        return redirect(url_for('login', next=url_for('checkout')))
    # ... rest of checkout logic ...
