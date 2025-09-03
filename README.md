# hackathon-centre

# College & External Events Aggregator
A clean, fast, Flask-based site that lists hackathons/events with rich filters. Admin can log in to add events. Users can submit suggestions (stored as pending) for admin review/approval.


## Features
- Public listing with instant search + multi-filter + collapsible details
- Admin login (username/password) → add events directly
- Public submission → queued as `pending` for admin review
- Flexible schema: add arbitrary key–value fields and multiple rounds per event
- SQLite storage; single-file deploy; Bootstrap UI + subtle animations


## Setup
1. **Clone & create env**
```bash
git clone <your-repo-url> hackhub
cd hackhub
python -m venv .venv && source .venv/bin/activate # Windows: .venv\Scripts\activate
pip install -r requirements.txt