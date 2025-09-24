from __future__ import annotations

import os
from datetime import datetime
import re
from typing import Type

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

db = SQLAlchemy()


def configure_app(flask_app: Flask) -> None:
    """Configure core Flask and SQLAlchemy settings."""

    database_uri = os.environ.get("DATABASE_URL", "sqlite:///fixly.db")
    if database_uri.startswith("postgres://"):
        database_uri = database_uri.replace("postgres://", "postgresql://", 1)

    flask_app.config.update(
        SECRET_KEY=os.environ.get("FIXLY_SECRET_KEY", "dev-secret-key-change-me"),
        SQLALCHEMY_DATABASE_URI=database_uri,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    db.init_app(flask_app)


configure_app(app)


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


def slugify(value: str, fallback_prefix: str = "item") -> str:
    """Create a URL-friendly slug from the provided value."""

    slug = re.sub(r"[^a-z0-9\s-]", "", value.lower())
    slug = re.sub(r"[\s-]+", "-", slug).strip("-")

    if not slug:
        slug = f"{fallback_prefix}-{int(datetime.utcnow().timestamp())}"

    return slug


def generate_unique_slug(model: Type[db.Model], base_slug: str) -> str:
    """Ensure the slug is unique for the provided model class."""

    slug_column = model.__table__.columns["slug"]
    max_length = getattr(slug_column.type, "length", None)
    slug_root = base_slug[:max_length] if max_length else base_slug

    unique_slug = slug_root
    index = 1

    while model.query.filter_by(slug=unique_slug).first() is not None:
        suffix = f"-{index}"
        trimmed_root = slug_root
        if max_length:
            trimmed_root = slug_root[: max_length - len(suffix)]
        unique_slug = f"{trimmed_root}{suffix}"
        index += 1

    return unique_slug


def derive_excerpt(content: str, max_length: int) -> str:
    """Derive a plain-text excerpt trimmed to the specified max length."""

    excerpt_candidate = content.strip()
    if len(excerpt_candidate) <= max_length:
        return excerpt_candidate

    truncated = excerpt_candidate[:max_length].rsplit(" ", 1)[0]
    return truncated or excerpt_candidate[:max_length]


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
    form_data = {"title": "", "summary": "", "content": ""}

    if request.method == "POST":
        form_data = {
            "title": request.form.get("title", "").strip(),
            "summary": request.form.get("summary", "").strip(),
            "content": request.form.get("content", "").strip(),
        }

        errors: list[str] = []

        title_limit = getattr(Tool.__table__.columns["title"].type, "length", None)
        summary_limit = getattr(Tool.__table__.columns["summary"].type, "length", None)

        if not form_data["title"]:
            errors.append("Please provide a title for your tool.")
        elif title_limit and len(form_data["title"]) > title_limit:
            errors.append(f"Tool titles must be {title_limit} characters or fewer.")

        if not form_data["summary"]:
            errors.append("Share a short summary to highlight what the tool does.")
        elif summary_limit and len(form_data["summary"]) > summary_limit:
            errors.append(f"Summaries must be {summary_limit} characters or fewer.")

        if not form_data["content"]:
            errors.append("Add longer-form content so your launch page feels complete.")

        if errors:
            for message in errors:
                flash(message, "error")
        else:
            base_slug = slugify(form_data["title"], fallback_prefix="tool")
            slug = generate_unique_slug(Tool, base_slug)

            tool = Tool(
                title=form_data["title"],
                summary=form_data["summary"],
                content=form_data["content"],
                slug=slug,
                is_published=True,
            )

            db.session.add(tool)
            db.session.commit()

            flash(f'"{tool.title}" is live on the Fixly.dev homepage.', "success")
            return redirect(url_for("admin_tools"))

    tools = Tool.query.order_by(Tool.created_at.desc()).all()
    published_tool_count = sum(1 for tool in tools if tool.is_published)

    return render_template(
        "admin/tools.html",
        tools=tools,
        form_data=form_data,
        total_tool_count=len(tools),
        published_tool_count=published_tool_count,
    )


@app.route("/admin/posts", methods=["GET", "POST"])
def admin_posts():
    form_data = {"title": "", "excerpt": "", "content": ""}

    if request.method == "POST":
        form_data = {
            "title": request.form.get("title", "").strip(),
            "excerpt": request.form.get("excerpt", "").strip(),
            "content": request.form.get("content", "").strip(),
        }

        errors: list[str] = []

        title_limit = getattr(Post.__table__.columns["title"].type, "length", None)
        excerpt_limit = getattr(Post.__table__.columns["excerpt"].type, "length", None)

        if not form_data["title"]:
            errors.append("Posts need a title before publishing.")
        elif title_limit and len(form_data["title"]) > title_limit:
            errors.append(f"Post titles must be {title_limit} characters or fewer.")

        if not form_data["content"]:
            errors.append("Write your article content so readers have something to explore.")

        excerpt_value = form_data["excerpt"]
        if not excerpt_value and form_data["content"]:
            excerpt_value = derive_excerpt(form_data["content"], excerpt_limit or 200)

        form_data["excerpt"] = excerpt_value

        if excerpt_limit and len(excerpt_value) > excerpt_limit:
            errors.append(f"Excerpts must be {excerpt_limit} characters or fewer.")

        if errors:
            for message in errors:
                flash(message, "error")
        else:
            base_slug = slugify(form_data["title"], fallback_prefix="post")
            slug = generate_unique_slug(Post, base_slug)

            post = Post(
                title=form_data["title"],
                excerpt=excerpt_value,
                content=form_data["content"],
                slug=slug,
                is_published=True,
            )

            db.session.add(post)
            db.session.commit()

            flash(f'Blog post "{post.title}" is live on Fixly.dev.', "success")
            return redirect(url_for("admin_posts"))

    posts = Post.query.order_by(Post.created_at.desc()).all()
    published_post_count = sum(1 for post in posts if post.is_published)

    return render_template(
        "admin/posts.html",
        posts=posts,
        form_data=form_data,
        total_post_count=len(posts),
        published_post_count=published_post_count,
    )


@app.post("/admin/tools/<int:tool_id>/toggle")
def toggle_tool(tool_id: int):
    tool = Tool.query.get_or_404(tool_id)
    tool.is_published = not tool.is_published
    db.session.commit()

    state = "published" if tool.is_published else "hidden"
    flash(f'"{tool.title}" is now {state}.', "info")
    return redirect(url_for("admin_tools"))


@app.post("/admin/posts/<int:post_id>/toggle")
def toggle_post(post_id: int):
    post = Post.query.get_or_404(post_id)
    post.is_published = not post.is_published
    db.session.commit()

    state = "published" if post.is_published else "hidden"
    flash(f'"{post.title}" is now {state}.', "info")
    return redirect(url_for("admin_posts"))


def ensure_database_setup() -> None:
    with app.app_context():
        db.create_all()


ensure_database_setup()


if __name__ == "__main__":
    app.run(debug=True)
