import json
import os
import datetime as dt
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

# load .env
load_dotenv()

app = Flask(__name__, instance_relative_config=True)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'hackhub.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-me')

os.makedirs(app.instance_path, exist_ok=True)

db = SQLAlchemy(app)


class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)

    # Core fields
    start_dt = db.Column(db.String(40))  # ISO string for simplicity
    end_dt = db.Column(db.String(40))
    reg_deadline = db.Column(db.String(40))
    team_min = db.Column(db.Integer)
    team_max = db.Column(db.Integer)
    intercollege = db.Column(db.Boolean, default=False)
    interdepartment = db.Column(db.Boolean, default=False)
    interyear = db.Column(db.Boolean, default=False)
    mode = db.Column(db.String(20))  # online/offline/hybrid
    venue = db.Column(db.String(300))  # if offline
    rounds_json = db.Column(db.Text)  # list of {name,date,time,venue,desc}
    description = db.Column(db.Text)
    levels_json = db.Column(db.Text)  # optional detailed levels
    sponsor = db.Column(db.String(200))
    organizer = db.Column(db.String(200))
    extra_json = db.Column(db.Text)  # arbitrary key-value
    status = db.Column(db.String(20), default='approved')  # approved | pending
    submitted_by = db.Column(db.String(20), default='admin')  # admin | user
    created_at = db.Column(db.DateTime, default=dt.datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'start_dt': self.start_dt,
            'end_dt': self.end_dt,
            'reg_deadline': self.reg_deadline,
            'team_min': self.team_min,
            'team_max': self.team_max,
            'intercollege': bool(self.intercollege),
            'interdepartment': bool(self.interdepartment),
            'interyear': bool(self.interyear),
            'mode': self.mode,
            'venue': self.venue,
            'rounds': json.loads(self.rounds_json or '[]'),
            'description': self.description,
            'levels': json.loads(self.levels_json or '[]'),
            'sponsor': self.sponsor,
            'organizer': self.organizer,
            'extra': json.loads(self.extra_json or '{}'),
            'status': self.status,
            'submitted_by': self.submitted_by,
            'created_at': (self.created_at.isoformat() + 'Z') if self.created_at else None,
        }


ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'changeme')
# allow hash or plain (if you set a hash, prefix with 'pbkdf2:' or 'scrypt:')
if not (ADMIN_PASSWORD.startswith('pbkdf2:') or ADMIN_PASSWORD.startswith('scrypt:')):
    ADMIN_PASSWORD_HASH = generate_password_hash(ADMIN_PASSWORD)
else:
    ADMIN_PASSWORD_HASH = ADMIN_PASSWORD


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('admin'):  # stores username
            flash('Please log in as admin.', 'warning')
            return redirect(url_for('login', next=request.path))
        return view(*args, **kwargs)
    return wrapped


# --- Routes: Public ------------------------------------------------------
@app.route('/')
def index():
    q = request.args.get('q', '').strip()
    mode = request.args.get('mode', '')
    intercollege = request.args.get('intercollege', '')
    date_from = request.args.get('from', '')
    date_to = request.args.get('to', '')

    events = Event.query.filter_by(status='approved').order_by(Event.created_at.desc()).all()

    def matches(e: Event):
        d = e.to_dict()
        text = (d['title'] or '') + ' ' + (d['description'] or '') + ' ' + (d.get('organizer') or '')
        ok = True
        if q:
            ok &= q.lower() in text.lower()
        if mode:
            ok &= (d['mode'] or '').lower() == mode.lower()
        if intercollege:
            ok &= ((d['intercollege'] is True) if intercollege == 'yes' else (d['intercollege'] is False))
        # simple date filtering by start_dt as ISO-ish strings
        if date_from:
            ok &= (d.get('start_dt') or '') >= date_from
        if date_to:
            ok &= (d.get('end_dt') or d.get('start_dt') or '') <= date_to
        return ok

    filtered = [e.to_dict() for e in events if matches(e)]
    return render_template('index.html', events=filtered,
                           query={'q': q, 'mode': mode, 'intercollege': intercollege, 'from': date_from, 'to': date_to})


@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if request.method == 'POST':
        payload = _parse_event_form(request)
        ev = Event(**payload)
        ev.status = 'pending'
        ev.submitted_by = 'user'
        db.session.add(ev)
        db.session.commit()
        flash('Thanks! Your event was submitted for review.', 'success')
        return redirect(url_for('index'))
    return render_template('submit.html')


@app.route('/api/events')
def api_events():
    items = [e.to_dict() for e in Event.query.filter_by(status='approved').all()]
    return jsonify(items)


# --- Routes: Auth + Admin -----------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin'] = username
            flash('Welcome, admin.', 'success')
            return redirect(request.args.get('next') or url_for('admin_add'))
        flash('Invalid credentials.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/admin/add', methods=['GET', 'POST'])
@login_required
def admin_add():
    if request.method == 'POST':
        payload = _parse_event_form(request)
        ev = Event(**payload)
        ev.status = 'approved'
        ev.submitted_by = 'admin'
        db.session.add(ev)
        db.session.commit()
        flash('Event added.', 'success')
        return redirect(url_for('index'))
    return render_template('admin_add.html')


@app.route('/admin/review')
@login_required
def review():
    pendings = [e.to_dict() for e in Event.query.filter_by(status='pending').order_by(Event.created_at.desc()).all()]
    return render_template('review.html', pendings=pendings)


@app.post('/admin/approve/<int:event_id>')
@login_required
def approve(event_id):
    ev = Event.query.get_or_404(event_id)
    ev.status = 'approved'
    db.session.commit()
    flash('Event approved.', 'success')
    return redirect(url_for('review'))


@app.post('/admin/reject/<int:event_id>')
@login_required
def reject(event_id):
    ev = Event.query.get_or_404(event_id)
    db.session.delete(ev)
    db.session.commit()
    flash('Event rejected & removed.', 'warning')
    return redirect(url_for('review'))


# --- Helpers -------------------------------------------------------------
def _parse_event_form(req):
    title = req.form.get('title', '').strip()
    start_dt = req.form.get('start_dt') or ''
    end_dt = req.form.get('end_dt') or ''
    reg_deadline = req.form.get('reg_deadline') or ''
    try:
        team_min = int(req.form.get('team_min') or 0)
    except ValueError:
        team_min = 0
    try:
        team_max = int(req.form.get('team_max') or 0)
    except ValueError:
        team_max = 0

    intercollege = req.form.get('intercollege') == 'on'
    interdepartment = req.form.get('interdepartment') == 'on'
    interyear = req.form.get('interyear') == 'on'
    mode = req.form.get('mode') or ''
    venue = req.form.get('venue') or ''

    description = req.form.get('description') or ''
    sponsor = req.form.get('sponsor') or ''
    organizer = req.form.get('organizer') or ''

    # rounds & levels & extra are posted as JSON via hidden inputs
    rounds = req.form.get('rounds_json') or '[]'
    levels = req.form.get('levels_json') or '[]'
    extra = req.form.get('extra_json') or '{}'

    # ensure valid JSON strings
    try:
        json.loads(rounds)
    except Exception:
        rounds = '[]'
    try:
        json.loads(levels)
    except Exception:
        levels = '[]'
    try:
        json.loads(extra)
    except Exception:
        extra = '{}'

    return dict(
        title=title,
        start_dt=start_dt,
        end_dt=end_dt,
        reg_deadline=reg_deadline,
        team_min=team_min,
        team_max=team_max,
        intercollege=intercollege,
        interdepartment=interdepartment,
        interyear=interyear,
        mode=mode,
        venue=venue,
        rounds_json=rounds,
        description=description,
        levels_json=levels,
        sponsor=sponsor,
        organizer=organizer,
        extra_json=extra,
    )


# CLI helper to create DB
@app.cli.command('init-db')
def init_db_cmd():
    db.create_all()
    print('Database initialized at', app.config['SQLALCHEMY_DATABASE_URI'])


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
