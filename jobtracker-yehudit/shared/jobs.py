"""Job-application store (domain data). Output is kept compact on purpose."""
STATUSES = ("wishlist", "applied", "interview", "offer", "rejected")


class JobStore:
    def __init__(self, ws):
        self.ws = ws

    def _all(self):
        return self.ws.read_json(self.ws.jobs_path, [])

    def all(self):
        return self._all()

    def add(self, company, title, status="applied", notes="", source=""):
        if status not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}, got {status!r}")
        jobs = self._all()
        for j in jobs:
            if j["company"].lower() == company.lower() and j["title"].lower() == title.lower():
                raise ValueError(f"job already exists with id {j['id']}")
        job = {"id": len(jobs) + 1, "company": company, "title": title,
               "status": status, "notes": notes, "source": source}
        jobs.append(job)
        self.ws.write_json(self.ws.jobs_path, jobs)
        return job

    def find(self, ref):
        """Find by numeric id or case-insensitive company name."""
        jobs = self._all()
        by_id = [j for j in jobs if str(j["id"]) == str(ref)]
        if by_id:
            return by_id
        return [j for j in jobs if j["company"].lower() == str(ref).lower()]

    def update_status(self, ref, status):
        if status not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}, got {status!r}")
        matches = self.find(ref)
        if not matches:
            raise LookupError(f"no job matches {ref!r}")
        if len(matches) > 1:
            raise LookupError(f"{ref!r} is ambiguous, use one of ids {[j['id'] for j in matches]}")
        jobs = self._all()
        for j in jobs:
            if j["id"] == matches[0]["id"]:
                j["status"] = status
        self.ws.write_json(self.ws.jobs_path, jobs)
        return next(j for j in jobs if j["id"] == matches[0]["id"])

    def list(self, status=None, limit=10):
        jobs = [j for j in self._all() if status in (None, "", j["status"])]
        return jobs[-limit:]

    def summary(self):
        counts = {}
        for j in self._all():
            counts[j["status"]] = counts.get(j["status"], 0) + 1
        return counts
