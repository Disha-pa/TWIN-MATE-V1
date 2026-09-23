from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, doc):
        self.doc = doc
        self.id = str(doc["_id"])
        self.email = doc.get("email", "")
        self.name = doc.get("name", "")
        self.username = doc.get("username", "")
        self.age = doc.get("age")
        self.profile_pic = doc.get("profile_pic", "")
        self.avatar_color = doc.get("avatar_color", "#b5d8ff")
        self.timezone = doc.get("timezone", "UTC")
        self.onboarding_complete = doc.get("onboarding_complete", True)
        self.reminder_time = doc.get("reminder_time", "20:00")
        self.created_at = doc.get("created_at")

    def get_id(self):
        return self.id

    @property
    def display_name(self):
        return self.name or self.username or (self.email.split("@")[0] if self.email else "User")

    @property
    def initials(self):
        source = (self.name or self.username or self.email or "U").strip()
        return source[:1].upper()
