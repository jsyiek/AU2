import os

COLLEGES = [
    "Christ's College",
    "Churchill College",
    "Clare College",
    "Clare Hall",
    "Corpus Christi College",
    "Darwin College",
    "Downing College",
    "Emmanuel College",
    "Fitzwilliam College",
    "Girton College",
    "Gonville & Caius College",
    "Homerton College",
    "Hughes Hall",
    "Jesus College",
    "King's College",
    "Lucy Cavendish College",
    "Magdalene College",
    "Murray Edwards College",
    "Newnham College",
    "Pembroke College",
    "Peterhouse",
    "Queens' College",
    "Robinson College",
    "Selwyn College",
    "Sidney Sussex College",
    "St Catharine's College",
    "St Edmund's College",
    "St John's College",
    "Trinity College",
    "Trinity Hall",
    "Wolfson College",
    "Other (see notes)",
    "The Real World (no college)",
    "Anglia Ruskin",
    "Casual"
]

WATER_STATUSES = [
    "No water",
    "Water with care (small water weapons only)",
    "Full water"
]

WEBPAGE_WRITE_LOCATION = os.path.expanduser("~/pages")

if not os.path.exists(WEBPAGE_WRITE_LOCATION):
    os.makedirs(WEBPAGE_WRITE_LOCATION)