from __future__ import annotations

from datetime import datetime
import re

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.update(
    SECRET_KEY="dev-secret-key-change-me",
    SQLALCHEMY_DATABASE_URI="sqlite:///fixly.db",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)

db = SQLAlchemy(app)


class Tool(db.Model):
    __tablename__ = "tools"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    slug = db.Column(db.String(160), unique=True, nullable=False)
    summary = db.Column(db.String(280), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_published = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Tool {self.title!r}>"


class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(180), unique=True, nullable=False)
    excerpt = db.Column(db.String(280), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_published = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Post {self.title!r}>"


def slugify(value: str) -> str:
    """Create a URL-friendly slug from the provided value."""

    slug = re.sub(r"[^a-z0-9\s-]", "", value.lower())
    slug = re.sub(r"[\s-]+", "-", slug).strip("-")

    if not slug:
        slug = f"tool-{int(datetime.utcnow().timestamp())}"

    return slug


@app.before_first_request
def create_tables() -> None:
    db.create_all()


@app.context_processor
def inject_globals():
    return {
        "brand_name": "Fixly.dev",
        "brand_domain": "fixly.dev",
        "brand_tagline": "SaaS builder for 400+ developer automations",
        "brand_url": url_for("index"),
        "admin_tools_url": url_for("admin_tools"),
        "admin_posts_url": url_for("admin_posts"),
        "blog_url": url_for("blog_index"),
        "current_year": datetime.now().year,
    }


@app.template_filter("paragraphs")
def paragraphs(value: str | None) -> list[str]:
    if not value:
        return []

    return [segment.strip() for segment in value.split("\n") if segment.strip()]


@app.route("/")
def index():
    tools = (
        Tool.query.filter_by(is_published=True)
        .order_by(Tool.created_at.desc())
        .all()
    )

    posts = (
        Post.query.filter_by(is_published=True)
        .order_by(Post.created_at.desc())
        .limit(3)
        .all()
    )

    return render_template("home.html", tools=tools, posts=posts)


@app.route("/tools/<string:slug>")
def tool_detail(slug: str):
    tool = Tool.query.filter_by(slug=slug, is_published=True).first()
    if tool is None:
        abort(404)

    return render_template("tool_detail.html", tool=tool)


@app.route("/blog")
def blog_index():
    posts = (
        Post.query.filter_by(is_published=True)
        .order_by(Post.created_at.desc())
        .all()
    )

    return render_template("blog_index.html", posts=posts)


@app.route("/blog/<string:slug>")
def blog_detail(slug: str):
    post = Post.query.filter_by(slug=slug, is_published=True).first()
    if post is None:
        abort(404)

    return render_template("blog_detail.html", post=post)


@app.route("/admin/tools", methods=["GET", "POST"])
def admin_tools():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        summary = request.form.get("summary", "").strip()
        content = request.form.get("content", "").strip()

        if not title or not summary or not content:
            flash("Please provide a title, summary, and detailed content.", "error")
        else:
            base_slug = slugify(title)
            slug_candidate = base_slug
            index = 1

            while Tool.query.filter_by(slug=slug_candidate).first() is not None:
                index += 1
                slug_candidate = f"{base_slug}-{index}"

            tool = Tool(
                title=title,
                summary=summary,
                content=content,
                slug=slug_candidate,
                is_published=True,
            )

            db.session.add(tool)
            db.session.commit()

            flash("“{}” is live on the Fixly.dev homepage.".format(tool.title), "success")
            return redirect(url_for("admin_tools"))

    tools = Tool.query.order_by(Tool.created_at.desc()).all()
    return render_template("admin/tools.html", tools=tools)


@app.route("/admin/posts", methods=["GET", "POST"])
def admin_posts():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        excerpt = request.form.get("excerpt", "").strip()
        content = request.form.get("content", "").strip()

        if not title or not content:
            flash("Posts need a title and content before publishing.", "error")
        else:
            if not excerpt:
                excerpt_candidate = content.strip()
                if len(excerpt_candidate) > 200:
                    excerpt_candidate = excerpt_candidate[:200].rsplit(" ", 1)[0]
                excerpt = excerpt_candidate or content[:200]

            base_slug = slugify(title)
            slug_candidate = base_slug
            index = 1

            while Post.query.filter_by(slug=slug_candidate).first() is not None:
                index += 1
                slug_candidate = f"{base_slug}-{index}"

            post = Post(
                title=title,
                excerpt=excerpt,
                content=content,
                slug=slug_candidate,
                is_published=True,
            )

            db.session.add(post)
            db.session.commit()

            flash("Blog post “{}” is live on Fixly.dev.".format(post.title), "success")
            return redirect(url_for("admin_posts"))

    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template("admin/posts.html", posts=posts)


@app.post("/admin/tools/<int:tool_id>/toggle")
def toggle_tool(tool_id: int):
    tool = Tool.query.get_or_404(tool_id)
    tool.is_published = not tool.is_published
    db.session.commit()

    state = "published" if tool.is_published else "hidden"
    flash("“{}” is now {}.".format(tool.title, state), "info")
    return redirect(url_for("admin_tools"))


@app.post("/admin/posts/<int:post_id>/toggle")
def toggle_post(post_id: int):
    post = Post.query.get_or_404(post_id)
    post.is_published = not post.is_published
    db.session.commit()

    state = "published" if post.is_published else "hidden"
    flash("“{}” is now {}.".format(post.title, state), "info")
    return redirect(url_for("admin_posts"))


if __name__ == "__main__":
    app.run(debug=True)
