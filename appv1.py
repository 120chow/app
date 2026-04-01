# Smart Negative Word Replacer Web App (Trainable + Editable + Deletable)
# Requirements:
# pip install flask

from flask import Flask, render_template_string, request, redirect
import re
import sqlite3

app = Flask(__name__)
DB_FILE = "replacements.db"

# -----------------------------
# Database setup
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS replacements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            negative_word TEXT UNIQUE,
            suggested_word TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def load_replacements():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT negative_word, suggested_word FROM replacements")
    data = dict(c.fetchall())
    conn.close()
    return data


def load_all():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, negative_word, suggested_word FROM replacements")
    rows = c.fetchall()
    conn.close()
    return rows


DEFAULT_REPLACEMENTS = {
    "scolded": "provided feedback",
    "forgot": "missed",
    "issue": "situation",
    "problem": "challenge",
    "problems": "challenges",
    "failed": "did not complete",
    "angry": "concerned",
    "wrong": "needs clarification",
    "blame": "highlight",
    "mistake": "oversight",
    "urgent": "high priority",
}


HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Smart Tone Improver</title>
    <style>
        body { font-family: Arial; padding: 40px; background: #f5f5f5; }
        textarea { width: 100%; height: 150px; padding: 10px; }
        input { padding: 8px; margin: 5px; }
        button { padding: 6px 12px; margin: 3px; }
        .output { margin-top: 20px; background: white; padding: 15px; border-radius: 8px; }
        .train { margin-top: 30px; background: #fff; padding: 15px; border-radius: 8px; }
        table { width: 100%; margin-top: 20px; background: white; border-collapse: collapse; }
        th, td { padding: 10px; border-bottom: 1px solid #ddd; }
    </style>
</head>
<body>
    <h2>Smart Tone Improver</h2>

    <form method="post">
        <textarea name="text" placeholder="Paste your summary here..."></textarea><br>
        <button type="submit">Improve Tone</button>
    </form>

    {% if result %}
    <div class="output">
        <h3>Improved Summary:</h3>
        <p>{{ result }}</p>
    </div>
    {% endif %}

    <div class="train">
        <h3>Teach Me New Suggestion</h3>
        <form method="post" action="/train">
            <input name="negative" placeholder="Negative word" required>
            <input name="positive" placeholder="Suggested word" required>
            <button type="submit">Save</button>
        </form>
    </div>

    <h3>Manage Suggestions</h3>
    <table>
        <tr><th>Negative</th><th>Suggested</th><th>Action</th></tr>
        {% for row in rows %}
        <tr>
            <form method="post" action="/update">
            <td>
                <input type="hidden" name="id" value="{{row[0]}}">
                <input name="negative" value="{{row[1]}}">
            </td>
            <td>
                <input name="positive" value="{{row[2]}}">
            </td>
            <td>
                <button type="submit">Update</button>
            </form>
            <form method="post" action="/delete" style="display:inline">
                <input type="hidden" name="id" value="{{row[0]}}">
                <button type="submit">Delete</button>
            </form>
            </td>
        </tr>
        {% endfor %}
    </table>

</body>
</html>
"""


def _preserve_case(original, replacement):
    if original.isupper():
        return replacement.upper()
    elif original[0].isupper():
        return replacement.capitalize()
    else:
        return replacement


def replace_negative_words(text, replacements):
    if not replacements:
        return text

    # FIX: Proper regex word boundaries (no hidden characters)
    pattern = re.compile(
        r"\b(" + "|".join(map(re.escape, replacements.keys())) + r")\b",
        re.IGNORECASE,
    )

    def replacer(match):
        word = match.group(0)
        replacement = replacements.get(word.lower())
        if replacement:
            return _preserve_case(word, replacement)
        return word

    return pattern.sub(replacer, text)


@app.route("/", methods=["GET", "POST"])
def home():
    replacements = load_replacements()
    rows = load_all()
    result = None
    if request.method == "POST":
        text = request.form.get("text", "")
        result = replace_negative_words(text, replacements)
    return render_template_string(HTML, result=result, rows=rows)


@app.route("/train", methods=["POST"])
def train():
    negative = request.form.get("negative").lower()
    positive = request.form.get("positive")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO replacements (negative_word, suggested_word) VALUES (?, ?)",
        (negative, positive),
    )
    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/update", methods=["POST"])
def update():
    id_ = request.form.get("id")
    negative = request.form.get("negative").lower()
    positive = request.form.get("positive")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "UPDATE replacements SET negative_word=?, suggested_word=? WHERE id=?",
        (negative, positive, id_),
    )
    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/delete", methods=["POST"])
def delete():
    id_ = request.form.get("id")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM replacements WHERE id=?", (id_,))
    conn.commit()
    conn.close()

    return redirect("/")


# ----------------------
# Test Cases
# ----------------------
def _run_tests():
    sample = {
        "scolded": "provided feedback",
        "problem": "challenge",
    }

    # existing tests
    assert replace_negative_words("Manager scolded me", sample) == "Manager provided feedback me"
    assert replace_negative_words("big problem", sample) == "big challenge"
    assert replace_negative_words("no change", sample) == "no change"

    # additional tests
    assert replace_negative_words("SCOLDED", sample) == "PROVIDED FEEDBACK"
    assert replace_negative_words("Scolded", sample) == "Provided feedback"
    assert replace_negative_words("problem solved", sample) == "challenge solved"
    assert replace_negative_words("multiple problems", {"problems":"challenges"}) == "multiple challenges"

    print("All tests passed!")


if __name__ == "__main__":
    init_db()

    if not load_replacements():
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        for k, v in DEFAULT_REPLACEMENTS.items():
            c.execute(
                "INSERT OR IGNORE INTO replacements (negative_word, suggested_word) VALUES (?, ?)",
                (k, v),
            )
        conn.commit()
        conn.close()

    _run_tests()

    # Always start Flask app automatically (no env variable needed)
    print("Starting web app...")
    print("Open in browser: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
