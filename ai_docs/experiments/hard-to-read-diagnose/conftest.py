# ABOUTME: Keeps repo-root pytest out of the seeded buggy trees and their hidden tests (#187); those run only through grade.py.
collect_ignore_glob = ["tasks/*", "hidden/*", "reference/*"]
