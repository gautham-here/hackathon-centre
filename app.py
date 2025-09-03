import json
import os
import datetime as dt
from functools import wraps

from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

# Load environment variables from .env (if present)
load_dotenv()

app = Flask(__name__, instance_relative_config=True)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'hackhub.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-me')

# ensure instance folder exists
os.makedirs(app.instance_path, exist_ok=True)
db = SQLAlchemy(app)

# ---------- Domains (50+ common domains + general) ----------
DOMAINS = [
    "Algorithms", "AI/ML", "Deep Learning", "NLP", "Computer Vision", "Robotics", "IoT", "Embedded Systems",
    "Blockchain", "Cybersecurity", "Data Science", "Databases", "Cloud Computing", "DevOps", "Mobile Apps",
    "Web Development", "Fullstack", "Frontend", "Backend", "AR/VR", "Game Dev", "Human-Computer Interaction",
    "Computer Graphics", "Operating Systems", "Distributed Systems", "Parallel Computing", "High Performance Computing",
    "Signal Processing", "Image Processing", "Optimization", "Reinforcement Learning", "Bioinformatics",
    "Natural Sciences", "Electronics", "VLSI", "Control Systems", "Power Systems", "CAD/CAE", "Automation",
    "Mechanical Design", "Civil/Infrastructure", "AgriTech", "FinTech", "HealthTech", "EdTech", "E-commerce",
    "Social Good", "Sustainability", "ClimateTech", "Other"
]

# ---------- Event model ----------
class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)

    # Basic
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)

    # Dates (store ISO-ish strings from datetime-local inputs)
    start_dt = db.Column(db.String(40), nullable=False)
    end_dt = db.Column(db.String(40), nullable=False)
    reg_deadline = db.Column(db.String(40), nullable=False)
    reg_open = db.Column(db.String(40), default='')  # optional registration opens date

    # team and eligibility
    team_min = db.Column(db.Integer)
    team_max = db.Column(db.Integer)
    team_status = db.Column(db.String(30))  # e.g., 'Not sure' or explicit

    # membership flags (allow: yes/no/not sure)
    intercollege = db.Column(db.String(30))
    interdepartment = db.Column(db.String(30))
    interyear = db.Column(db.String(30))

    # mode & accommodation & venue
    mode = db.Column(db.String(30))
    venue = db.Column(db.String(300))
    accommodation = db.Column(db.String(30))  # Yes | No | To be confirmed

    # rounds / levels / problems
    rounds_json = db.Column(db.Text)
    levels_json = db.Column(db.Text)
    problems_json = db.Column(db.Text)

    # sponsors, organizer, prize, fee, eligibility, extra
    sponsor = db.Column(db.String(200))
    organizer = db.Column(db.String(200))
    prize = db.Column(db.String(100))    # keep as string (₹50,000 or TBA)
    fee = db.Column(db.String(100))      # string (Free or ₹500)
    eligibility = db.Column(db.Text)
    extra_json = db.Column(db.Text)

    # domains & meta
    domains_json = db.Column(db.Text)
    upvotes = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='approved')  # approved | pending
    submitted_by = db.Column(db.String(30), default='admin')  # admin | user
    created_at = db.Column(db.DateTime, default=dt.datetime.utcnow)

    def to_dict(self):
        # Safe JSON parsing helpers
        def _loads(s, default):
            try:
                return json.loads(s) if s else default
            except Exception:
                return default

        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'start_dt': self.start_dt,
            'end_dt': self.end_dt,
            'reg_deadline': self.reg_deadline,
            'reg_open': self.reg_open,
            'team_min': self.team_min,
            'team_max': self.team_max,
            'team_status': self.team_status,
            'intercollege': self.intercollege,
            'interdepartment': self.interdepartment,
            'interyear': self.interyear,
            'mode': self.mode,
            'venue': self.venue,
            'accommodation': self.accommodation,
            'rounds': _loads(self.rounds_json, []),
            'levels': _loads(self.levels_json, []),
            'problems': _loads(self.problems_json, []),
            'sponsor': self.sponsor,
            'organizer': self.organizer,
            'prize': self.prize,
            'fee': self.fee,
            'eligibility': self.eligibility,
            'extra': _loads(self.extra_json, {}),
            'domains': _loads(self.domains_json, []),
            'upvotes': int(self.upvotes or 0),
            'status': self.status,
            'submitted_by': self.submitted_by,
            'created_at': (self.created_at.isoformat() + 'Z') if self.created_at else None,
        }

# ---------- Auth ----------
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'changeme')
if not (ADMIN_PASSWORD.startswith('pbkdf2:') or ADMIN_PASSWORD.startswith('scrypt:')):
    ADMIN_PASSWORD_HASH = generate_password_hash(ADMIN_PASSWORD)
else:
    ADMIN_PASSWORD_HASH = ADMIN_PASSWORD


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('admin'):
            flash('Please log in as admin.', 'warning')
            return redirect(url_for('login', next=request.path))
        return view(*args, **kwargs)
    return wrapped


# ---------- Utilities ----------
def parse_iso(s):
    if not s:
        return None
    try:
        # accept YYYY-MM-DD or YYYY-MM-DDTHH:MM
        return dt.datetime.fromisoformat(s)
    except Exception:
        return None


def is_registration_open(ev: Event):
    now = dt.datetime.utcnow()
    # if reg_open present, ensure now >= reg_open and now <= reg_deadline
    open_dt = parse_iso(ev.reg_open) if getattr(ev, 'reg_open', None) else None
    deadline = parse_iso(ev.reg_deadline)
    if not deadline:
        return False
    if open_dt:
        return open_dt <= now <= deadline
    return now <= deadline


# ---------- Routes: Public ----------
@app.route('/')
def home():
    q = request.args.get('q', '').strip()
    mode = request.args.get('mode', '')  # online/offline/hybrid
    reg_status = request.args.get('reg_status', '')  # open | closed | any
    domain_filters = request.args.getlist('domain')  # multi-select
    eligibility_q = request.args.get('eligibility', '').strip()
    intercollege = request.args.get('intercollege', '')
    sort_by = request.args.get('sort', '')  # prize | fee | deadline | start

    events = Event.query.filter_by(status='approved').order_by(Event.created_at.desc()).all()

    def matches(e: Event):
        d = e.to_dict()
        ok = True
        if q:
            txt = (d['title'] or '') + ' ' + (d['description'] or '') + ' ' + (d.get('organizer') or '')
            ok &= q.lower() in txt.lower()
        if mode:
            ok &= (d['mode'] or '').lower() == mode.lower()
        if intercollege:
            ok &= (d['intercollege'] or '').lower() == intercollege.lower()
        if domain_filters:
            ev_domains = [s.lower() for s in d.get('domains', [])]
            ok &= any(dom.lower() in ev_domains for dom in domain_filters)
        if eligibility_q:
            ok &= eligibility_q.lower() in (d.get('eligibility') or '').lower()
        if reg_status == 'open':
            ev_obj = Event.query.get(d['id'])
            ok &= is_registration_open(ev_obj)
        if reg_status == 'closed':
            ev_obj = Event.query.get(d['id'])
            ok &= not is_registration_open(ev_obj)
        return ok

    filtered = [e.to_dict() for e in events if matches(e)]

    # simple sorting heuristics: prize & fee are strings; try numeric extraction
    def numeric_from_string(s):
        if not s:
            return 0
        import re
        m = re.search(r'(\d[\d,]*)', s.replace(',', ''))
        if m:
            try:
                return int(m.group(1).replace(',', ''))
            except:
                return 0
        return 0

    if sort_by == 'prize':
        filtered.sort(key=lambda x: numeric_from_string(x.get('prize')), reverse=True)
    elif sort_by == 'fee':
        filtered.sort(key=lambda x: numeric_from_string(x.get('fee')), reverse=False)
    elif sort_by == 'deadline':
        filtered.sort(key=lambda x: x.get('reg_deadline') or '')
    elif sort_by == 'start':
        filtered.sort(key=lambda x: x.get('start_dt') or '')

    # Pass a safe query dict so templates referencing 'query' won't error
    query_dict = {
        'q': q, 'mode': mode, 'reg_status': reg_status, 'domains': domain_filters,
        'eligibility': eligibility_q, 'intercollege': intercollege, 'sort': sort_by
    }

    return render_template('home.html', events=filtered, query=query_dict, DOMAINS=DOMAINS)


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
        return redirect(url_for('home'))
    # pass query and DOMAINS so base.html and form partials are happy
    return render_template('submit.html', DOMAINS=DOMAINS, query={})


@app.post('/vote/<int:event_id>')
def vote(event_id):
    ev = Event.query.get_or_404(event_id)
    voted = session.get('voted_events', [])
    if event_id in voted:
        return jsonify({'ok': False, 'message': 'Already voted'}), 400
    ev.upvotes = (ev.upvotes or 0) + 1
    db.session.commit()
    voted.append(event_id)
    session['voted_events'] = voted
    return jsonify({'ok': True, 'upvotes': ev.upvotes})


@app.route('/api/events')
def api_events():
    items = [e.to_dict() for e in Event.query.filter_by(status='approved').all()]
    return jsonify(items)


# ---------- Auth + Admin ----------
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
    # pass an empty query dict (templates expect 'query')
    return render_template('login.html', query={})


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('home'))


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
        return redirect(url_for('home'))
    # include DOMAINS and a safe query dict
    return render_template('admin_add.html', DOMAINS=DOMAINS, query={})


@app.route('/admin/edit/<int:event_id>', methods=['GET', 'POST'])
@login_required
def admin_edit(event_id):
    ev = Event.query.get_or_404(event_id)
    if request.method == 'POST':
        payload = _parse_event_form(request)
        # update fields
        for k, v in payload.items():
            setattr(ev, k, v)
        db.session.commit()
        flash('Event updated.', 'success')
        return redirect(url_for('review'))
    # prefill form: convert event fields to simple values for template
    data = ev.to_dict()
    # pass DOMAINS and query so no template errors
    return render_template('admin_edit.html', event=data, DOMAINS=DOMAINS, query={})


@app.route('/admin/review')
@login_required
def review():
    pendings = [e.to_dict() for e in Event.query.filter_by(status='pending').order_by(Event.created_at.desc()).all()]
    return render_template('review.html', pendings=pendings, DOMAINS=DOMAINS, query={})


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


# ---------- Helpers ----------
def _parse_event_form(req):
    title = req.form.get('title', '').strip()
    description = req.form.get('description', '').strip()
    start_dt = req.form.get('start_dt') or ''
    end_dt = req.form.get('end_dt') or ''
    reg_deadline = req.form.get('reg_deadline') or ''
    reg_open = req.form.get('reg_open') or ''

    # team
    try:
        team_min = int(req.form.get('team_min') or 0)
    except:
        team_min = 0
    try:
        team_max = int(req.form.get('team_max') or 0)
    except:
        team_max = 0
    team_status = req.form.get('team_status') or 'Not sure'

    intercollege = req.form.get('intercollege') or 'Not sure'
    interdepartment = req.form.get('interdepartment') or 'Not sure'
    interyear = req.form.get('interyear') or 'Not sure'

    mode = req.form.get('mode') or 'Not sure'
    venue = req.form.get('venue') or ''
    accommodation = req.form.get('accommodation') or ''

    sponsor = req.form.get('sponsor') or ''
    organizer = req.form.get('organizer') or ''
    prize = req.form.get('prize') or ''
    fee = req.form.get('fee') or ''
    eligibility = req.form.get('eligibility') or ''

    # arrays posted as JSON from front-end
    rounds = req.form.get('rounds_json') or '[]'
    levels = req.form.get('levels_json') or '[]'
    problems = req.form.get('problems_json') or '[]'
    extra = req.form.get('extra_json') or '{}'
    domains = req.form.get('domains_json') or '[]'

    # ensure valid JSON
    try:
        json.loads(rounds)
    except:
        rounds = '[]'
    try:
        json.loads(levels)
    except:
        levels = '[]'
    try:
        json.loads(problems)
    except:
        problems = '[]'
    try:
        json.loads(extra)
    except:
        extra = '{}'
    try:
        json.loads(domains)
    except:
        domains = '[]'

    return dict(
        title=title,
        description=description,
        start_dt=start_dt,
        end_dt=end_dt,
        reg_deadline=reg_deadline,
        reg_open=reg_open,
        team_min=team_min,
        team_max=team_max,
        team_status=team_status,
        intercollege=intercollege,
        interdepartment=interdepartment,
        interyear=interyear,
        mode=mode,
        venue=venue,
        accommodation=accommodation,
        rounds_json=rounds,
        levels_json=levels,
        problems_json=problems,
        sponsor=sponsor,
        organizer=organizer,
        prize=prize,
        fee=fee,
        eligibility=eligibility,
        extra_json=extra,
        domains_json=domains,
    )


# CLI: init-db and reset-db
@app.cli.command('init-db')
def init_db_cmd():
    db.create_all()
    print('Database initialized at', app.config['SQLALCHEMY_DATABASE_URI'])


@app.cli.command('reset-db')
def reset_db_cmd():
    confirm = input("This will DROP all data. Type YES to continue: ")
    if confirm == 'YES':
        db.drop_all()
        db.create_all()
        print('Database reset done.')
    else:
        print('Aborted.')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
